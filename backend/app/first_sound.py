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

── NEVER REMEMBERED ────────────────────────────────────────────────────────

Like the stumbles of aloud.py, these are how he sounds, not what he said. They
go to the phone, and to the echo filter (live.Session._said) so his own «м-м»
coming back from the speaker is known for his; nowhere else.
"""

from __future__ import annotations

import array
import asyncio
import random
import re
import sys

from . import lang, tts

#: A listener's sound — in a pause of theirs, and before most of his answers.
LISTENING = ("М-м…",)
#: Before an answer to something they asked him to weigh.
THINKING = ("Хм…", "Так…", "М-м…")
#: The same sounds in an English conversation (lang.py) — said by an English
#: voice, which would read «Так…» as a word.
LISTENING_EN = ("Mm…",)
THINKING_EN = ("Hmm…", "So…", "Mm…")
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


def pick(voice: str | None, kind: str, rng: random.Random, avoid: str = "",
         before: str = "") -> tuple[str, int, bytes] | None:
    """One of his sounds of this kind, as (what it is, rate, PCM) — not the
    one he made last, when there is another, and never the word his answer
    `before` opens with (live.Draft voices it ahead). None until they are made."""
    ready = [t for t in _texts(kind) if _made.get((voice, t))
             and not (before and without_repeat(before, t) != before)]
    if not ready:
        return None
    fresh = [t for t in ready if t != avoid] or ready
    text = rng.choice(fresh)
    rate, pcm = rng.choice(_made[(voice, text)])
    return text, rate, pcm


def ready(voice: str | None) -> bool:
    return any(_made.get((voice, t)) for t in _texts("listening"))


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
    texts = dict.fromkeys(_texts("listening") + _texts("thinking"))
    for text in texts:
        takes = []
        for _ in range(TAKES):
            try:
                rate, pcm = None, b""
                async for rate, chunk in tts.stream(text, voice):
                    pcm += chunk
                if rate and (pcm := trimmed(pcm, rate)):
                    takes.append((rate, pcm))
            except Exception as e:  # noqa: BLE001 — a sound is a nicety, never a failure
                print(f"[first_sound] could not make {text!r}: {e}", file=sys.stderr, flush=True)
                break
        if takes:
            _made[(voice, text)] = takes


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
