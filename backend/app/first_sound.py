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

  a pause in their turn          «м-м» — a listener's sound, now and then. If
  (ears: «похоже, договорил»)    they carry on, that is exactly what it was.
                                 Only when he may be talked over (duplex):
                                 otherwise the microphone is closed while he
                                 makes a sound, and their next words would be lost.
  the end of their turn          most often his BREATH, the way somebody about
                                 to speak takes one; sometimes a word an answer
                                 opens with — «да…», «ну…» after something told,
                                 «ну…» after a question, «хм…», «так…» before
                                 something he must weigh; sometimes nothing
                                 (SHARES). An older friend breathes more, and
                                 mostly deep (DEEP_SHARE).
  his words still not there      one more — a word, once
  LATE seconds after

The owner, 2026-10-08, of the «м-м» before every answer: «even when it's not
logically belong there… Maybe we can have some other voice lines like "nuuu",
"da..." Sometimes maybe we don't use it at all. But most of the time, I want
to use the breathing effect. Especially when we talk to someone old».

Never before a goodbye, never twice within SPACING, never when he speaks
first, never in a search turn — that one says «сейчас гляну» (live._FILLERS).

── IN HIS OWN VOICE, MADE ONCE ─────────────────────────────────────────────

Each sound is made by the voice that says his words, TAKES times — a voice
never says it the same way twice, and neither should he — when the
conversation opens, and kept: playing one costs nothing and waits for
nothing. The silence a voice puts before and after a word is cut off: it would
only be more gap.

His breath is Gemini's own `<breath>` (body.MARK_BREATH, tts.GEMINI_SOUNDS).
Most takes come out a quiet half-second to a second; now and then one runs for
seconds, loud — so a take of it is kept only when it is short and quiet
(_kept), and made again when it is not. (Fish's «[inhale]» came out voiced,
2026-10-02: a voice with no breath of its own gets words instead.)

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
import math
import operator
import random
import re
import sys
import wave
from collections.abc import Container

from . import body, config, lang, tts

#: A listener's sound — in a pause of theirs.
LISTENING = ("М-м…",)
#: His breath before he answers — the sound he makes most; and the deeper,
#: longer one of an older friend, or of a friend to somebody past sixty.
BREATH = body.MARK_BREATH
EXHALE = body.MARK_EXHALE
DEEP_BREATH = body.MARK_DEEP_BREATH
#: Words an answer opens with: after something told, after a plain question,
#: and before an answer to something they asked him to weigh.
STATEMENT = ("Да…", "Ну…")
QUESTION = ("Ну…",)
THINKING = ("Хм…", "Так…", "Ну…")
#: While he looks something up — somebody searching, half to himself (the
#: owner, 2026-10-14: «когда ищет, как и любой настоящий человек… "Эм..."
#: "Так, ну тут это, а тут это..."»).
SEARCHING = ("Эм…", "Так-так…", "Так, тут…", "Ага…", "Сейчас-сейчас…", "Ну-ка…")
#: The same in an English conversation (lang.py) — said by an English voice,
#: which would read «Так…» as a word.
LISTENING_EN = ("Mm…",)
STATEMENT_EN = ("Yeah…", "Well…")
QUESTION_EN = ("Well…",)
THINKING_EN = ("Hmm…", "So…", "Well…")
SEARCHING_EN = ("Um…", "Let's see…", "Okay, so…", "Uh-huh…", "Hang on…", "Hmm, here…")
#: How his breath is shown on the phone, where his words are.
BREATH_SHOWN, BREATH_SHOWN_EN = "(вдох)", "(breath)"
EXHALE_SHOWN, EXHALE_SHOWN_EN = "(выдох)", "(breath out)"
#: …all of which are breaths, wherever they are shown.
BREATHS_SHOWN = frozenset({BREATH_SHOWN, BREATH_SHOWN_EN, EXHALE_SHOWN, EXHALE_SHOWN_EN})
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
#: A listener's sounds while they talk, and when they stall — by the colour
#: they are said in. listening.py chooses the colour and the words for the
#: moment, from the talk itself. Short, on purpose — the owner, 2026-10-14:
#: «он просто скажет "ну" или "ну, ну, и что там?"… что-то короткое, чтобы
#: дать ему понять, что он слушает». Plain ones say «go on»; ones with feeling
#: in them — «Ох…», «Да ты что!» — show that it reached him (Bavelas et al.
#: 2000: listeners as co-narrators; Stivers 2008).
LISTENER = {
    "calm": ("Угу.", "Ага.", "Да-да.", "Так.", "М-м.", "Ну?", "И?", "А дальше?", "И что?"),
    "soft": ("М-м…", "Ох…", "Да…", "Эх…", "Угу…", "Ну?", "И?"),
    "lively": ("Ого!", "Ничего себе!", "Да ты что!", "Ха!", "Надо же!", "Ну-ну!", "И что там?",
               "А дальше?"),
    "heated": ("Ну-ну.", "Да ну?", "Ой, да ладно.", "Хм.", "Ну конечно.", "Ну?", "Ну и?",
               "И что?"),
}
LISTENER_EN = {
    "calm": ("Mm-hm.", "Uh-huh.", "Yeah.", "Right.", "And?", "And then?", "So?"),
    "soft": ("Mm…", "Oh…", "Oh no…", "Yeah…", "Mm?", "Go on…"),
    "lively": ("Wow!", "No way!", "Really?", "Ha!", "Huh!", "And then?", "What happened?"),
    "heated": ("Oh, come on.", "Yeah, yeah.", "Hmm.", "Sure.", "So?", "And?"),
}
#: How each colour is said — told to his own voice, as his breaths are
#: (_breathing): the same «Ну?» is a different word in a quarrel and over
#: something sad. «calm» is his voice as it is.
TONES = {"calm": None,
         "soft": "quietly and gently, with sympathy — a listener's sound, barely more than a breath",
         "lively": "with lively interest and warmth, a little amused — an engaged listener",
         "heated": "impatiently, with heat, as in an argument"}
#: How many versions of each sound are made.
TAKES = 2
#: Of the ends of their turns, by what was said: the share that gets his
#: breath, and the share that gets a word — the rest get nothing, as people's
#: do not always. An older friend (OLDER_FROM) breathes more and says less.
SHARES = {"statement": (0.6, 0.2), "question": (0.6, 0.2), "thinking": (0.45, 0.4)}
SHARES_OLDER = {"statement": (0.75, 0.1), "question": (0.75, 0.1), "thinking": (0.6, 0.25)}
OLDER_FROM = 55
#: …and of an older friend's breaths, the share that are deep — the owner,
#: 2026-10-08: «чем старше, тем больше вдоха… и дольше, и сильнее». Asked, he
#: chose «чаще глубокий»: not every one deep, and not a deep one only as often
#: as any other of his thirteen (about one in three, as it had become). The
#: rest are in or out, so that they still vary.
DEEP_SHARE = 0.75
#: How often a pause in their turn gets a listener's «м-м». None now: half of
#: those pauses are the end of their turn after all, and the «м-м» became the
#: start of his answer with a silence after it — the very thing the owner
#: disliked most (2026-10-08). His breath before his words is his sound now.
CHANCE_IN_PAUSE = 0.0
#: Seconds between two sounds of his in a pause — a listener who says «м-м» at
#: every breath is not listening, he is ticking.
SPACING = 4.0
#: …and between a sound in their last pause and one at the end of the turn: the
#: «м-м» that went into the pause a moment ago was already his first sound.
SPACING_AT_END = 2.0
#: Seconds after their turn ended, with his words still not there and no
#: sound of his on its way before them, for one. None: never.
LATE: float | None = 2.2
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
    """What kind of turn this was, for his sound after it — "thinking" (a
    question he must weigh), "question", "statement" — or None for none at
    all (a goodbye, or nothing said)."""
    said = (transcript or "").strip()
    if not _words(said) or goodbye(said):
        return None
    low = said.lower().replace("ё", "е")
    if said.endswith("?"):
        return "thinking" if (_WEIGH.search(low) or _WEIGH_EN.search(low)) else "question"
    return "statement"


def in_pause(transcript: str) -> bool:
    """May a pause in this turn get a listener's sound?"""
    return len(_words(transcript)) >= PAUSE_AFTER_WORDS and not goodbye(transcript)


def _texts(kind: str) -> tuple[str, ...]:
    if kind == "breath":
        return (BREATH,)
    if kind == "deep breath":
        return (DEEP_BREATH,)
    english = lang.english()
    return {"thinking": THINKING_EN if english else THINKING,
            "question": QUESTION_EN if english else QUESTION,
            "statement": STATEMENT_EN if english else STATEMENT,
            "searching": SEARCHING_EN if english else SEARCHING,
            }.get(kind, LISTENING_EN if english else LISTENING)


def shown(text: str) -> str:
    """A sound of his as the phone shows it: his breath as «(вдох)»."""
    if text in (BREATH, DEEP_BREATH):
        return BREATH_SHOWN_EN if lang.english() else BREATH_SHOWN
    if text == EXHALE:
        return EXHALE_SHOWN_EN if lang.english() else EXHALE_SHOWN
    return text


def pick(voice: str | None, kind: str, rng: random.Random,
         avoid: str = "") -> tuple[str, int, bytes] | None:
    """One of his sounds of this kind, as (what it is, rate, PCM) — not the
    one he made last, when there is another. None until they are made."""
    ready = [t for t in _texts(kind) if _made.get((voice, t))]
    if not ready:
        return None
    fresh = [t for t in ready if shown(t) != avoid] or ready
    text = rng.choice(fresh)
    rate, pcm = rng.choice(_made[(voice, text)])
    return shown(text), rate, pcm


def breaths(voice: str | None, *, older: bool = False) -> list[tuple[str, int, bytes]]:
    """His breaths that are made, as (shown, rate, PCM) — in and out, and for
    an older friend the deep ones too."""
    kinds = (BREATH, EXHALE, DEEP_BREATH) if older else (BREATH, EXHALE)
    return [(shown(kind), rate, pcm) for kind in kinds for rate, pcm in _made.get((voice, kind), [])]


def breath(voice: str | None, rng: random.Random, *, older: bool = False,
           taken: Container[int] = ()) -> tuple[str, int, bytes] | None:
    """His breath before his words, as (shown, rate, PCM): an older friend's
    most often a deep one (DEEP_SHARE), anybody's otherwise one in or out —
    and never one of those he took last (`taken`, by the id of their PCM)
    while there is another, deep or not: «breathing cant sound identical 6
    times in a row». None while none is made."""
    every = breaths(voice, older=older)
    fresh = [b for b in every if id(b[2]) not in taken] or every
    deep = {id(pcm) for _rate, pcm in _made.get((voice, DEEP_BREATH), [])}
    wanted = older and rng.random() < DEEP_SHARE
    choices = [b for b in fresh if (id(b[2]) in deep) == wanted] or fresh
    return rng.choice(choices) if choices else None


#: …and when he jumps in — a quarrel, a story he can't wait to answer — he
#: mostly just speaks: nobody takes a calm breath to cut somebody off.
SHARES_EAGER = (0.25, 0.1)


def choose(voice: str | None, kind: str, rng: random.Random, *, older: bool = False,
           eager: bool = False, avoid: str = "") -> tuple[str, int, bytes] | None:
    """His sound at the end of a turn of this kind (at_end): his breath most
    often — more often still when `older` — a word sometimes, nothing the
    rest of the time (SHARES); mostly nothing when `eager` (listening.py:
    he is jumping in). While his breath is not made yet, a word stands in.
    Which of his breaths it is, deep or not, is taken when it is time (breath)."""
    breath, word = (SHARES_EAGER if eager else
                    (SHARES_OLDER if older else SHARES).get(kind, SHARES["statement"]))
    roll = rng.random()
    if roll < breath and (made := pick(voice, "breath", rng)):
        return made
    if roll < breath + word:
        return pick(voice, kind, rng, avoid=avoid)
    return None


def _toned(voice: str | None, tone: str) -> str | None:
    """His voice saying a listener's sound in this colour (TONES): the same
    voice, the same person, told how. His own voice for «calm»; None for a
    colour a voice cannot be told (no Gemini voice)."""
    from . import voices

    how = TONES.get(tone)
    if not how:
        return voice
    parsed = voices.parse(voice)
    if parsed is None:
        return None
    name, style = parsed
    who = re.split(r" \(|,", style or "", maxsplit=1)[0].strip() or "a person"
    return voices.key({"name": name, "style": f"{who}: {how}"})


def listener_sounds(tone: str) -> tuple[str, ...]:
    """The listener's sounds of this colour, in the language of the talk."""
    return (LISTENER_EN if lang.english() else LISTENER).get(tone, ())


def listener(voice: str | None, text: str, tone: str) -> tuple[int, bytes] | None:
    """One of his listener sounds in this colour, ready-made: (rate, PCM), a
    different take each time — or None while it is not made."""
    toned = _toned(voice, tone)
    takes = _made.get((toned, text)) if toned is not None else None
    return random.choice(takes) if takes else None


def ready(voice: str | None) -> bool:
    return any(_made.get((voice, t)) for t in _texts("listening") + _texts("breath"))


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
    # His sounds first, every take — they are wanted at once and often; then
    # one of each of his ready first words, then their second takes. On a
    # voice rationed by the minute (tts.limited) all of it is made in the
    # requests his words leave over, so it can take a while — the most useful
    # first.
    # His listener's sounds come next: they are what a talk with him sounds
    # like from its first minute (listening.py) — each in its colour.
    await _make_breaths(voice)
    sounds = list(dict.fromkeys(_texts("statement") + _texts("question") + _texts("thinking")
                                + _texts("listening") + _texts("searching")))
    reactions = [t for t in (REACTIONS_EN if lang.english() else REACTIONS) if t not in sounds]
    listening = [(toned, text) for tone in TONES if (toned := _toned(voice, tone)) is not None
                 for text in listener_sounds(tone)]
    listening = [(v, t) for v, t in dict.fromkeys(listening) if not (v == voice and t in sounds)]
    order = ([(voice, t, k) for t in sounds for k in range(TAKES)]
             + [(v, t, k) for k in range(TAKES)
                for v, t in listening + [(voice, r) for r in reactions
                                         if (voice, r) not in listening]])
    takes: dict[tuple[str | None, str], list[tuple[int, bytes]]] = {}
    failed: set[tuple[str | None, str]] = set()
    for said_by, text, take in order:
        if (said_by, text) in failed:
            continue
        try:
            kept = _load(said_by, text, take)
            for _attempt in range(ATTEMPTS if kept is None else 0):
                rate, pcm = None, b""
                async for rate, chunk in tts.stream(text, said_by, background=True):
                    pcm += chunk
                if rate and (pcm := trimmed(pcm, rate)) and _kept(text, rate, pcm):
                    kept = (rate, pcm)
                    _keep(said_by, text, take, kept)
                    break
            if kept is None:
                continue
        except Exception as e:  # noqa: BLE001 — a sound is a nicety, never a failure
            print(f"[first_sound] could not make {text!r}: {type(e).__name__}: {e}",
                  file=sys.stderr, flush=True)
            failed.add((said_by, text))
            continue
        takes.setdefault((said_by, text), []).append(kept)
        _made[(said_by, text)] = list(takes[(said_by, text)])


# ── his breaths ──────────────────────────────────────────────────────────────
#
# The owner, 2026-10-08, of the breaths the voice made from its own <breath>:
# «everytime he says "ehh" thats not real and kinda dumb. i need it to be like
# breathing. inhale or exhale. and different sounds all the time. breathing
# cant sound identical 6 times in a row… and yet again it cuts in the middle
# of the sound». Measured: of the takes kept then, half were VOICED — 0.45–0.95
# of their loud moments had a pitch (_voiced): an «э», not air — and they had
# been cut short to fit before his words. Told whom it plays as «just air, no
# voice at all», the same voice breathed: eight takes of eight unvoiced.
#
# So: a dozen of them, in and out, none voiced, none cut — and before his
# words he takes one of them (breath; an older friend most often a deep one),
# never one he has just taken.

#: (kind, how it is breathed, how many takes are kept, how long one may be)
BREATHS = (
    (BREATH, "a quiet in-breath through the nose before speaking", 6, (0.3, 1.1)),
    (EXHALE, "a soft breath out, settling before speaking", 3, (0.4, 1.4)),
    (DEEP_BREATH, "a slow, deep in-breath through the mouth before speaking", 4, (0.6, 1.6)),
)
_AIR = " — just air, no voice at all"
#: How loud each is made: quieter than his words, as breath is; the deep one
#: the strongest (the owner: «и дольше, и сильнее»).
PEAKS = {BREATH: 7000, EXHALE: 7000, DEEP_BREATH: 11000}
#: Not silence, not the full-volume noise a take now and then turns out as.
BREATH_FAINTEST, BREATH_LOUDEST = 600, 26000
#: Of its loud moments, at most this share may have a pitch: more, and it is
#: a voice, not a breath.
VOICED_AT_MOST = 0.15
#: Tries for each take kept, before it is given up on.
BREATH_TRIES_EACH = 5


def _breathing(voice: str | None, how: str) -> str | None:
    """His voice told to breathe: the same voice, playing the same person,
    told that this is air and nothing else. None for a voice that cannot be
    told whom it plays (no Gemini voice) — such a voice has no breaths."""
    from . import voices

    parsed = voices.parse(voice)
    if parsed is None:
        return None
    name, style = parsed
    who = re.split(r" \(|,", style or "", maxsplit=1)[0].strip() or "a person"
    return voices.key({"name": name, "style": f"{who}: {how}{_AIR}"})


async def _make_breaths(voice: str | None) -> None:
    """His breaths (BREATHS), made once in his voice and kept, as any sound of
    his: each take a breath (_air) or made again, BREATH_TRIES_EACH times."""
    for kind, how, count, (shortest, longest) in BREATHS:
        takes = [_load(voice, kind, k) for k in range(count)]
        breathing = _breathing(voice, how) if None in takes else None
        for take in range(count):
            for _try in range(BREATH_TRIES_EACH if breathing and takes[take] is None else 0):
                try:
                    rate, pcm = None, b""
                    async for rate, chunk in tts.stream(kind, breathing, background=True):
                        pcm += chunk
                except Exception as e:  # noqa: BLE001 — a sound is a nicety, never a failure
                    print(f"[first_sound] could not make a breath: {type(e).__name__}: {e}",
                          file=sys.stderr, flush=True)
                    breathing = None
                    break
                # Off the conversation's loop: listening for a pitch is a
                # moment of arithmetic, and his words must not wait on it.
                if rate and (pcm := trimmed(pcm, rate)) and await asyncio.to_thread(
                        _air, rate, pcm, shortest, longest):
                    takes[take] = (rate, _louder(pcm, PEAKS[kind]))
                    _keep(voice, kind, take, takes[take])
                    break
        if made := [t for t in takes if t]:
            _made[(voice, kind)] = made


def _air(rate: int, pcm: bytes, shortest: float, longest: float) -> bool:
    """Is this a breath — as long as one of its kind may be, neither silence
    nor full-volume noise, and not voiced?"""
    samples = array.array("h")
    samples.frombytes(pcm[: len(pcm) - len(pcm) % 2])
    seconds, peak = len(samples) / rate, max(map(abs, samples), default=0)
    return (shortest <= seconds <= longest and BREATH_FAINTEST <= peak <= BREATH_LOUDEST
            and _voiced(samples, rate) <= VOICED_AT_MOST)


def _voiced(samples: array.array, rate: int) -> float:
    """The share of its loud moments that have a pitch — a voice's buzz, as
    an «э» has and air has not: autocorrelation at a lag of one 80–400 Hz
    period, over 40 ms frames, at 8 kHz."""
    step = max(1, rate // 8000)
    x = samples[::step]
    sr = rate / step
    n, hop = int(sr * 0.04), int(sr * 0.02)
    lo, hi = int(sr / 400), int(sr / 80)
    frames = []
    for i in range(0, len(x) - n - hi, hop):
        frame = x[i:i + n + hi]
        mean = sum(frame) / len(frame)
        frames.append([v - mean for v in frame])
    energies = [sum(v * v for v in f[:n]) for f in frames]
    top = max(energies, default=0)
    if not top:
        return 0.0
    voiced = loud = 0
    for f, e0 in zip(frames, energies):
        if e0 < 0.01 * top:                    # (10% of the loudest, as amplitude)
            continue
        loud += 1
        head = f[:n]
        best = 0.0
        for lag in range(lo, hi):
            tail = f[lag:lag + n]
            c = sum(map(operator.mul, head, tail))
            e1 = sum(v * v for v in tail)
            if c > 0 and e1:
                best = max(best, c / math.sqrt(e0 * e1))
        voiced += best > 0.6
    return voiced / loud if loud else 0.0


#: A breath is joined in no later than this from its end — less would be a
#: puff, not a breath — and faded in over this.
JOINED_SHORTEST, JOINED_FADE = 0.3, 0.08


def joined(pcm: bytes, rate: int, seconds: float) -> bytes:
    """A breath as heard from the middle when there are only `seconds` for
    it: its last `seconds`, faded in, to its own natural end — a breath that
    began a moment earlier, not one cut off (the owner, 2026-10-08: «it cuts
    in the middle of the sound»)."""
    samples = array.array("h")
    samples.frombytes(pcm[: len(pcm) - len(pcm) % 2])
    keep = int(rate * seconds)
    if keep >= len(samples):
        return pcm
    part = samples[len(samples) - keep:]
    fade = min(int(rate * JOINED_FADE), keep)
    for i in range(fade):
        part[i] = int(part[i] * (i / fade) ** 0.5)
    return part.tobytes()


def _louder(pcm: bytes, peak: int) -> bytes:
    """The same sound with its loudest moment at `peak`."""
    samples = array.array("h")
    samples.frombytes(pcm[: len(pcm) - len(pcm) % 2])
    top = max(map(abs, samples), default=0)
    if not top:
        return pcm
    k = peak / top
    return array.array("h", (max(-32767, min(32767, int(x * k))) for x in samples)).tobytes()


#: Times a take of any other sound is made before it is given up on.
ATTEMPTS = 4
#: …and how long one may be.
SOUND_LONGEST = 3.0


def _kept(text: str, rate: int, pcm: bytes) -> bool:
    """Is this take what it should be?"""
    return len(pcm) / (2 * rate) <= SOUND_LONGEST


def _path(voice: str | None, text: str, take: int):
    """Where one take is kept — by everything that decides how it sounds."""
    model = config.GEMINI_TTS_MODEL if config.voice_provider() == "gemini" else config.FISH_MODEL
    name = hashlib.sha256(
        f"{config.voice_provider()}|{model}|{voice}|{text}|{take}|{CUT}".encode()).hexdigest()
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


#: Below this share of the loudest moment, a stretch counts as silence — low,
#: so that the end of a breath or of «ну…» dies away as it does in a room
#: instead of being cut off (the owner, 2026-10-08: «резко обрывается… звучит
#: как некачественный SFX»; and again: «cuts in the middle of the sound»).
_QUIET = 0.006
#: Silence kept before a sound, and its fade in, in seconds — no click…
_EDGE = 0.02
#: …and after it: a long, slow fade, the way a sound ends.
_TAIL = 0.15
#: How sounds are cut now — part of where they are kept (_path), so that those
#: cut the old, abrupt way are made again.
CUT = "soft-ends-2026-10-08b"


def trimmed(pcm: bytes, rate: int) -> bytes:
    """The sound without the silence a voice puts around a word, faded in
    quickly and out slowly, so that it neither clicks nor stops dead. Empty if
    it is all silence."""
    samples = array.array("h")
    samples.frombytes(pcm[: len(pcm) - len(pcm) % 2])
    if not samples:
        return b""
    floor = max(abs(s) for s in samples) * _QUIET
    if floor <= 0:
        return b""
    loud = [i for i, s in enumerate(samples) if abs(s) > floor]
    edge, tail = int(rate * _EDGE), int(rate * _TAIL)
    start, end = max(0, loud[0] - edge), min(len(samples), loud[-1] + 1 + tail)
    cut = samples[start:end]
    fade_in, fade_out = min(edge, len(cut) // 2), min(tail, len(cut) // 2)
    for i in range(fade_in):
        cut[i] = int(cut[i] * i / fade_in)
    for i in range(fade_out):
        k = (i / fade_out) ** 2              # as a sound dies away: fast, then lingering
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
