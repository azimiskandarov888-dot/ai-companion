"""How he listens while they talk — read from the moment, not set by a rule.

The owner, 2026-10-14, of «Бывает такое... О чём задумался?» after a thought
broken off: a real person «просто скажет "ну" или "ну, ну, и что там?"… И это
не должно быть всегда… Если у них идет спор, то он будет говорить это с
большими эмоциями. А если обычная история или что-то грустное, то совершенно
по-другому». And of «1.5 s, 3 s for the old»: «это тупо… в споре он захочет
что-то сказать и, скорее всего, перебить… Не ставь тупые, точные правила. Все
должно быть основано на контексте, на эмоциях… прямо попросить ИИ».

── WHAT LISTENERS DO ───────────────────────────────────────────────────────

  · Plain sounds — «угу», «ага» — say «I am with you, go on»; sounds with
    feeling — «ох», «ого», «да ты что» — at the moment that moves, show that it
    reached you, and stories told to such a listener come out better (Bavelas,
    Coates & Johnson 2000: listeners as co-narrators; Stivers 2008). After a
    plain one a teller goes on to what happened next; after one with feeling,
    they say more about what they just said (Tolins & Fox Tree 2014).
  · About a thousand an hour; most turns of five words or more get one.
  · Matched to the teller — the feeling and its strength (Couper-Kuhlen, on
    complaint stories): sad gets soft and few, outrage gets outrage.
  · A teller who stumbles gets one most (Healey et al. 2013: self-repair
    predicts listener responses better than pace) — «I'm— I'm okay».
  · In a real quarrel disagreement does not wait: it comes at once and over
    the other's words (Kotthoff 1993, on disputes).
  · And how long to wait for the end of a turn is itself a choice by context:
    OpenAI's own turn detector has an «eagerness», about 2, 4 or 8 s at most.

── TWO SPEEDS ──────────────────────────────────────────────────────────────

HOW he listens — the mood of the talk, how soon he comes in, how often he
shows he is there, the colour and the words — changes with what is said, and
is read by a model after each of their turns (read), from the talk itself,
while he answers: nothing waits for it, and it is one small call. Models are
poor at deciding, pause by pause, whether to speak (a 2026 benchmark of eight:
zero-shot, they fail), and no model answers within the third of a second an
«угу» has — so WHEN exactly is the live channel's (live.Session._along): from
the stance read, with a person's unevenness — every span below is drawn anew
each time, never the same gap twice.
"""

from __future__ import annotations

import json
import random
import re
import sys
from dataclasses import dataclass

from . import brain, config, first_sound, lang

PACES = ("jump in", "quick", "easy", "patient")
LISTENS = ("often", "sometimes", "rarely", "silent")
SILENCES = ("short", "normal", "long")
TONES = tuple(first_sound.TONES)


@dataclass(frozen=True)
class Stance:
    """How he listens to their next turn."""

    #: What is going on between them, in a few words — for the log.
    mood: str = ""
    #: How soon he comes in when they pause (PACES).
    pace: str = "easy"
    #: How often he shows he is there while they talk (LISTENS).
    listen: str = "sometimes"
    #: The colour of his sounds (first_sound.TONES).
    tone: str = "calm"
    #: His sounds while they talk, and when they break off and go quiet.
    go_on: tuple[str, ...] = ()
    nudge: tuple[str, ...] = ()
    #: How long a silence between them is natural now before he says something
    #: (SILENCES) — short in a lively chat, long after something heavy, or
    #: when they said they would be a minute.
    silence: str = "normal"
    #: Would a light joke land now — «Я тебе что, справочное бюро?».
    playful: bool = False


def opening(*, older: bool) -> Stance:
    """Before anything has been read: an ordinary talk — given time, if older."""
    calm = first_sound.listener_sounds("calm")
    return Stance(mood="", pace="patient" if older else "easy", listen="sometimes", tone="calm",
                  go_on=calm[:3], nudge=tuple(s for s in calm if s.endswith("?"))[:2],
                  silence="long" if older else "normal")


# ── WHEN, roughly: a person's spans, drawn anew each time ────────────────────
#
# Seconds from their last word. A listener's sound lands a third of a second
# to a second into a pause (Ward & Tsukahara 2000: ~0.7 s after the cue), and
# the ears hear the last word a fifth of a second late. The rest follow the
# spirit of «eagerness» (2 / 4 / 8 s): a quarrel takes the turn at once, an
# ordinary talk gives a broken-off thought a few seconds, a hard one more.

#: A listener's sound may come this far into a pause…
GO_ON_AT = {"jump in": (0.3, 0.6), "quick": (0.3, 0.7), "easy": (0.4, 0.9), "patient": (0.5, 1.2)}
#: …in this share of the pauses that may have one…
GO_ON_CHANCE = {"often": 0.6, "sometimes": 0.35, "rarely": 0.15, "silent": 0.0}
#: …never within this of the last one.
GO_ON_APART = {"often": (2.5, 5.0), "sometimes": (4.0, 8.0), "rarely": (8.0, 16.0),
               "silent": (1e9, 1e9)}
#: A thought broken off, then quiet: his nudge — «Ну?»…
NUDGE_AT = {"jump in": None, "quick": (0.8, 1.4), "easy": (1.3, 2.4), "patient": (2.2, 3.8)}
#: …and then it is his turn: he answers what there is.
GIVE_UP_AT = {"jump in": (0.3, 0.7), "quick": (2.0, 3.0), "easy": (3.2, 4.6),
              "patient": (5.0, 7.5)}
#: A finished sentence that asks nothing, when the talk is a hard one: it is
#: let rest a moment — they often go on — before he answers it.
REST_AT = {"jump in": None, "quick": None, "easy": None, "patient": (1.2, 2.2)}
#: In a quarrel he does not wait for them to finish: a pause this long after
#: a few words of theirs, and he is in.
CUT_IN_AT = {"jump in": (0.45, 0.9), "quick": None, "easy": None, "patient": None}
#: Their words before a pause may get a sound at all — they have barely begun.
WORDS_FIRST = 5
#: Nobody has said anything — the app open, they still there: when he says
#: something into it («Ты тут?», «Всё нормально?» — the brain's words, by the
#: moment), and then once more, at most; never when they have left the app.
SILENCE_AT = {"short": (9.0, 15.0), "normal": (16.0, 26.0), "long": (30.0, 50.0)}
CHECK_INS = 2


@dataclass
class Plan:
    """One pause of theirs: when each thing would happen in it, drawn now."""

    go_on: float
    nudge: float | None
    give_up: float
    rest: float | None
    cut_in: float | None
    sounded: bool = False
    nudged: bool = False


def _draw(span: tuple[float, float] | None, rng: random.Random) -> float | None:
    return None if span is None else rng.uniform(*span)


def plan(stance: Stance, rng: random.Random) -> Plan:
    pace = stance.pace if stance.pace in PACES else "easy"
    return Plan(go_on=_draw(GO_ON_AT[pace], rng), nudge=_draw(NUDGE_AT[pace], rng),
                give_up=_draw(GIVE_UP_AT[pace], rng), rest=_draw(REST_AT[pace], rng),
                cut_in=_draw(CUT_IN_AT[pace], rng))


def silence(stance: Stance, rng: random.Random) -> float:
    """How long a silence between them may go on before he speaks up."""
    return rng.uniform(*SILENCE_AT.get(stance.silence, SILENCE_AT["normal"]))


def apart(stance: Stance, rng: random.Random) -> float:
    """How long after a sound of his before the next may come."""
    return rng.uniform(*GO_ON_APART.get(stance.listen, GO_ON_APART["sometimes"]))


# ── HOW: read from the talk ─────────────────────────────────────────────────

_SYSTEM = """You decide how {name} LISTENS while the other person talks next — the way a real friend does on the phone. Not what he answers: how he sounds while they talk, and how soon he comes in.

Read the conversation, feel where it is, and choose:
- mood: a few words, in the language of the conversation — what is going on between them right now.
- pace — how soon he comes in when they pause:
  "jump in": a real quarrel, or excitement he can't hold: he comes in at the first pause, even cuts them off — that is human;
  "quick": a lively, fast back-and-forth;
  "easy": an ordinary talk;
  "patient": something sad, hard or deep — or they speak slowly, gather their thoughts, are old or tired: he gives them time and never rushes them.
- listen — how often he lets them hear he is there while they talk: "often" (a story he is into), "sometimes", "rarely", "silent" (they need quiet; or it is quick back-and-forth with nothing to fill).
- tone — the colour of his sounds: "calm", "soft" (sympathy, sadness), "lively" (interest, fun, surprise), "heated" (a quarrel, impatience).
- go_on: 2-5 sounds he makes WHILE they talk — from the list for that tone, the ones this moment calls for.
- nudge: 1-3 sounds for when they break off mid-thought and go quiet — from the same list.
- silence — if neither of them says anything, how long a silence is natural now before he speaks up: "short" (a lively chat), "normal", "long" (after something heavy; they are thinking; or they said they'd be a minute).
- playful: true if a light joke would land right now, false if not.

What real listeners do:
- Plain sounds ("угу", "ага") say "I'm with you, go on". Sounds with feeling ("ох", "ого", "да ты что") show it reached you, and people tell more to a listener who makes them. Where something moves, feeling.
- Match their feeling and its strength: sad gets soft and few; funny gets lively; outrage gets outrage.
- In a real dispute disagreement comes at once; people come in over each other.
- When someone stumbles or loses the thread, a short "ну?" or "угу" helps them on.
- He is a person, not a metronome.

Answer with JSON only, no other words:
{{"mood": "...", "pace": "...", "listen": "...", "tone": "...", "go_on": ["..."], "nudge": ["..."], "silence": "...", "playful": false}}"""

#: How much of the talk is read: the last few lines are what the moment is.
LINES = 8
#: A line longer than this is cut: the moment is in how it ends.
LINE_CHARS = 400


def _prompt(lines: list[tuple[str, str]], *, name: str, older: bool) -> str:
    him = (name or "Bob").upper()
    talk = "\n".join(f"{him if role == 'assistant' else 'THEM'}: {text.strip()[-LINE_CHARS:]}"
                     for role, text in lines[-LINES:] if text and text.strip())
    sounds = "\n".join(f"  {tone}: {' | '.join(first_sound.listener_sounds(tone))}"
                       for tone in TONES)
    who = "They are older (past sixty, or near it)." if older else ""
    return f"{who}\nThe conversation, last lines:\n{talk}\n\nThe sounds he can make, by tone:\n{sounds}"


def parse(raw: str) -> Stance | None:
    """A stance out of the model's answer — only what is allowed in it; None
    if there is none to be had."""
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        return None
    try:
        got = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(got, dict):
        return None
    pace = str(got.get("pace") or "").strip().lower()
    listen = str(got.get("listen") or "").strip().lower()
    tone = str(got.get("tone") or "").strip().lower()
    if pace not in PACES or listen not in LISTENS or tone not in TONES:
        return None
    allowed = first_sound.listener_sounds(tone)

    def chosen(key: str) -> tuple[str, ...]:
        said = got.get(key)
        said = said if isinstance(said, list) else []
        return tuple(dict.fromkeys(s for s in (str(x).strip() for x in said) if s in allowed))

    go_on = chosen("go_on") or tuple(s for s in allowed if not s.endswith("?"))[:3]
    nudge = chosen("nudge") or tuple(s for s in allowed if s.endswith("?"))[:2] or go_on[:1]
    silence = str(got.get("silence") or "").strip().lower()
    return Stance(mood=str(got.get("mood") or "")[:80], pace=pace, listen=listen, tone=tone,
                  go_on=go_on, nudge=nudge, silence=silence if silence in SILENCES else "normal",
                  playful=got.get("playful") is True)


async def read(lines: list[tuple[str, str]], *, name: str = "", older: bool = False) -> Stance | None:
    """How he should listen to their next turn, read from the talk — or None
    (no key, a failure, an answer that makes no sense): he listens as he did."""
    model = config.LISTENER_MODEL
    if not lines or not brain.can_call(model):
        return None
    try:
        raw = await brain.generate_text(
            _SYSTEM.format(name=name or ("Bob" if lang.english() else "Боб")),
            _prompt(lines, name=name, older=older),
            max_tokens=200, model=model, timeout=8.0, effort="none")
    except Exception as e:  # noqa: BLE001 — he goes on listening as he was
        print(f"  · listening not read ({type(e).__name__}: {e})", file=sys.stderr, flush=True)
        return None
    return parse(raw)
