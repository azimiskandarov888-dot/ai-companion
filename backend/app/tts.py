"""The mouth: text-to-speech.

Six providers, chosen by config.TTS_PROVIDER (config.voice_provider says which
one actually speaks — «fish» with only an OpenRouter key is Fish through it):
  - "gemini"     Google's Gemini voices, streamed on Google's own key — THE VOICE
                 since 2026-10-03, chosen by the owner's ear (docs/VOICES-RU.md).
                 Each companion has a voice of his own and a line about whom it
                 plays (voices.py). Raw audio, 24 kHz: the file path gets WAV.
                 Streamed or not at all — the owner: «We are never going to use
                 non-streaming voice».
  - "yandex"     Yandex SpeechKit — Russian voices made BY Russians for
                 Russian. Best prosody of the lot on Russian text, and by some
                 distance the cheapest for it. The right default for this app.
  - "openai"     OpenAI — same key as the ears, takes a plain-language
                 direction for HOW to speak, and reachable where the others
                 are not.
  - "fish"       Fish Audio — excellent model, but see the cost note below
                 before choosing it for Russian.
  - "elevenlabs" ElevenLabs — warmest, and several times the price.
  - "openrouter" Fish Audio through OpenRouter — the same voice, on the one
                 key the owner has.
All return MP3 bytes, so the rest of the app doesn't care which spoke.

── HIS SOUNDS ──────────────────────────────────────────────────────────────

A cough, «кхм», a sigh, a laugh, a yawn — played, not read. The model writes
our own markers (body.py) where the sound happens; here, on the way to a voice
that can make it, each becomes that voice's tag, and it is made in HIS voice,
with his breath, in his room — never a recording of somebody else's cough,
which is heard at once as a sound effect. On any voice that cannot make it,
the marker is removed, exactly as before. See docs/SOUNDS.md.

── WHAT RUSSIAN ACTUALLY COSTS ─────────────────────────────────────────────

Every published price for these is quoted per CHARACTER or per "1M UTF-8
bytes", and for English those are the same number. For Russian they are not:
Cyrillic is TWO bytes per character in UTF-8, so a provider that bills bytes
charges exactly double its advertised rate for this app, on every single
sentence, forever.

    Yandex   standard   ~600 ₽ / 1M chars     ← cheapest, and Russian-native
    Yandex   premium   ~1200 ₽ / 1M chars
    OpenAI   gpt-4o-mini-tts   ~$12–15 / 1M chars
    Fish     s1 / s2-pro       $15 / 1M BYTES = ~$30 / 1M Russian chars
    ElevenLabs                 several times all of the above

An hour of speech is roughly 55 000 characters. A person using their full
daily allowance is on the order of 1.5M characters a month — which is about
$45 on Fish and about $11 on Yandex standard. That is the difference between
the voice eating the subscription and the voice being a rounding error.

None of this is a reason to avoid Fish if it sounds better to the person who
has to listen to it. It is a reason to KNOW, and to audition the cheap one
first (`python3 audition.py --compare`).

If no provider is configured, main.py falls back to letting the client speak
with its own free voice (the MVP path). The EARS stay on Whisper regardless —
Fish Audio's speech-to-text doesn't support Russian (see stt.py).
"""

from __future__ import annotations

import asyncio
import io
import json
import re
import sys
import time
import wave
from collections import deque
from collections.abc import AsyncIterator

import httpx


from . import body, companion, config, lang, voices

_FISH_API_URL = "https://api.fish.audio/v1/tts"
_ROUTER_TTS_URL = "https://openrouter.ai/api/v1/audio/speech"
_ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1/text-to-speech"
_OPENAI_TTS_URL = "https://api.openai.com/v1/audio/speech"
_YANDEX_TTS_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"


# --------------------------------------------------------------------------- #
# Cutting a reply into things worth speaking one at a time
# --------------------------------------------------------------------------- #
#
# THE POINT OF THIS SECTION, since it is the whole latency story:
#
# A turn used to be strictly serial — hear it all, think it all, say it all,
# THEN send it. The listener sat through the sum of three waits. Cut the reply
# at sentence boundaries and the three overlap: the first sentence is being
# spoken out loud while the second is still being written.
#
# The seams land where a person would draw breath anyway, which is why this
# works with plain MP3 files played back to back and needs no gapless audio
# engine, no WebSocket, and no provider-specific streaming protocol. It works
# identically on all four providers — which matters a great deal, because
# binding the app to one provider's live API is exactly how you end up unable
# to leave the expensive one.

#: The first chunk is cut as early as a sentence allows, however short — it is
#: the entire win, and «Доброе утро.» arriving in one second is worth more than
#: a perfectly balanced paragraph arriving in five.
FIRST_CHUNK_MIN = 10
#: And after that, near enough the same. The floor was 90 at first, on the
#: reasoning that a short chunk is a wasted round trip — which was measurably
#: wrong. A high floor makes the SECOND piece swallow the whole rest of the
#: reply, and the rest of the reply cannot exist until it has been written, so
#: he says «Доброе утро.» and then stops for a second and a half. The round
#: trip a low floor costs is paid while the previous sentence is still being
#: spoken aloud, where nobody can hear it; the gap a high floor costs happens
#: in the middle of him talking, where everybody can.
#:
#: Synthesising a sentence at a time does cost a little prosody — the voice
#: can't lean across a full stop it hasn't seen. Against a silence in the
#: middle of a sentence, that is a trade worth making.
LATER_CHUNK_MIN = 12
#: One enormous sentence would defeat the whole thing, so past this length we
#: cut at a comma or a dash — places a speaker would pause anyway.
CHUNK_MAX = 220
#: …and the FIRST piece need not wait that long. A long opening sentence may
#: go to the voice at its first comma or dash once it has this much in it: the
#: voice starts while the rest of the sentence is still being written. Short
#: sentences still go whole — «Понимаю.» split in two would be a stammer.
FIRST_CLAUSE_MIN = 40

#: Greedy on purpose: matches through the LAST sentence-ending punctuation that
#: has something after it, so several finished sentences go to the voice in one
#: call rather than one round trip each.
_COMPLETE_SENTENCES = re.compile(r"^.*[.!?…]+(?=\s)", re.DOTALL)
#: Where it is acceptable to break a sentence that has run too long, best first.
_SOFT_BREAKS = (" — ", "; ", ", ", " – ", " - ")
#: Where a FIRST piece may end: a finished sentence (with any closing quote or
#: bracket), or a pause inside one. Each only once something follows it.
_FIRST_PAUSES = re.compile(r"[.!?…]+[»\"')\]]*(?=\s)|[,;:](?=\s)|\s[—–](?=\s)")


def ready_split(text: str, *, first: bool) -> int:
    """How much of this HALF-WRITTEN reply is finished enough to speak now.

    Returns a character count, or 0 for "nothing yet — wait for more". The
    answer is only ever allowed to grow, which is what makes this safe to use
    on a reply that is still arriving: once a piece has been handed to the
    voice it can never be revised, because it may already have been heard.

    A sentence counts as finished only when something FOLLOWS its full stop.
    That costs one token of waiting and buys the difference between «Ну.» and
    «Ну. Здравствуй.» — and it is what stops «т. д.» being spoken as two
    sentences.
    """
    floor = FIRST_CHUNK_MIN if first else LATER_CHUNK_MIN

    if first:
        # The EARLIEST place a speaker could pause, not the latest: this is
        # the piece the listener is waiting on. Once found it never moves,
        # because nothing after it can change what came before.
        for pause in _FIRST_PAUSES.finditer(text):
            piece = text[: pause.end()].strip()
            ends_sentence = pause.group(0)[0] in ".!?…"
            if len(piece) >= (FIRST_CHUNK_MIN if ends_sentence else FIRST_CLAUSE_MIN):
                return pause.end()
    else:
        match = _COMPLETE_SENTENCES.search(text)
        if match and len(match.group(0).strip()) >= floor:
            return match.end()

    # No finished sentence yet. If it has run very long, break at a pause a
    # speaker would take anyway — otherwise one rambling sentence holds up the
    # entire reply and streaming has bought nothing.
    if len(text) > CHUNK_MAX:
        cut = max(
            (text.rfind(sep, 0, CHUNK_MAX) + len(sep) for sep in _SOFT_BREAKS),
            default=-1,
        )
        if cut > floor:
            return cut
    return 0


#: The live channel's FIRST piece is shorter still: the earliest pause a
#: speaker could take — «Ого,» — once it has this many letters. A voice that
#: makes each piece whole takes ~1.4 s plus ~0.25 s a second of speech
#: (docs/WHY-LIVE-IS-FAST.md), so the shorter the first piece, the sooner his
#: first word; the rest is made while it plays. The owner, 2026-10-03: he
#: should start talking «the same time it's thinking».
LIVE_FIRST_LETTERS = 3
_LETTER = re.compile(r"[^\W\d_]")


def first_pause(text: str) -> int:
    """Where the live channel's first piece ends in a reply still being
    written: at its first pause with a word before it — or, failing one, where
    `ready_split` would end it. 0 for «not yet». Never moves once found."""
    for pause in _FIRST_PAUSES.finditer(text):
        if len(_LETTER.findall(text[: pause.end()])) >= LIVE_FIRST_LETTERS:
            return pause.end()
    return ready_split(text, first=True)


def speakable_chunks(text: str) -> list[str]:
    """Cut a FINISHED reply into pieces that can each be spoken on their own.

    The batch form of `ready_split`, built on it so the two can never drift
    apart. Guarantees: every character survives, in order; no chunk is empty;
    the first chunk is as early as the first sentence allows.
    """
    chunks: list[str] = []
    rest = text.strip()
    while rest:
        cut = ready_split(rest, first=not chunks)
        if not cut:
            break
        piece = rest[:cut].strip()
        if piece:
            chunks.append(piece)
        rest = rest[cut:].lstrip()

    if rest:
        # The final sentence has no whitespace after it, so it always lands
        # here. A tail too short to stand alone joins the piece before it
        # rather than becoming a lone «Да.» after a pause.
        if chunks and len(rest) < LATER_CHUNK_MIN:
            chunks[-1] = f"{chunks[-1]} {rest}"
        else:
            chunks.append(rest)
    return chunks


# --------------------------------------------------------------------------- #
# Which voice this particular companion speaks in
# --------------------------------------------------------------------------- #
def is_female(persona: dict | None) -> bool:
    """Did the pen write a woman?

    Read from the persona's own `gender` field rather than guessed from the
    name, because Russian names will not support the guess: Гриша, Никита,
    Илья and Саша all end in -а and are men. A missing field means an older
    persona, written before this existed, and those keep the default voice.
    """
    value = str((persona or {}).get("gender") or "").strip().lower()
    return value.startswith(("ж", "f"))  # женский · женщина · female


def voice_for(persona: dict | None) -> str | None:
    """The provider-specific voice this companion should speak in.

    None means "the configured default", which is the male one — so nothing
    changes for the companions that already exist.

    Half the people the matchmaker invents are women, and until this existed
    every one of them was read aloud by a man. There is no faster way to
    destroy the one thing this app is for.
    """
    if config.voice_provider() == "gemini":
        # His own, from the catalog — the same in either language.
        return voices.key(voices.of(persona))
    if config.voice_provider() in ("fish", "openrouter") and lang.english():
        # An English conversation gets English voices, his or hers, explicitly.
        return config.FISH_VOICE_ID_FEMALE_EN if is_female(persona) else config.FISH_VOICE_ID_EN
    if not is_female(persona):
        return None
    female = {
        "yandex": config.YANDEX_VOICE_FEMALE,
        "openai": config.OPENAI_VOICE_FEMALE,
        "fish": config.FISH_VOICE_ID_FEMALE,
        "openrouter": config.FISH_VOICE_ID_FEMALE,
        "elevenlabs": config.ELEVENLABS_VOICE_ID_FEMALE,
    }.get(config.voice_provider(), "")
    # Unset → fall back rather than fail. A wrong-sounding voice is bad; a
    # friend who has stopped speaking altogether is worse.
    return female or None


# --------------------------------------------------------------------------- #
# What actually gets read out loud
# --------------------------------------------------------------------------- #
#
# A voice reads EXACTLY what it is given, including things that were never
# meant to be heard. Live: he said «ну вообще звёздочка пауза звёздочка» —
# the model had written «*пауза*» as a stage direction and Yandex dutifully
# pronounced the asterisks and the word inside them.
#
# The prompt now forbids writing them (companion.py), but a prompt is a
# request and this is a guarantee. It is the last thing before the audio, it
# costs nothing, and the failure it prevents is one of the worst in the app:
# a friend reading his own script aloud is unmistakably a machine.

_STAGE_DIRECTIONS = (
    # *пауза*, _тихо_, **вздыхает** — emphasis and directions alike.
    re.compile(r"[*_]{1,3}[^*_\n]{1,60}[*_]{1,3}"),
    # [пауза], (смеётся) — brackets only when the WHOLE thing is a direction;
    # ordinary parenthetical speech is left alone, since people do talk that way.
    re.compile(r"\[[^\]\n]{1,60}\]"),
)

#: A link, whole — «[сайт](https://…)» — or a bare address. A web-search turn
#: has its sources taken out before it gets here (brain._uncited), and this is
#: the net under that: an address read aloud is a minute of «эйч ти ти пи эс
#: двоеточие».
_LINKS = re.compile(r"\[[^\]\n]{0,80}\]\([^)\s]{0,300}\)|\(?https?://[^\s)]+\)?")

#: Anything a voice would either mispronounce or read as a word.
_UNSPEAKABLE = re.compile(
    r"[#`~|<>{}\\^]"                       # markdown and code punctuation
    r"|[\U0001F300-\U0001FAFF☀-➿]"  # emoji and dingbats
)

#: A bullet at the start of a line — «- » read aloud is «минус».
_BULLET = re.compile(r"(?m)^\s*[-•*]\s+")


#: His markers → what Fish S2 plays instead of reading. Chosen by listening
#: (2026-09-28, docs/SOUNDS.md): each synthesised inside a Russian sentence, in
#: more than one voice, and heard back. Brackets, never parentheses —
#: «(clears throat)» came out as «Силле… строт» and «(yawning)» was spelled
#: letter by letter. A laugh plays at the START of a sentence, in a man's voice
#: and a woman's; in the middle of one only now and then — so he is told to put
#: it there. A yawn sometimes comes out as a tired sigh, which is a fine thing
#: for a yawn to become. A sneeze could not be made at all — it came out as a
#: sniff — so it is not here, and nothing that is not here is ever read aloud:
#: it is removed.
SOUNDS: dict[str, str] = {
    body.MARK_COUGH: "[cough]",
    body.MARK_CLEAR: "[clears throat]",
    body.MARK_SIGH: "[sigh]",
    body.MARK_YAWN: "[yawns]",
    body.MARK_LAUGH: "[laugh]",
}
#: …and what the Gemini voices play: Google's own tags, in angle brackets
#: (ai.google.dev, speech generation). Put in a Russian sentence and heard back
#: by Deepgram, none was read out as a word (2026-10-03). Whether each is the
#: sound and not a hiccup is for the owner's ear — so only the three Google
#: names, and no throat-clearing or yawn: there is no tag for them, and a
#: marker with no tag is removed, never read aloud.
GEMINI_SOUNDS: dict[str, str] = {
    body.MARK_COUGH: "<cough>",
    body.MARK_SIGH: "<sigh>",
    body.MARK_LAUGH: "<laugh>",
}


def _sounds() -> dict[str, str]:
    """The tags of the voice that will actually speak."""
    return GEMINI_SOUNDS if config.voice_provider() == "gemini" else SOUNDS


def makes_sounds() -> bool:
    """Does the voice that will actually speak make his sounds? Gemini does,
    and Fish S2 — directly or through OpenRouter. S1, the other providers, and
    the phone's own voice (no server voice set up) do not."""
    if not configured():
        return False
    provider = config.voice_provider()
    return provider == "gemini" or (provider in ("fish", "openrouter")
                                    and config.FISH_MODEL.startswith("s2"))


def makes(mark: str) -> bool:
    """Will this marker be HEARD — rather than quietly removed?"""
    return makes_sounds() and mark in _sounds()


def audible(text: str) -> bool:
    """Is there anything in this to put through the voice at all?"""
    return bool(spoken(text, sounds=makes_sounds()))


def spoken(text: str, *, sounds: bool = False) -> str:
    """The text with everything that was never meant to be heard removed —
    and, with `sounds`, his markers turned into the sounds the voice makes."""
    # FIRST, before anything else: the farewell marker. It is not punctuation
    # and not a stage direction, and if any later rule got to it first it
    # would leave «КОНЕЦ» behind as a word and he would announce the end of
    # the conversation out loud.
    text = text.replace(companion.FAREWELL_MARKER, " ")
    # And the body markers, for the same reason and just as early. These matter
    # MORE here than at the end of a turn, because the streaming path
    # synthesises each fragment as it arrives — long before anything has looked
    # at the finished reply. «Две косые черты кашель» is the worst sound this
    # app could make, and this is the only place that sees every fragment.
    # A sound the voice can make is held aside as a token no rule below can
    # touch — the stage-direction rule would otherwise eat its brackets — and
    # put back as the voice's tag once everything else is clean.
    held: dict[str, str] = {}
    table = _sounds()
    for i, mark in enumerate(body.MARKERS):
        if sounds and mark in table:
            token = f"\x00{i}\x00"
            if mark in text:
                held[token] = table[mark]
            text = text.replace(mark, f" {token} ")
        else:
            text = text.replace(mark, " ")
    text = _LINKS.sub(" ", text)
    for pattern in _STAGE_DIRECTIONS:
        text = pattern.sub(" ", text)
    text = _BULLET.sub("", text)
    text = _UNSPEAKABLE.sub(" ", text)
    # Collapse the holes left behind, and tidy space before punctuation so a
    # removed direction doesn't leave «слушай , друг».
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+([,.!?…:;])", r"\1", text)
    for token, tag in held.items():
        text = text.replace(token, tag)
    return text.strip()


def configured() -> bool:
    """Is the selected voice provider set up? (Single source of truth: config.)"""
    return config.tts_configured()


def mime() -> str:
    """What `synthesize` returns: WAV from the Gemini voices — they give raw
    audio, and wrapping it costs nothing — MP3 from everybody else."""
    return "audio/wav" if config.voice_provider() == "gemini" else "audio/mpeg"


def slow_start() -> bool:
    """Does the voice take a while to make its first sound? Gemini does —
    0.6–0.9 s, against Fish's ~0.45 — so the live channel starts the next
    piece's voice sooner (live._AHEAD_WHOLE)."""
    return config.voice_provider() == "gemini"


def streams() -> bool:
    """Does the voice start sounding before the sentence is made? Fish and
    Gemini do; the other providers give a whole file."""
    return config.voice_provider() in ("fish", "openrouter", "gemini")


def provider_name() -> str:
    """Which voice is speaking — for the health endpoint (no secrets)."""
    return config.voice_provider() or "none"


#: How much slower he speaks to somebody who has been struggling to follow him.
#: 0.85 of the configured rate — noticeably easier to catch, and nowhere near
#: the theatrical slowness that reads as talking to a child, which is its own
#: insult and the one this app can least afford to give.
SLOWER = 0.85


def _base_speed(raw: str | float) -> float:
    """The configured rate as a number. Bad config must not silence the voice."""
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 1.0


def rate_for(user_id: str | None) -> float:
    """The speaking rate for THIS person, as a multiplier of the configured one.

    The app already watched this and then did nothing mechanical about it: two
    confirmed «переспросил» or «говори помедленнее» produced a line in the
    prompt asking for shorter sentences — which helps, and is not what was
    asked for. The knob is on the API. A rule that can be replaced by a
    mechanism should be.

    Never raises and never blocks: a voice that will not speak is far worse
    than one speaking at the wrong speed, so anything unexpected here means
    the ordinary rate.
    """
    if not user_id:
        return 1.0
    try:
        from . import fit

        return SLOWER if fit.hard_of_hearing(user_id) else 1.0
    except Exception:  # noqa: BLE001 — see the docstring
        return 1.0


async def synthesize(
    text: str, voice: str | None = None, *, rate: float = 1.0
) -> bytes:
    """Turn a reply into spoken audio (MP3 bytes), via the chosen provider.

    `voice` is a provider-specific voice id/name — normally whatever
    `voice_for(persona)` returned, so that a companion who is a woman is
    not read aloud by a man. None means the configured default.

    `rate` multiplies the configured speaking rate — `rate_for(user_id)`. Only
    the providers that actually take a speed parameter honour it, and that is
    stated rather than papered over: pretending to slow down a voice that has
    not slowed down would be worse than the ordinary rate, because the watching
    would look as though it had been acted on.
    """
    # One choke point, so every provider gets this for free — and his sounds
    # reach only a voice that can make them.
    text = spoken(text, sounds=makes_sounds())
    if not text:
        raise ValueError("Nothing to say — empty text passed to synthesize().")

    provider = config.voice_provider()
    if provider == "gemini":
        if not config.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set — the voice (Gemini) is not configured.")
        return await _synthesize_gemini(text, voice, rate=rate)

    if provider == "fish":
        if not config.FISH_API_KEY:
            raise RuntimeError(
                "FISH_API_KEY is not set — the Fish Audio voice is not configured."
            )
        return await _synthesize_fish(text, voice)

    if provider == "openrouter":
        if not config.OPENROUTER_API_KEY:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set — the voice (OpenRouter) is not configured."
            )
        return await _synthesize_openrouter(text, voice)

    if provider == "openai":
        if not config.OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY is not set — the OpenAI voice is not configured."
            )
        return await _synthesize_openai(text, voice, rate=rate)

    if provider == "yandex":
        if not (config.YANDEX_API_KEY and config.YANDEX_FOLDER_ID):
            raise RuntimeError(
                "YANDEX_API_KEY / YANDEX_FOLDER_ID not set — the Yandex voice "
                "is not configured."
            )
        return await _synthesize_yandex(text, voice, rate=rate)

    if provider == "elevenlabs":
        if not (config.ELEVENLABS_API_KEY and config.ELEVENLABS_VOICE_ID):
            raise RuntimeError(
                "ELEVENLABS_API_KEY / ELEVENLABS_VOICE_ID not set — the ElevenLabs "
                "voice is not configured."
            )
        return await _synthesize_elevenlabs(text, voice)

    raise RuntimeError(
        f"No voice provider configured (TTS_PROVIDER={config.TTS_PROVIDER!r})."
    )


# --------------------------------------------------------------------------- #
# Fish — directly, or through OpenRouter — on one open line
# --------------------------------------------------------------------------- #

#: One line to the voice for the whole process. A fresh connection is three
#: or four round trips of handshakes before a byte is even asked for: first
#: audio came back in 0.87–1.12 s on a new connection and 0.47–0.54 s on an open
#: one (measured from Tashkent, 2026-09-29) — and the old code opened a new one
#: for every sentence he said.
_client: httpx.AsyncClient | None = None
_client_loop: asyncio.AbstractEventLoop | None = None

#: Raw audio as he is streamed: 16-bit little-endian mono. OpenRouter says the
#: rate in its content type («audio/pcm;rate=44100;channels=1»), and that is
#: what is believed; this is the rate asked of Fish directly, and the fallback.
PCM_RATE = 44100
#: …and the rate the Gemini voices give, when Google does not say.
GEMINI_RATE = 24000
_RATE = re.compile(r"rate=(\d+)")


def _line() -> httpx.AsyncClient:
    """The open line — made again only once the event loop it was made in has
    closed (a tool running asyncio.run twice), because a connection outliving
    its loop is only a source of errors."""
    global _client, _client_loop
    if _client is not None and _client_loop is not None and _client_loop.is_closed():
        _client = None
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0),
            # httpx keeps an idle connection five seconds by default — less
            # than one of the person's turns — and then the handshake is paid
            # again before the first word.
            limits=httpx.Limits(keepalive_expiry=180.0),
        )
        try:
            _client_loop = asyncio.get_running_loop()
        except RuntimeError:
            _client_loop = None
    return _client


async def warm(lines: int = 1) -> None:
    """Open the line to the voice before it is needed (see brain.warm) — or
    `lines` of them, for pieces made side by side (live._AHEAD_WHOLE): one
    connection carries one piece at a time, and a second piece asked for while
    the first is still coming would otherwise begin with a handshake. Never
    raises, costs nothing."""
    provider = config.voice_provider()
    url = ("https://generativelanguage.googleapis.com/" if provider == "gemini" and config.GEMINI_API_KEY
           else "https://openrouter.ai/api/v1/models" if provider == "openrouter" and config.OPENROUTER_API_KEY
           else "https://api.fish.audio/" if provider == "fish" and config.FISH_API_KEY
           else None)
    if url is None:
        return
    # Side by side, so each takes a line of its own.
    await asyncio.gather(*(_line().head(url) for _ in range(max(1, lines))), return_exceptions=True)


def _fish_request(text: str, voice: str | None, fmt: str) -> tuple[str, dict, dict]:
    """Fish Audio directly: POST /v1/tts, the model in a header."""
    headers = {
        "Authorization": f"Bearer {config.FISH_API_KEY}",
        "Content-Type": "application/json",
        # Fish selects the model version via this header (e.g. "s1", "s2-pro").
        "model": config.FISH_MODEL,
    }
    payload: dict = {
        "text": text,
        "format": fmt,
        "normalize": True,   # tidy punctuation/numbers for natural speech
        # "balanced" starts returning audio sooner than "normal" at a
        # quality cost nobody has ever noticed in a spoken sentence. The
        # voice is the slowest link in the turn, so this is the cheapest
        # second available.
        "latency": "balanced",
    }
    if fmt == "mp3":
        payload["mp3_bitrate"] = 128
    if fmt == "pcm":
        payload["sample_rate"] = PCM_RATE
    # A chosen voice from the Fish library; omit to use Fish's default voice.
    chosen = voice or (config.FISH_VOICE_ID_EN if lang.english() else config.FISH_VOICE_ID)
    if chosen:
        payload["reference_id"] = chosen
    return _FISH_API_URL, headers, payload


def _router_request(text: str, voice: str | None, fmt: str) -> tuple[str, dict, dict]:
    """The same Fish model and voice ids through OpenRouter, on its key."""
    payload: dict = {
        "model": f"fish-audio/{config.FISH_MODEL}",
        "input": text,
        "response_format": fmt,
    }
    chosen = voice or (config.FISH_VOICE_ID_EN if lang.english() else config.FISH_VOICE_ID)
    if chosen:
        payload["voice"] = chosen
    return _ROUTER_TTS_URL, {"Authorization": f"Bearer {config.OPENROUTER_API_KEY}"}, payload


#: What a line with no companion behind it speaks in (voice_for gives every
#: companion his own): the owner's best of thirty.
GEMINI_DEFAULT = "Zubenelgenubi"
#: Added to whom the voice plays for somebody who has trouble following him
#: (rate_for): the voice takes no speed, and is told instead.
_SLOWER_STYLE = ", speaking a little slower and more clearly than usual"


def wav(pcm: bytes, rate: int) -> bytes:
    """Raw 16-bit mono audio as a WAV file — what a phone plays from a file."""
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm[: len(pcm) - len(pcm) % 2])
    return out.getvalue()


_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse"
_PCM_RATE_IN = re.compile(r"rate=(\d+)", re.I)


def _gemini_direct_request(text: str, voice: str | None, *, rate: float = 1.0) -> tuple[str, dict, dict]:
    """The same voice on Google's own key, as a stream — streamGenerateContent,
    the voice in `speech_config.voice_config.voice` and whom it plays in the
    text's own `speech_metadata.style` (ai.google.dev — generate-content
    speech generation). Measured 2026-10-03 from Tashkent, «Ого, сам программу
    пишешь?»: first sound in 0.63–0.93 s on 3.8 Flash-Lite and 1.07–1.10 s on
    3.8 Flash — against 2.3–2.9 s by the newer Interactions API and ~2 s whole
    through OpenRouter. The style is honoured (an old man read those words in
    4.9–5.6 s, a student in 3.4–3.8 s) and never read out."""
    name, style = voices.parse(voice) or (GEMINI_DEFAULT, voices.MANNER)
    if rate < 1.0:
        style += _SLOWER_STYLE
    model = config.GEMINI_TTS_MODEL.split("/", 1)[-1]
    payload = {
        "contents": [{"role": "user", "parts": [{"text": text, "speech_metadata": {"style": style}}]}],
        "generationConfig": {"responseModalities": ["AUDIO"],
                             "speech_config": {"voice_config": {"voice": name}}},
    }
    return (_GEMINI_URL.format(model=model),
            {"x-goog-api-key": config.GEMINI_API_KEY or "", "Content-Type": "application/json"}, payload)


def _audio_in(event: dict) -> tuple[int, bytes]:
    """(rate, audio) one streamed event carries: base64 in `inlineData` of its
    parts. Read tolerantly — what is not audio is no audio."""
    import base64

    rate, audio = GEMINI_RATE, b""
    for candidate in event.get("candidates") or []:
        for part in ((candidate or {}).get("content") or {}).get("parts") or []:
            inline = (part or {}).get("inlineData") or {}
            data = inline.get("data")
            if not isinstance(data, str):
                continue
            if found := _PCM_RATE_IN.search(str(inline.get("mimeType") or "")):
                rate = int(found.group(1))
            try:
                audio += base64.b64decode(data)
            except (ValueError, TypeError):
                continue
    return rate, audio


class _Budget:
    """Requests a minute to the voice, counted on this side, so that Google
    never has to refuse one (config.GEMINI_TTS_RPM: ten, on a paid key's first
    tier). His words take a request whenever one is left; work nobody is
    waiting on — his sounds made ahead (first_sound.prepare) — only while
    `spare` more are left for his words. A request that cannot go yet waits
    for the minute to free one: a pause, never a refusal mid-sentence."""

    #: A minute — and a second, for two clocks that do not quite agree.
    WINDOW = 61.0

    def __init__(self, per_minute: int, window: float = WINDOW) -> None:
        self.per_minute = per_minute
        self.window = window
        self._sent: deque[float] = deque()
        self._closed_until = 0.0

    def left(self) -> int:
        now = time.monotonic()
        while self._sent and now - self._sent[0] >= self.window:
            self._sent.popleft()
        if now < self._closed_until:
            return 0
        return self.per_minute - len(self._sent)

    async def take(self, *, spare: int = 0) -> None:
        if self.per_minute <= 0:
            return
        if (shut := self._closed_until - time.monotonic()) > WAIT_AT_MOST:
            raise RuntimeError(f"Gemini API voice refused (429) for another {shut / 3600:.1f} h — "
                               "the key's requests for the day are spent")
        while self.left() <= spare:
            now = time.monotonic()
            if now < self._closed_until:
                opens = self._closed_until                  # Google said when
            else:
                opens = self._sent[0] + self.window          # the oldest leaves the minute
            await asyncio.sleep(max(0.05, opens - now))
        self._sent.append(time.monotonic())

    def refused(self, seconds: float) -> None:
        """Google refused all the same — the key is used from somewhere else
        too: nothing goes until it said to come back."""
        self._closed_until = max(self._closed_until, time.monotonic() + seconds)


_budget: _Budget | None = None
#: Longer than this, a refusal is not waited out: on a paid key's first tier
#: Google also takes only 100 requests a DAY for the voice (measured
#: 2026-10-07, GenerateRequestsPerDayPerProjectPerModel) and then says to come
#: back in hours. A turn says so at once rather than hanging.
WAIT_AT_MOST = 12.0
#: Requests his sounds made ahead leave for his words (first_sound.prepare).
BACKGROUND_SPARE = 4


def _voice_budget() -> _Budget:
    global _budget
    if _budget is None or _budget.per_minute != config.GEMINI_TTS_RPM:
        _budget = _Budget(config.GEMINI_TTS_RPM)
    return _budget


def limited() -> bool:
    """Is the voice rationed by the minute? Then an answer is voiced in as few
    pieces as it can be without a silence in it (live.Session._answer)."""
    return config.voice_provider() == "gemini" and config.GEMINI_TTS_RPM > 0


def room() -> int:
    """Requests to the voice left this minute — as many as one likes when it
    is not rationed."""
    return _voice_budget().left() if limited() else 1_000


def _retry_after(detail: bytes) -> float:
    """How long Google said to wait, from its refusal (google.rpc.RetryInfo
    «13s»); ten seconds when it did not say."""
    try:
        for item in json.loads(detail).get("error", {}).get("details", []):
            if str(item.get("@type", "")).endswith("RetryInfo"):
                return float(str(item.get("retryDelay", "10s")).rstrip("s"))
    except (ValueError, TypeError, AttributeError):
        pass
    return 10.0


async def _gemini_direct_stream(text: str, voice: str | None, *, rate: float = 1.0,
                                background: bool = False) -> AsyncIterator[tuple[int, bytes]]:
    """(rate, raw audio) from Google as it is made, within the minute's
    requests (_Budget). Refused for the minute all the same, it waits as long
    as Google says and asks once more; any other refusal is raised before the
    first sound."""
    url, headers, payload = _gemini_direct_request(text, voice, rate=rate)
    budget = _voice_budget()
    for attempt in (1, 2):
        await budget.take(spare=BACKGROUND_SPARE if background else 0)
        async with _line().stream("POST", url, headers=headers, json=payload) as resp:
            if resp.status_code != 200:
                detail = await resp.aread()
                if resp.status_code == 429:
                    budget.refused(wait := _retry_after(detail))
                    if attempt == 1 and wait <= WAIT_AT_MOST:
                        continue
                raise RuntimeError(f"Gemini API voice failed ({resp.status_code}): "
                                   f"{detail.decode('utf-8', 'replace')[:300]}")
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                try:
                    event = json.loads(line[len("data:"):].strip())
                except ValueError:
                    continue
                if not isinstance(event, dict):
                    continue
                if event.get("error"):
                    raise RuntimeError(f"Gemini API voice: {event['error']}")
                out_rate, audio = _audio_in(event)
                if audio:
                    yield out_rate, audio
            return


async def _gemini_pcm(text: str, voice: str | None, *, rate: float = 1.0,
                      background: bool = False) -> AsyncIterator[tuple[int, bytes]]:
    """A Gemini voice as (rate, raw audio) pieces, streamed on Google's key."""
    if not config.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set — the voice (Gemini) is not configured.")
    async for out_rate, audio in _gemini_direct_stream(text, voice, rate=rate, background=background):
        yield out_rate, audio


async def _synthesize_gemini(text: str, voice: str | None = None, *, rate: float = 1.0) -> bytes:
    """A Gemini voice for a file: the same stream, gathered, as WAV."""
    pcm, out_rate = b"", GEMINI_RATE
    async for out_rate, piece in _gemini_pcm(text, voice, rate=rate):
        pcm += piece
    return wav(pcm, out_rate)


async def _synthesize_fish(text: str, voice: str | None = None) -> bytes:
    """Fish Audio TTS, the whole sentence as MP3."""
    url, headers, payload = _fish_request(text, voice, "mp3")
    resp = await _line().post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Fish Audio TTS failed ({resp.status_code}): {resp.text[:300]}"
        )
    return resp.content


async def _synthesize_openrouter(text: str, voice: str | None = None) -> bytes:
    """Fish Audio through OpenRouter — the same model and the same voice ids,
    on the OpenRouter key. How his sounds were tested (docs/SOUNDS.md)."""
    url, headers, payload = _router_request(text, voice, "mp3")
    resp = await _line().post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        raise RuntimeError(
            f"OpenRouter voice failed ({resp.status_code}): {resp.text[:300]}"
        )
    return resp.content


async def stream(text: str, voice: str | None = None, *,
                 background: bool = False) -> AsyncIterator[tuple[int, bytes]]:
    """His voice for this text AS IT IS MADE: (rate, raw audio) pieces, the
    first of them long before the sentence is finished being synthesised.

    The live channel's voice (live.py). Measured through OpenRouter: the first
    bytes of a long sentence in 0.48 s, the whole of it in 1.9 s — the second
    number was what everybody used to wait for.

    Gemini streams here on Google's key, Fish directly or through OpenRouter;
    anything else is said plainly rather than faked. Pieces are always whole
    samples: a byte split across two pieces is a click.

    `background`: nobody is waiting on it (first_sound.prepare) — on a voice
    rationed by the minute it goes only while requests are left for his words.
    """
    text = spoken(text, sounds=makes_sounds())
    if not text:
        raise ValueError("Nothing to say — empty text passed to stream().")
    provider = config.voice_provider()
    default_rate = PCM_RATE
    if provider == "gemini" and config.GEMINI_API_KEY:
        carry = b""
        async for rate, chunk in _gemini_pcm(text, voice, background=background):
            data = carry + chunk
            whole = len(data) - len(data) % 2
            carry = data[whole:]
            if whole:
                yield rate, data[:whole]
        return
    if provider == "openrouter" and config.OPENROUTER_API_KEY:
        url, headers, payload = _router_request(text, voice, "pcm")
    elif provider == "fish" and config.FISH_API_KEY:
        url, headers, payload = _fish_request(text, voice, "pcm")
    else:
        raise RuntimeError(
            "The live channel needs a voice it can stream — Gemini (GEMINI_API_KEY), or Fish"
            f" directly (FISH_API_KEY) or through OpenRouter; TTS_PROVIDER={config.TTS_PROVIDER!r}."
        )
    async with _line().stream("POST", url, headers=headers, json=payload) as resp:
        if resp.status_code != 200:
            detail = (await resp.aread()).decode("utf-8", "replace")
            raise RuntimeError(f"The voice failed ({resp.status_code}): {detail[:300]}")
        found = _RATE.search(resp.headers.get("content-type", ""))
        rate = int(found.group(1)) if found else default_rate
        carry = b""
        async for chunk in resp.aiter_bytes():
            data = carry + chunk
            whole = len(data) - len(data) % 2
            carry = data[whole:]
            if whole:
                yield rate, data[:whole]


async def _synthesize_openai(text: str, voice: str | None = None, *, rate: float = 1.0) -> bytes:
    """OpenAI TTS. Returns MP3 bytes.

    `instructions` is the interesting part: gpt-4o-mini-tts takes a plain-language
    direction for HOW to speak, not just what to say. That is where his warmth
    actually comes from — the same words read as a news bulletin or as a friend
    are two different products.
    """
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload: dict = {
        "model": config.OPENAI_TTS_MODEL,
        "voice": voice or config.OPENAI_VOICE,
        "input": text,
        "response_format": "mp3",
    }
    if config.OPENAI_VOICE_STYLE:
        payload["instructions"] = config.OPENAI_VOICE_STYLE
    # Only when it is not 1.0: the default is the provider's own, and sending
    # an explicit 1.0 would quietly override any future change to that.
    if rate != 1.0:
        payload["speed"] = round(rate, 3)

    async with httpx.AsyncClient(timeout=60.0) as http:
        resp = await http.post(_OPENAI_TTS_URL, headers=headers, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(
                f"OpenAI TTS failed ({resp.status_code}): {resp.text[:300]}"
            )
        return resp.content


#: Set once, the first time a voice turns out not to accept an emotion, so the
#: retry below happens once rather than on every sentence he speaks.
_yandex_drop_emotion = False


def _yandex_takes_emotion() -> bool:
    """Should `emotion` be sent at all?

    Only if it was explicitly asked for — the default is empty, and empty is
    the better sound. `emotion` is a crude override (one of neutral | good |
    evil, held across a whole utterance) that only some voices accept; the
    premium ones refuse it because they already do the thing it approximates,
    reading the sentence first and picking human intonation for it. Pinning
    every line he ever says to "good" is what makes synthetic speech sound
    like a call centre.

    There is deliberately no cleverness about WHICH voices take it. An earlier
    version guessed from a `:premium` suffix — which turned out not to exist:
    Yandex rejects `filipp:premium` with a 400 and wants the bare name, though
    a good deal of its own documentation still shows the suffix. Guessing from
    published lists that disagree with the live API is how you get a heuristic
    that is confidently wrong; the retry below finds out for real, once.
    """
    return bool(config.YANDEX_EMOTION)


async def _synthesize_yandex(text: str, voice: str | None = None, *, rate: float = 1.0) -> bytes:
    """Yandex SpeechKit. Form-encoded, not JSON. Returns MP3 bytes.

    Emotion is the one fiddly part — see `_yandex_takes_emotion`. The rule
    there covers what the documentation says; the retry below covers what the
    API actually does, because a config detail must never be the reason a
    lonely person's friend goes silent.
    """
    global _yandex_drop_emotion

    # Lowercased and trimmed: Yandex voice names are case-sensitive and it
    # rejects «Jane» outright, which reads on the phone as «не слышит» and
    # takes a round trip through the logs to find. Nobody types a voice name
    # meaning a different one by its capitalisation, so there is nothing to
    # lose by normalising and a whole evening to save.
    speaking_as = (voice or config.YANDEX_VOICE).strip().lower()

    def form(with_emotion: bool) -> dict:
        data = {
            "text": text,
            "lang": "ru-RU",
            "voice": speaking_as,
            "speed": str(round(_base_speed(config.YANDEX_SPEED) * rate, 3)),
            "format": "mp3",
            "folderId": config.YANDEX_FOLDER_ID,
        }
        if with_emotion and _yandex_takes_emotion():
            data["emotion"] = config.YANDEX_EMOTION
        return data

    headers = {"Authorization": f"Api-Key {config.YANDEX_API_KEY}"}
    async with httpx.AsyncClient(timeout=60.0) as http:
        resp = await http.post(
            _YANDEX_TTS_URL, headers=headers, data=form(not _yandex_drop_emotion)
        )

        if resp.status_code == 400 and not _yandex_drop_emotion and _yandex_takes_emotion():
            print(
                f"\n  ℹ voice {speaking_as!r} doesn't take an emotion — "
                "speaking without one from now on.\n"
                "    Set YANDEX_EMOTION= (empty) in backend/.env to silence this.\n",
                file=sys.stderr,
                flush=True,
            )
            _yandex_drop_emotion = True
            resp = await http.post(_YANDEX_TTS_URL, headers=headers, data=form(False))

        if resp.status_code != 200:
            raise RuntimeError(
                f"Yandex SpeechKit failed ({resp.status_code}): {resp.text[:300]}"
                + _yandex_hint(resp.status_code, speaking_as)
            )
        return resp.content


def _yandex_hint(status: int, speaking_as: str = "") -> str:
    """Turn Yandex's terse HTTP codes into the thing you actually have to go
    and fix. Every one of these has cost somebody an evening."""
    if status in (401, 403):
        # A 401 whose body says PermissionDenied is not about the key at all —
        # the key was read fine, and then the request was refused anyway. FOUR
        # unrelated causes produce this identical message, and there is no way
        # to tell them apart from the response, so all four get named rather
        # than making someone guess in the dark.
        return (
            "\n    → the key was accepted and the request refused anyway. Four "
            "things look exactly like this:"
            "\n      1. BILLING. The billing account must be ACTIVE or "
            "TRIAL_ACTIVE. A cloud with no card attached, an unactivated trial "
            "or a spent grant denies permission to everything. Check this first "
            "— it is the one that has nothing to do with your setup."
            "\n      2. the service account has no role — give it "
            "ai.speechkit-tts.user, and verify it on the FOLDER's access-"
            "bindings page (the create dialog often fails to save it)"
            "\n      3. the role is on a DIFFERENT folder than YANDEX_FOLDER_ID"
            "\n      4. the API key was created with a restricted scope that "
            "excludes SpeechKit — make one with no scope limit"
            "\n      (docs/HIS-VOICE.md § «Если он говорит 401»)"
        )
    if status == 400:
        return (
            f"\n    → the voice {(speaking_as or config.YANDEX_VOICE)!r} may not exist. NOTE: the "
            "`:premium` suffix that much of Yandex's documentation shows "
            "(filipp:premium) is rejected — use the bare name, e.g. `filipp`, "
            "which IS the premium male voice."
            "\n      Otherwise YANDEX_FOLDER_ID is missing or wrong."
            "\n      `python3 audition.py --yandex` lists what your account "
            "actually has."
        )
    if status == 429:
        return "\n    → too many requests at once, or the billing account is out of credit"
    return ""


async def _synthesize_elevenlabs(text: str, voice: str | None = None) -> bytes:
    """ElevenLabs TTS (eleven_multilingual_v2 handles Russian). Returns MP3 bytes."""
    url = f"{_ELEVENLABS_API_BASE}/{voice or config.ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": config.ELEVENLABS_API_KEY,
        "accept": "audio/mpeg",
        "content-type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": config.ELEVENLABS_MODEL,
        # Warm, steady delivery for an elderly listener.
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        },
    }
    async with httpx.AsyncClient(timeout=60.0) as http:
        resp = await http.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(
                f"ElevenLabs TTS failed ({resp.status_code}): {resp.text[:300]}"
            )
        return resp.content
