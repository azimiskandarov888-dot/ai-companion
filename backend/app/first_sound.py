"""His first sound — he gives voice at once, the way people do, while his
words are still on their way.

── WHY ─────────────────────────────────────────────────────────────────────

People answer about 0.2 s after the other stops, in every language measured
(Stivers et al., PNAS 2009), and a gap past ~0.7 s is heard as trouble coming
(Kendrick & Torreira 2015). His words come 1.6–2.3 s after the person stops:
knowing that the turn is over takes the ears ~0.6–0.9 s, and the brain's first
words about a second more (docs/LATENCY.md). People who need a moment fill it:
an «м-м», «хм», «так…» says that an answer is on its way (Clark & Fox Tree
2002). And a listener's «м-м» in a pause says «go on» (Jefferson 1984) — on
the phone it is the only sign of listening there is. The owner, 2026-10-02:
«да, сделай чтобы он сразу подавал голос».

── WHAT, AND WHEN ──────────────────────────────────────────────────────────

  a pause in their turn          «м-м» — a listener's sound. If they carry on,
  (Flux: «похоже, договорил»)    that is exactly what it was. Only when he may
                                 be talked over (duplex): otherwise the
                                 microphone is closed while he makes a sound,
                                 and their next words would be lost.
  the end of their turn          «хм…», «так…» or «м-м…» before an answer to
                                 something they asked him to weigh; «м-м…»
                                 before anything else
  his words still not there      one more, once
  LATE seconds after

Never before a goodbye, never twice within SPACING, never when he speaks
first, never in a search turn — that one says «сейчас гляну» (live._FILLERS).

── IN HIS OWN VOICE, MADE ONCE ─────────────────────────────────────────────

Each sound is made by the voice that says his words, TAKES times — a voice
never says it the same way twice, and neither should he — when the
conversation opens, and kept: playing one costs nothing and waits for
nothing. The silence a voice puts before and after a word is cut off: it would
only be more gap.

A breath before speaking would be the most neutral sound of all, and Fish has
a tag for it. Measured (2026-10-02), «[inhale]» came out VOICED — no noise,
the periodicity of a vowel — so whatever it is, it is not obviously a breath.
It is not here until the owner has heard it; adding it means a marker in
tts.SOUNDS too, since the voice is never sent a bracket it does not know.

── HIS FIRST WORD, READY TOO ───────────────────────────────────────────────

Most answers open with a reaction — «Ого,», «Понимаю.», «Ну?», «А там что?»
(the first pieces of 1,257 of his Russian replies: about a third are one of a
few dozen). Those are made ahead in his voice as well (REACTIONS), and when the
first piece of his answer is one of them, it is played as it is — at once,
instead of after the voice has made it (live._Voicing.first). The rest of the sentence
is made meanwhile, as before. The owner, 2026-10-03: he should start talking
«the same time it's thinking».

── MADE ONCE, EVER ─────────────────────────────────────────────────────────

What is made is kept on disk (DATA_DIR/sounds), by voice, words and model, so a
companion's sounds are made the first time he speaks and never again — not
in the next conversation, not after a restart.

── NEVER REMEMBERED ────────────────────────────────────────────────────────

Like the stumbles of aloud.py, these are how he sounds, not what he said. They
go to the phone, and to the echo filter (live.Session._said) so his own «м-м»
coming back from the speaker is known for his; nowhere else.
"""

from __future__ import annotations

import array
import asyncio
import hashlib
import random
import re
import sys
import wave

from . import config, lang, tts

#: A listener's sound — in a pause of theirs, and before most of his answers.
LISTENING = ("М-м…",)
#: Before an answer to something they asked him to weigh.
THINKING = ("Хм…", "Так…", "М-м…")
#: The same sounds in an English conversation (lang.py) — said by an English
#: voice, which would read «Так…» as a word.
LISTENING_EN = ("Mm…",)
THINKING_EN = ("Hmm…", "So…", "Mm…")
#: First words most of his answers open with (see the module docstring) —
#: each with its own ending, since «Ого!» and «Ого…» are said differently.
REACTIONS = ("Ого,", "Ого…", "Ого.", "Ого!", "Ой,", "Ой…", "Ой!", "Понимаю.", "Понимаю…",
             "Ничего себе.", "Ничего себе!", "Да ты что!", "Ну да,", "Ну?", "Ну…", "Что?",
             "Ага,", "Ага.", "А дальше?", "А там что?", "И что?", "Бывает.", "Круто.",
             "Это точно.", "Слушай,", "Да ладно,", "Хм,", "Правда?", "Ладно,", "Нет,",
             # …and how Gemma opens (2026-10-07): «Ох... понимаю.», «О... А в какие
             # игры?», «Да, очень.» — of 577 rehearsed replies, nine models,
             # only 2–15% opened with one of the words above.
             "Ох…", "Ох,", "О…", "О,", "Да,", "Да.", "Ха,", "Ну,", "Ах,", "Эх…",
             "Понятно.", "Ясно.", "Точно,", "Привет.")
REACTIONS_EN = ("Oh wow,", "Oh wow!", "Wow,", "Oh,", "Oh!", "Oh no,", "Yeah,", "Yeah?",
                "Really?", "What?", "And then?", "I see.", "Right,", "Hmm,", "Huh,", "Nice!",
                "No way!", "Okay,", "Well,", "Mm,",
                "Wait,", "Hey.", "Hi.", "Ah,", "Exactly.", "I get that.")
#: How many versions of each sound are made.
TAKES = 2
#: How often a finished turn gets one. Not always: people do not.
CHANCE_AT_END = 0.85
#: How often a pause in their turn gets one.
CHANCE_IN_PAUSE = 0.6
#: Seconds between two sounds of his in a pause — a listener who says «м-м» at
#: every breath is not listening, he is ticking.
SPACING = 4.0
#: …and between a sound in their last pause and one at the end of the turn: the
#: «м-м» that went into the pause a moment ago was already his first sound.
SPACING_AT_END = 2.0
#: Seconds after their turn ended, with his words still not there, for one more.
#: None: never.
LATE: float | None = 1.6
#: A pause this early in a turn is not one to fill: they have barely begun.
PAUSE_AFTER_WORDS = 3

#: (voice, text) → its takes, as (sample rate, 16-bit mono PCM).
_made: dict[tuple[str | None, str], list[tuple[int, bytes]]] = {}
_making: dict[tuple[str | None, bool], asyncio.Task] = {}

_WORD = re.compile(r"[a-zа-яё]+(?:-[a-zа-яё]+)*")
_GOODBYE = re.compile(r"\b(?:пока|давай|до свидания|до завтра|до встречи|спокойной ночи|споки|"
                      r"мне пора|пойду|бывай|увидимся|всего доброго|всего хорошего)\b")
#: A question that asks him to weigh something, not to say a fact: «Хм…» before
#: «Из Алматы» would be a man pondering where he is from.
_WEIGH = re.compile(r"\b(?:думаешь|считаешь|по-твоему|посоветуешь|советуешь|почему|зачем|"
                    r"как лучше|что лучше|что делать|как быть|а если|стоит ли|стоит)\b")
_GOODBYE_EN = re.compile(r"\b(?:bye|goodbye|good night|night night|see you|see ya|gotta go|"
                         r"got to go|have to go|i'm off|i am off|talk later|talk to you later|"
                         r"catch you later|take care)\b")
_WEIGH_EN = re.compile(r"\b(?:what do you think|do you think|you think|should i|would you|"
                       r"what would you|why|how come|which is better|what's better|"
                       r"what should|is it worth|worth it)\b")


def _words(text: str) -> list[str]:
    return _WORD.findall((text or "").lower().replace("ё", "е"))


def goodbye(transcript: str) -> bool:
    said = (transcript or "").lower().replace("ё", "е")
    return bool(_GOODBYE.search(said) or _GOODBYE_EN.search(said))


def at_end(transcript: str) -> str | None:
    """Which sound a finished turn gets — "thinking", "listening" — or None."""
    said = (transcript or "").strip()
    if not _words(said) or goodbye(said):
        return None
    low = said.lower().replace("ё", "е")
    if said.endswith("?") and (_WEIGH.search(low) or _WEIGH_EN.search(low)):
        return "thinking"
    return "listening"


def in_pause(transcript: str) -> bool:
    """May a pause in this turn get a listener's sound?"""
    return len(_words(transcript)) >= PAUSE_AFTER_WORDS and not goodbye(transcript)


def _texts(kind: str) -> tuple[str, ...]:
    if lang.english():
        return THINKING_EN if kind == "thinking" else LISTENING_EN
    return THINKING if kind == "thinking" else LISTENING


def pick(voice: str | None, kind: str, rng: random.Random,
         avoid: str = "") -> tuple[str, int, bytes] | None:
    """One of his sounds of this kind, as (what it is, rate, PCM) — not the
    one he made last, when there is another. None until they are made."""
    ready = [t for t in _texts(kind) if _made.get((voice, t))]
    if not ready:
        return None
    fresh = [t for t in ready if t != avoid] or ready
    text = rng.choice(fresh)
    rate, pcm = rng.choice(_made[(voice, text)])
    return text, rate, pcm


def ready(voice: str | None) -> bool:
    return any(_made.get((voice, t)) for t in _texts("listening"))


def reaction(voice: str | None, piece: str) -> tuple[int, bytes] | None:
    """His first piece, ready-made, if it is one of REACTIONS and has been made
    in this voice: (rate, PCM), a different take each time. None otherwise."""
    said = _normal(piece)
    for text in (REACTIONS_EN if lang.english() else REACTIONS):
        if _normal(text) == said and (takes := _made.get((voice, text))):
            return random.choice(takes)
    return None


def opener(voice: str | None, text: str) -> int:
    """Where his reply's first piece ends when it opens with one of his
    ready-made first words — however short: «Ох…», «Да,» — so that it plays
    the moment it is written instead of waiting for more words to make a
    piece the voice is asked for (tts.first_pause wants three letters). 0 when
    it does not open with one made in this voice, or not yet: only once
    something follows it, as «Ох» may still become «Охотно»."""
    best = 0
    for said in (REACTIONS_EN if lang.english() else REACTIONS):
        if not _made.get((voice, said)):
            continue
        shape = re.escape(said).replace("…", r"(?:…|\.\.\.)")
        if m := re.match(rf"\s*{shape}(?=\s)", text):
            best = max(best, m.end())
    return best


def _normal(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().replace("...", "…"))


def prepare(voice: str | None) -> asyncio.Task:
    """Make his sounds in this voice, once — in the background; a conversation
    never waits for them, it just has none until they are there."""
    key = (voice, lang.english())
    task = _making.get(key)
    if task is None or (task.done() and not ready(voice)):
        task = asyncio.create_task(_make_all(voice))
        _making[key] = task
    return task


async def _make_all(voice: str | None) -> None:
    # His sounds first — they are wanted at once; his ready first words after.
    reactions = REACTIONS_EN if lang.english() else REACTIONS
    texts = dict.fromkeys(_texts("listening") + _texts("thinking") + reactions)
    for text in texts:
        takes = []
        for take in range(TAKES):
            try:
                kept = _load(voice, text, take)
                if kept is None:
                    rate, pcm = None, b""
                    async for rate, chunk in tts.stream(text, voice):
                        pcm += chunk
                    if not (rate and (pcm := trimmed(pcm, rate))):
                        continue
                    kept = (rate, pcm)
                    _keep(voice, text, take, kept)
                takes.append(kept)
            except Exception as e:  # noqa: BLE001 — a sound is a nicety, never a failure
                print(f"[first_sound] could not make {text!r}: {type(e).__name__}: {e}",
                      file=sys.stderr, flush=True)
                break
        if takes:
            _made[(voice, text)] = takes


def _path(voice: str | None, text: str, take: int):
    """Where one take is kept — by everything that decides how it sounds."""
    model = config.GEMINI_TTS_MODEL if config.voice_provider() == "gemini" else config.FISH_MODEL
    name = hashlib.sha256(f"{config.voice_provider()}|{model}|{voice}|{text}|{take}".encode()).hexdigest()
    return config.DATA_DIR / "sounds" / f"{name[:32]}.wav"


def _load(voice: str | None, text: str, take: int) -> tuple[int, bytes] | None:
    try:
        with wave.open(str(_path(voice, text, take)), "rb") as w:
            return w.getframerate(), w.readframes(w.getnframes())
    except (OSError, EOFError, wave.Error):
        return None


def _keep(voice: str | None, text: str, take: int, made: tuple[int, bytes]) -> None:
    try:
        path = _path(voice, text, take)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(tts.wav(made[1], made[0]))
    except OSError as e:  # a sound kept is a nicety too
        print(f"[first_sound] could not keep {text!r}: {e}", file=sys.stderr, flush=True)


#: Below this share of the loudest moment, a stretch counts as silence.
_QUIET = 0.04
#: Silence kept at each end, and the fade over it, in seconds — no click.
_EDGE = 0.02


def trimmed(pcm: bytes, rate: int) -> bytes:
    """The sound without the silence a voice puts around a word, faded in and
    out so cutting it does not click. Empty if it is all silence."""
    samples = array.array("h")
    samples.frombytes(pcm[: len(pcm) - len(pcm) % 2])
    if not samples:
        return b""
    floor = max(abs(s) for s in samples) * _QUIET
    if floor <= 0:
        return b""
    loud = [i for i, s in enumerate(samples) if abs(s) > floor]
    edge = int(rate * _EDGE)
    start, end = max(0, loud[0] - edge), min(len(samples), loud[-1] + 1 + edge)
    cut = samples[start:end]
    fade = min(edge, len(cut) // 2)
    for i in range(fade):
        k = i / fade
        cut[i] = int(cut[i] * k)
        cut[-1 - i] = int(cut[-1 - i] * k)
    return cut.tobytes()


def _spoken_word(text: str) -> str:
    """«М-м…» → «мм»: the word a sound is, as the brain would spell it."""
    return "".join(_words(text)).replace("-", "")


def without_repeat(piece: str, sound: str) -> str:
    """His answer, minus a first word that only repeats the sound he has just
    made — «Хм, ну…» after «Хм…» would be a man saying «хм» twice."""
    if not sound:
        return piece
    word = _spoken_word(sound)
    m = re.match(r"\s*([A-Za-zА-Яа-яЁё]+(?:-[A-Za-zА-Яа-яЁё]+)*)[\s,.!?…—–-]*", piece)
    if not m or m.group(1).lower().replace("-", "").replace("ё", "е") != word:
        return piece
    rest = piece[m.end():]
    return rest[:1].upper() + rest[1:] if rest else ""
