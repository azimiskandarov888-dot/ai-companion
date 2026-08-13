"""The mouth: text-to-speech.

Four providers, chosen by config.TTS_PROVIDER:
  - "yandex"     Yandex SpeechKit — Russian voices made BY Russians for
                 Russian. Best prosody of the lot on Russian text, and by some
                 distance the cheapest for it. The right default for this app.
  - "openai"     OpenAI — same key as the ears, takes a plain-language
                 direction for HOW to speak, and reachable where the others
                 are not.
  - "fish"       Fish Audio — excellent model, but see the cost note below
                 before choosing it for Russian.
  - "elevenlabs" ElevenLabs — warmest, and several times the price.
All return MP3 bytes, so the rest of the app doesn't care which spoke.

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

import re
import sys

import httpx

from . import config

_FISH_API_URL = "https://api.fish.audio/v1/tts"
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

#: Greedy on purpose: matches through the LAST sentence-ending punctuation that
#: has something after it, so several finished sentences go to the voice in one
#: call rather than one round trip each.
_COMPLETE_SENTENCES = re.compile(r"^.*[.!?…]+(?=\s)", re.DOTALL)
#: Where it is acceptable to break a sentence that has run too long, best first.
_SOFT_BREAKS = (" — ", "; ", ", ", " – ", " - ")


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
    if not is_female(persona):
        return None
    female = {
        "yandex": config.YANDEX_VOICE_FEMALE,
        "openai": config.OPENAI_VOICE_FEMALE,
        "fish": config.FISH_VOICE_ID_FEMALE,
        "elevenlabs": config.ELEVENLABS_VOICE_ID_FEMALE,
    }.get(config.TTS_PROVIDER, "")
    # Unset → fall back rather than fail. A wrong-sounding voice is bad; a
    # friend who has stopped speaking altogether is worse.
    return female or None


def configured() -> bool:
    """Is the selected voice provider set up? (Single source of truth: config.)"""
    return config.tts_configured()


def provider_name() -> str:
    """Which voice is speaking — for the health endpoint (no secrets)."""
    return config.TTS_PROVIDER or "none"


async def synthesize(text: str, voice: str | None = None) -> bytes:
    """Turn a reply into spoken audio (MP3 bytes), via the chosen provider.

    `voice` is a provider-specific voice id/name — normally whatever
    `voice_for(persona)` returned, so that a companion who is a woman is
    not read aloud by a man. None means the configured default.
    """
    if not text.strip():
        raise ValueError("Nothing to say — empty text passed to synthesize().")

    if config.TTS_PROVIDER == "fish":
        if not config.FISH_API_KEY:
            raise RuntimeError(
                "FISH_API_KEY is not set — the Fish Audio voice is not configured."
            )
        return await _synthesize_fish(text, voice)

    if config.TTS_PROVIDER == "openai":
        if not config.OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY is not set — the OpenAI voice is not configured."
            )
        return await _synthesize_openai(text, voice)

    if config.TTS_PROVIDER == "yandex":
        if not (config.YANDEX_API_KEY and config.YANDEX_FOLDER_ID):
            raise RuntimeError(
                "YANDEX_API_KEY / YANDEX_FOLDER_ID not set — the Yandex voice "
                "is not configured."
            )
        return await _synthesize_yandex(text, voice)

    if config.TTS_PROVIDER == "elevenlabs":
        if not (config.ELEVENLABS_API_KEY and config.ELEVENLABS_VOICE_ID):
            raise RuntimeError(
                "ELEVENLABS_API_KEY / ELEVENLABS_VOICE_ID not set — the ElevenLabs "
                "voice is not configured."
            )
        return await _synthesize_elevenlabs(text, voice)

    raise RuntimeError(
        f"No voice provider configured (TTS_PROVIDER={config.TTS_PROVIDER!r})."
    )


async def _synthesize_fish(text: str, voice: str | None = None) -> bytes:
    """Fish Audio TTS. POST /v1/tts with the model in a header; returns MP3 bytes."""
    headers = {
        "Authorization": f"Bearer {config.FISH_API_KEY}",
        "Content-Type": "application/json",
        # Fish selects the model version via this header (e.g. "s1", "s2-pro").
        "model": config.FISH_MODEL,
    }
    payload: dict = {
        "text": text,
        "format": "mp3",
        "mp3_bitrate": 128,
        "normalize": True,   # tidy punctuation/numbers for natural speech
        # "balanced" starts returning audio sooner than "normal" at a
        # quality cost nobody has ever noticed in a spoken sentence. The
        # voice is the slowest link in the turn, so this is the cheapest
        # second available.
        "latency": "balanced",
    }
    # A chosen voice from the Fish library; omit to use Fish's default voice.
    chosen = voice or config.FISH_VOICE_ID
    if chosen:
        payload["reference_id"] = chosen

    async with httpx.AsyncClient(timeout=60.0) as http:
        resp = await http.post(_FISH_API_URL, headers=headers, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(
                f"Fish Audio TTS failed ({resp.status_code}): {resp.text[:300]}"
            )
        return resp.content


async def _synthesize_openai(text: str, voice: str | None = None) -> bytes:
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


async def _synthesize_yandex(text: str, voice: str | None = None) -> bytes:
    """Yandex SpeechKit. Form-encoded, not JSON. Returns MP3 bytes.

    Emotion is the one fiddly part — see `_yandex_takes_emotion`. The rule
    there covers what the documentation says; the retry below covers what the
    API actually does, because a config detail must never be the reason a
    lonely person's friend goes silent.
    """
    global _yandex_drop_emotion

    speaking_as = voice or config.YANDEX_VOICE

    def form(with_emotion: bool) -> dict:
        data = {
            "text": text,
            "lang": "ru-RU",
            "voice": speaking_as,
            "speed": config.YANDEX_SPEED,
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
