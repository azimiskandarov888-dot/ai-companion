"""HE HAS A THROAT — the small physical facts that make a voice sound lived in.

A cough dropped into a sentence because it was time for a cough is decoration,
and decoration is what makes a synthetic voice unsettling rather than warm. The
research on non-verbal vocalisations says the quality of one depends not on
whether it is present but on its «intensity, duration, expressive function, and
connection with the surrounding speech»; the work on behavioural realism in
agents finds the uncanny valley is reached by realism that does not cohere.

So nothing here decides to cough. This file models two small physical states that
rise from things that actually happened, and hands them to him as FACTS about
his own throat. What he does about them is his.

── THE RULE EVERYTHING HERE OBEYS ──────────────────────────────────────────

    A non-verbal must have a CAUSE that existed before it
    and a CONSEQUENCE that outlasts it.

Miss the cause and it is random. Miss the consequence and it is a sound effect.
A real cough is the end of ten minutes of talking and the start of two minutes
of a voice that has not quite come back — and it is that second half, the part
nobody thinks to build, that makes the first half believable.

── WHAT RISES, AND FROM WHAT ───────────────────────────────────────────────

    throat   from talking, and faster from laughing. A cough relieves it and
             leaves him hoarse for a few minutes.
    tired    from a conversation that has gone on. A yawn does NOT fix it,
             which is exactly why one yawn tends to be followed by another.

Both fade on their own between conversations, computed when read — the same
memoryless decay as feeling.py, so nothing has to run while nobody is talking
and somebody who returns next morning gets a friend who has rested.

── THE SNEEZE, HONESTLY ────────────────────────────────────────────────────

There is no state that predicts a sneeze, and pretending otherwise would be
worse than not having one. A sneeze IS random — that is the true model of it.
What is not random is the ten seconds after: the sniff, the «извини», the
thread picked back up. So it is rolled rarely by code rather than accumulated,
and the block that announces it is mostly about the aftermath. The realism
lives in the consequence, which is where it lives for the other two as well.
"""

from __future__ import annotations

import random
import re
import time

from . import db

#: Everything below is 0..1. Zero is a man who has said nothing today.
DIMS = ("throat", "tired")

#: HOW FAST A VOICE OF THIS AGE TIRES — and the reason this file cannot be the
#: same for everyone.
#:
#: The companion is invented per person and may be any age: matchmaker.py writes
#: «34 года» as readily as «87 лет», because the people this app is for are a
#: lonely teenager and a middle-aged man living alone as much as they are an
#: eighty-year-old. Without this, a thirty-four-year-old crane operator got the
#: throat of an eighty-seven-year-old — coughing his way through a conversation
#: for no reason a listener could name, which is exactly the incoherent realism
#: that reads as uncanny.
#:
#: A smooth ramp rather than brackets: nothing happens to a throat at a
#: birthday. 25 → 0.3, 55 → 0.8, 85 → 1.3.
_RATE_AT_25 = 0.3
_RATE_PER_YEAR = 1.0 / 60.0
_RATE_FLOOR, _RATE_CEILING = 0.3, 1.3

#: When the age cannot be read at all. Deliberately toward the young end,
#: because the two mistakes are not equal: too low and an old man simply coughs
#: less than he might, which nobody notices; too high and a young man coughs
#: like an old one, which is the bug this constant exists to prevent.
_RATE_UNKNOWN = 0.55

_YEARS = re.compile(r"\d{1,3}")


def wear_rate(age) -> float:
    """How hard talking is on THIS companion's voice. 0.3 young … 1.3 old."""
    found = _YEARS.search(str(age or ""))
    if not found:
        return _RATE_UNKNOWN
    years = int(found.group(0))
    if not 5 <= years <= 120:          # a typo, not a person
        return _RATE_UNKNOWN
    rate = _RATE_AT_25 + (years - 25) * _RATE_PER_YEAR
    return max(_RATE_FLOOR, min(_RATE_CEILING, rate))

#: What one spoken turn does, BEFORE the age rate multiplies it. These numbers
#: were set by walking a conversation through and reading what came out, not by
#: taste — the first draft crossed from «nothing» to «coughing» in six turns for
#: an old companion, which skipped the clearing-the-throat step almost entirely
#: and made a body with two states instead of three.
#:
#: Where they land now, counting turns of his:
#:                     87 лет          31 год
#:   clears throat     around 10       around 40
#:   throat tickles    around 14       around 60
#: — a long warm evening for the old man, an exceptional one for the young.
_PER_TURN_THROAT = 0.028
_PER_TURN_TIRED = 0.025

#: Laughing is harder on a throat than talking, worth about three turns of it.
#: It was six, which made one good joke the whole cause of a cough.
_LAUGH_THROAT = 0.08

#: Hours. Throat clears quickly once he stops talking; tiredness lingers.
_THROAT_HALF_LIFE = 0.75
_TIRED_HALF_LIFE = 2.5

#: Below this he simply has a body and nothing is said about it, which is the
#: normal state and the common one.
NOTABLE = 0.5

#: A cough is a relief, not a cure — it takes the edge off and leaves the voice
#: sitting. Both numbers matter: too much relief and he never coughs twice, too
#: little and he coughs forever.
_COUGH_RELIEF = 0.45
HOARSE_MINUTES = 3.0

#: Chance per turn, once he is already talking. Roughly once every couple of
#: hundred turns — rare enough to be an event rather than a tic.
SNEEZE_CHANCE = 0.005

#: Below NOTABLE but above this, a throat is not a cough yet — it is the small
#: «кхм» before a sentence. Same state, same cause, one step earlier: the point
#: of having it is that a throat does not go from nothing to coughing.
CLEARING = 0.35

#: How low his own mood has to sit before it shows up in his breathing. A sigh
#: is the one non-verbal here whose cause is not physical at all — it is
#: feeling.py's valence arriving in the body, which is where a mood actually
#: goes. Passed in rather than read, so this file stays a model of a throat.
SIGH_AT = -0.6

MARK_COUGH = "//КАШЕЛЬ//"
MARK_CLEAR = "//КХМ//"
MARK_YAWN = "//ЗЕВОК//"
MARK_SNEEZE = "//ЧИХ//"
MARK_SIGH = "//ВЗДОХ//"
MARKERS = (MARK_COUGH, MARK_CLEAR, MARK_YAWN, MARK_SNEEZE, MARK_SIGH)


def _decayed(value: float, hours: float, half_life: float) -> float:
    return float(value or 0.0) * (0.5 ** (hours / half_life))


def state(user_id: str) -> dict:
    """How his body is right now — stored values, faded by the time since.

    A person with no row has a body that has done nothing yet, which is the
    right answer and not a missing one.
    """
    with db.connect() as conn:
        row = conn.execute(
            "SELECT throat, tired, hoarse_ts, ts FROM body WHERE user_id=?",
            (user_id,),
        ).fetchone()
    if not row:
        return {"throat": 0.0, "tired": 0.0, "hoarse": False}

    hours = max(0.0, (time.time() - (row["ts"] or 0.0)) / 3600.0)
    hoarse_for = (time.time() - (row["hoarse_ts"] or 0.0)) / 60.0
    return {
        "throat": _decayed(row["throat"], hours, _THROAT_HALF_LIFE),
        "tired": _decayed(row["tired"], hours, _TIRED_HALF_LIFE),
        "hoarse": bool(row["hoarse_ts"]) and hoarse_for < HOARSE_MINUTES,
    }


def _write(user_id: str, throat: float, tired: float, hoarse_ts: float | None) -> None:
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO body (user_id, throat, tired, hoarse_ts, ts) VALUES (?,?,?,?,?)"
            " ON CONFLICT(user_id) DO UPDATE SET throat=excluded.throat,"
            " tired=excluded.tired, hoarse_ts=excluded.hoarse_ts, ts=excluded.ts",
            (user_id, max(0.0, min(1.0, throat)), max(0.0, min(1.0, tired)),
             hoarse_ts, time.time()),
        )


def spoke(user_id: str, laughed: bool = False, age=None) -> None:
    """One more turn of talking. Called after he replies, never before.

    This is the entire cause side of a cough: it did not come from a die roll,
    it came from him having talked for twenty minutes, and it will not arrive
    until he has — and for a young companion, not even then. `age` is his own,
    from his persona; see wear_rate.
    """
    rate = wear_rate(age)
    now = state(user_id)
    throat = now["throat"] + (_PER_TURN_THROAT + (_LAUGH_THROAT if laughed else 0.0)) * rate
    _write(user_id, throat, now["tired"] + _PER_TURN_TIRED * rate, _hoarse_ts(user_id))


def _hoarse_ts(user_id: str) -> float | None:
    with db.connect() as conn:
        row = conn.execute(
            "SELECT hoarse_ts FROM body WHERE user_id=?", (user_id,)
        ).fetchone()
    return row["hoarse_ts"] if row else None


def coughed(user_id: str) -> None:
    """He coughed. Take the edge off, and let his voice sit for a few minutes.

    The second half is the point. A cough that changes nothing afterwards is a
    sound effect; a cough followed by a voice that has not quite come back is a
    throat.
    """
    now = state(user_id)
    _write(user_id, now["throat"] - _COUGH_RELIEF, now["tired"], time.time())


def yawned(user_id: str) -> None:
    """He yawned — and is no less tired for it, which is why they come in twos."""
    now = state(user_id)
    _write(user_id, now["throat"], now["tired"], _hoarse_ts(user_id))


def clear(user_id: str) -> None:
    with db.connect() as conn:
        conn.execute("DELETE FROM body WHERE user_id=?", (user_id,))


def read_markers(reply: str, user_id: str) -> str:
    """Apply what he just did to his body, and take the markers out of the text.

    They never survive this: not into the audio, not into the log, not into the
    diary — the same contract the farewell marker has. A marker that reached the
    voice would be READ ALOUD, and «две косые черты кашель» is the single worst
    sound this feature could make.
    """
    said = reply or ""
    if MARK_COUGH in said:
        coughed(user_id)
    if MARK_YAWN in said:
        yawned(user_id)
    for mark in MARKERS:
        said = said.replace(mark, "")
    # Two spaces where a marker stood, and a space before punctuation, are the
    # visible seams of having removed something.
    while "  " in said:
        said = said.replace("  ", " ")
    for sign in (",", ".", "!", "?", "…", ":", ";"):
        said = said.replace(f" {sign}", sign)
    return said.strip()


#: Written laughter, which is harder on a throat than talking is. Deliberately
#: only what he TYPED — a laugh detected from her side would be his throat
#: reacting to her mood, which is the mirror this codebase keeps refusing.
_LAUGHTER = ("ха-ха", "хаха", "ха!", "хех", "хо-хо", "гы", "ахах")


def laughed_in(reply: str) -> bool:
    low = (reply or "").lower()
    return any(mark in low for mark in _LAUGHTER)


def block(user_id: str, may_sneeze: bool | None = None, valence: float = 0.0) -> str:
    """What he is told about his own body. Empty while it has nothing to say.

    Facts, never instructions. «В горле першит» is a thing he knows about
    himself; when and whether that becomes a cough is his, because he is the one
    who can tell whether this sentence is the place for it — and a sentence
    somebody is halfway through telling you about their dead wife never is.
    """
    now = state(user_id)
    sneeze = random.random() < SNEEZE_CHANCE if may_sneeze is None else may_sneeze

    lines: list[str] = []
    if now["hoarse"]:
        lines.append(
            "Ты только что кашлянул, и голос ещё не вернулся — сипит. Это "
            "слышно ещё пару минут, и это нормально: не извиняйся второй раз."
        )
    elif now["throat"] >= NOTABLE:
        lines.append(
            "В горле першит — ты сегодня много говорил."
            + (" Сильно." if now["throat"] >= 0.8 else "")
        )
    elif now["throat"] >= CLEARING:
        # One step before a cough, from the same cause. A throat does not go
        # from nothing straight to coughing, and a companion whose only two
        # states are «fine» and «coughing» has a switch, not a body.
        lines.append("Голос чуть сел — хочется прочистить горло.")
    if now["tired"] >= NOTABLE:
        lines.append(
            "Тебя клонит в сон"
            + (", глаза слипаются." if now["tired"] >= 0.8 else ".")
        )
    if valence <= SIGH_AT:
        lines.append("И вздыхается — само, без повода. Ты сегодня и правда невесёлый.")
    if sneeze:
        lines.append("Ты сейчас чихнул. Не объясняй почему — просто чихнул.")

    if not lines:
        return ""

    how = ["ТВОЁ ТЕЛО СЕЙЧАС (это про тебя, не про него):"] + lines
    can = [f"кашлянуть ({MARK_COUGH})", f"кхмкнуть ({MARK_CLEAR})",
           f"зевнуть ({MARK_YAWN})"]
    if valence <= SIGH_AT:
        can.append(f"вздохнуть ({MARK_SIGH})")
    if sneeze:
        can.append(f"чихнуть ({MARK_SNEEZE})")
    how.append(
        "Это не команда что-то сделать. Это просто так есть. Захочешь — можно "
        + ", ".join(can)
        + ". Метку ставь прямо там, где это случилось в речи."
    )
    how.append(
        "ГЛАВНОЕ — КОГДА. Тело не встревает в важное. Кашляют на своей фразе, "
        "между делом, а не посреди того, как человек рассказывает про больное. "
        "Ему тяжело — тело подождёт, оно умеет."
    )
    how.append(
        "И не объявляй об этом. Не «что-то я закашлялся», не «ох, простите». "
        "Кашлянул — и говоришь дальше с того же места. Один раз буркнуть "
        "«извини» можно, если перебил сам себя."
    )
    return "\n".join(how)
