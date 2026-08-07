"""How much of the day he has left, and when he falls asleep.

Two separate jobs, both enforced HERE on the server rather than in the phone
app. An app-side limit is worth nothing: a modified app ignores it, and — far
more likely — a bug in the app bypasses it while still spending real money. The
server counts the seconds and the server says no.

  1. THE DAILY ALLOWANCE. A user gets a few hours of conversation a day. Not
     rationing for its own sake: three hours a day at API prices is about $40 a
     month, which is more than the subscription. The limit exists so one person
     cannot cost more than they pay.

  2. FALLING ASLEEP. He can't tell a television from a person. Sound crosses the
     microphone threshold, he transcribes it, answers it, and the television
     says something else — all night, at roughly $2–3 an hour, filling his diary
     with things his friend never said. So if several exchanges go by that don't
     look like a conversation, he goes quiet until he's woken.

Both are said in his own voice, never as an error. A friend who needs to sleep
is more believable than a friend who is infinite.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from . import config, db

# ── the day's allowance ──────────────────────────────────────────────────────

SECONDS_PER_DAY: int = config.DAILY_SECONDS

# ── falling asleep ───────────────────────────────────────────────────────────

#: Replies in a row that didn't look like a conversation before he goes quiet.
DOZE_AFTER_STRAY_TURNS: int = 6
#: A transcript shorter than this is background noise, not someone talking.
MIN_MEANINGFUL_CHARS: int = 12
#: Once asleep, he stays asleep until woken from the app.
_asleep: set[str] = set()
_stray: dict[str, int] = {}


@dataclass
class Verdict:
    """What the server has decided about this turn."""

    allowed: bool
    #: Said in his voice when he isn't answering. Empty when he is.
    reason: str = ""
    #: Why, for the app — never shown to the user.
    code: str = ""
    seconds_left: int = 0


def _today() -> str:
    return time.strftime("%Y-%m-%d", time.localtime())


# ── counting the day ─────────────────────────────────────────────────────────


def spend(session_id: str, seconds: float) -> None:
    """Record seconds of conversation against today's allowance."""
    with db.connect() as conn:
        conn.execute(
            """
            INSERT INTO usage (session_id, day, seconds, turns)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(session_id, day) DO UPDATE SET
                seconds = seconds + excluded.seconds,
                turns   = turns + 1
            """,
            (session_id, _today(), max(0.0, seconds)),
        )


def used_today(session_id: str) -> float:
    with db.connect() as conn:
        row = conn.execute(
            "SELECT seconds FROM usage WHERE session_id = ? AND day = ?",
            (session_id, _today()),
        ).fetchone()
    return float(row["seconds"]) if row else 0.0


def seconds_left(session_id: str) -> int:
    return max(0, int(SECONDS_PER_DAY - used_today(session_id)))


# ── the decision ─────────────────────────────────────────────────────────────


def check(session_id: str) -> Verdict:
    """Called before any paid work is done for this turn."""
    if session_id in _asleep:
        return Verdict(
            allowed=False,
            reason=_line("asleep"),
            code="asleep",
            seconds_left=seconds_left(session_id),
        )

    left = seconds_left(session_id)
    if left <= 0:
        return Verdict(
            allowed=False,
            reason=_line("spent"),
            code="daily_limit",
            seconds_left=0,
        )

    return Verdict(allowed=True, seconds_left=left)


def note_turn(session_id: str, transcript: str) -> None:
    """Judge whether that turn looked like a person talking to him.

    Deliberately crude, and deliberately forgiving: one real sentence resets the
    count entirely, so a person who is quietly thinking is never cut off. It
    only trips when NOTHING has looked like conversation for several turns in a
    row, which is what a room with a television sounds like.
    """
    meaningful = len(transcript.strip()) >= MIN_MEANINGFUL_CHARS
    if meaningful:
        _stray.pop(session_id, None)
        return

    _stray[session_id] = _stray.get(session_id, 0) + 1
    if _stray[session_id] >= DOZE_AFTER_STRAY_TURNS:
        _asleep.add(session_id)
        _stray.pop(session_id, None)


def wake(session_id: str) -> None:
    """The app asks him to wake — someone has come back and tapped."""
    _asleep.discard(session_id)
    _stray.pop(session_id, None)


def is_asleep(session_id: str) -> bool:
    return session_id in _asleep


# ── what he says ─────────────────────────────────────────────────────────────


def _line(kind: str) -> str:
    russian = config.LANGUAGE.startswith("ru")
    if kind == "asleep":
        return (
            "Кажется, я задремал. Разбуди меня, когда захочешь поговорить."
            if russian
            else "I think I dozed off. Wake me when you'd like to talk."
        )
    return (
        "Я сегодня наговорился — глаза слипаются. Поговорим завтра?"
        if russian
        else "I've talked myself out for today. Tomorrow?"
    )
