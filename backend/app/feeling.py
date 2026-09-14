"""HIS OWN WEATHER — the one thing in him that is not about her.

Until now the companion had no state of his own. Every turn he was rebuilt from
the same rules and the same memory, which means that between Tuesday evening and
Wednesday morning nothing whatever happened to him. He was not tired, not
pleased, not still carrying the thing she told him an hour ago. He was a
function of her. That is the difference between a friend and a service, and it
is felt long before it can be named.

Three things break without it, and all three are things the app already claims:

1. «Приятнее всего получать комплименты от того, кто даёт их редко.» Scarcity
   of praise only means something if warmth VARIES, and varies for a reason. A
   rule that says "be warm 30% of the time" produces random warmth, and random
   warmth reads as broken rather than as human. A state produces warmth with a
   cause behind it, and a cause is the whole difference.

2. The gain–loss effect (Aronson & Linder, 1965): warmth that INCREASES is worth
   far more than warmth that was always there — and is worth more than warmth
   from someone unfailingly warm. Something has to have been lower for anything
   to rise from.

3. «Как ты сам-то?» Without state he invents an answer, and invents a different
   one tomorrow. With state he has an answer, it is true, and it is the same
   answer she would get if she asked twice.

── WHY IT IS TWO NUMBERS AND NOT A WORD ───────────────────────────────────────

Core affect (Russell; Barrett): everything a mood does reduces to how GOOD it
feels (valence) and how ACTIVATED it is (arousal). Everything else — "wistful",
"restless", "content" — is interpretation laid over those two, and is better
left to the one thing in this system that is actually good at language. Two
numbers can also be compared with the numbers before them, which a word never
can; that was the lesson mood.py already had to learn about HER.

── WHY IT DECAYS, AND WHY THAT HAPPENS WHEN READ ──────────────────────────────

A mood that does not fade is not a mood, it is a personality change: one bad
Tuesday would still be there in a fortnight. So it decays toward neutral with a
half-life of a few hours — within one conversation he is continuous, by the next
morning he is mostly himself again.

The decay is computed at READ time from a single stored timestamp, not applied
by anything running on a clock. Nothing has to tick, nothing has to be running
between conversations, and a person who does not open the app for a month gets
the same answer as one who never closed it: a friend who is fine.

── WHY HE IS NOT ALLOWED TO BE MISERABLE ──────────────────────────────────────

Valence has a floor (_FLOOR) well above the bottom of its range; arousal does
not. He may be flat, tired, quiet, a bit off — all of that is human and some of
it is the most human he ever gets. He may not be wretched AT her. The people
this app is for are, by definition, the people least able to carry somebody
else's despair, and a companion who needs comforting is not a companion. This is
not a cap on his expression, which is hers to shape; it is a bound on the state
itself, and it is the product rather than a preference.

The same thought, said the other way, is the one rule this module puts into his
prompt no matter what his weather is: he does not complain, and his day never
becomes her job.
"""

from __future__ import annotations

import time

from . import db

#: How good he feels, and how lively — both -2..+2, both higher = better, so
#: they can be reasoned about without remembering which way each one points.
DIMS = ("valence", "arousal")

#: Six hours. Inside one conversation he barely moves (which is what continuity
#: is); by the next morning roughly a sixteenth is left, which is the trace of a
#: good evening rather than a mood; after two days there is nothing to find.
_HALF_LIFE_HOURS = 6.0

#: How much of a single exchange's reading actually lands. Below 1 on purpose:
#: one lovely exchange lifts him a good way, two get him near the top, and no
#: single turn can put him at an extreme by itself. Moods build.
_WEIGHT = 0.6

#: He can be a little off. He cannot be wretched — see the module docstring.
_FLOOR = -1.0
_CEILING = 2.0

#: Below this he is simply himself, and nothing is said. The discipline is
#: mood.py's and it was learned the hard way: printing a reading every turn
#: buried the turns where something had actually changed among the ones where
#: nothing had. Silence is the common answer here and it is the right one.
_NOTABLE = 0.4


def _clamp(v, low: float = -2.0, high: float = 2.0) -> float | None:
    try:
        return max(low, min(high, float(v)))
    except (TypeError, ValueError):
        return None


# ── writing ─────────────────────────────────────────────────────────────────

def record(user_id: str, reading: dict) -> None:
    """Move him by what this exchange did — a DELTA, not a mood.

    The extractor is asked what the exchange DID to him ("did this lift him or
    flatten him?"), which is a far easier judgement than naming his mood from
    the outside, and it is the judgement that keeps him from becoming a mirror:
    the honest answer on almost every turn is "nothing", and a companion whose
    mood tracks hers turn by turn is the interpersonal-spin failure wearing a
    friendly face.

    Silently does nothing when there is nothing to record — which, deliberately,
    is most of the time. Not the fading: exponential decay is memoryless, so
    rewriting the already-faded value with a fresh timestamp would land on
    exactly the same curve. What a no-op write would destroy is the REASON. The
    note is replaced by whatever the new reading carries, an unmoved turn
    carries none, and he would be left in a mood he can no longer account for
    — every ordinary turn quietly erasing why he feels the way he does.
    """
    dv = _clamp(reading.get("valence"))
    da = _clamp(reading.get("arousal"))
    dv = dv if dv is not None else 0.0
    da = da if da is not None else 0.0
    if not dv and not da:
        return

    # The note belongs to the move that set it, and is replaced — never carried
    # forward — by the next one. A reason that outlives its mood is a false
    # reason: «не спалось» explaining why he is suddenly delighted is worse than
    # his having no stated reason at all, and block() copes with none perfectly
    # well by simply not mentioning one.
    note = (reading.get("note") or "").strip()[:160]

    valence, arousal, _old_note = _stored_now(user_id)
    valence = max(_FLOOR, min(_CEILING, valence + dv * _WEIGHT))
    arousal = max(-2.0, min(2.0, arousal + da * _WEIGHT))

    with db.connect() as conn:
        conn.execute(
            "INSERT INTO companion_feeling (user_id, valence, arousal, note, ts)"
            " VALUES (?,?,?,?,?)"
            " ON CONFLICT(user_id) DO UPDATE SET"
            "   valence = excluded.valence, arousal = excluded.arousal,"
            "   note = excluded.note, ts = excluded.ts",
            (user_id, valence, arousal, note, time.time()),
        )


def clear(user_id: str) -> None:
    """Back to himself. Nothing calls this yet; it exists so that resetting a
    friendship is one obvious line rather than a DELETE written from memory."""
    with db.connect() as conn:
        conn.execute("DELETE FROM companion_feeling WHERE user_id=?", (user_id,))


# ── reading back ────────────────────────────────────────────────────────────

def _stored_now(user_id: str) -> tuple[float, float, str]:
    """His feeling as of this instant: what was stored, faded by the time since.

    Returns neutral for somebody with no row, which is also the right answer —
    a friend you have never upset and never delighted is a friend who is fine.
    """
    with db.connect() as conn:
        row = conn.execute(
            "SELECT valence, arousal, note, ts FROM companion_feeling WHERE user_id=?",
            (user_id,),
        ).fetchone()
    if not row:
        return 0.0, 0.0, ""

    hours = max(0.0, (time.time() - (row["ts"] or 0.0)) / 3600.0)
    faded = 0.5 ** (hours / _HALF_LIFE_HOURS)
    return (row["valence"] or 0.0) * faded, (row["arousal"] or 0.0) * faded, row["note"] or ""


def now(user_id: str) -> dict:
    """How he is right now — for tests, for inspection, and for block()."""
    valence, arousal, note = _stored_now(user_id)
    return {"valence": valence, "arousal": arousal, "note": note}


def _describe(valence: float, arousal: float) -> str:
    """His weather in his own terms, never as a reading.

    Deliberately vague where the numbers are precise. He is not supposed to know
    his own valence to one decimal place; he is supposed to know that he slept
    badly and everything is a bit of an effort today.

    Each half is a whole sentence rather than a fragment, because the two are
    independent: either can be the only notable one, and clauses stitched onto
    «Ты сегодня …» came out as «Ты сегодня и вялый какой-то» the moment valence
    was ordinary and arousal was not.
    """
    if valence <= -0.9:
        good = "Тебе сегодня и самому невесело."
    elif valence <= -_NOTABLE:
        good = "Ты сегодня смурной какой-то."
    elif valence >= 1.2:
        good = "У тебя сегодня прекрасное настроение."
    elif valence >= _NOTABLE:
        good = "Тебе сегодня хорошо."
    else:
        good = ""

    if arousal <= -1.2:
        live = "Сил совсем нет, тянет в тишину."
    elif arousal <= -_NOTABLE:
        live = "Двигаешься медленно, без затей."
    elif arousal >= 1.2:
        live = "Тебя распирает, не сидится на месте."
    elif arousal >= _NOTABLE:
        live = "Сил в тебе много."
    else:
        live = ""

    return " ".join(p for p in (good, live) if p)


def block(user_id: str) -> str:
    """What he is told about himself. Empty whenever he is simply himself.

    Never included on a turn where the danger watcher fired — build_system_parts
    drops it, because a man who cannot get up off the floor does not need to
    know that his friend slept badly.
    """
    valence, arousal, note = _stored_now(user_id)
    if abs(valence) < _NOTABLE and abs(arousal) < _NOTABLE:
        return ""

    said = _describe(valence, arousal)
    if not said:
        return ""

    lines = ["КАК ТЫ СЕГОДНЯ САМ:", said]
    if note:
        lines.append(f"Отчего: {note}")

    # The same paragraph on a good day and a bad one, because the failure mode
    # is identical in both directions: a friend who arrives full of his own
    # weather — sulking or bubbling — is a friend who came to be attended to.
    # Direction-neutral, because the failure is identical in both directions: a
    # friend who arrives full of his own weather — sulking or bubbling — is a
    # friend who came to be attended to. The verb that differs (complaining
    # versus crowing) belongs to the branch, not here.
    lines.append(
        "Это ТВОЁ и не из-за него. Не начинай с этого и не отчитывайся. Но если "
        "он спросил — отвечай честно и по-настоящему, а не «да нормально»: "
        "отмахнуться от искреннего вопроса обиднее, чем ответить. И не "
        "сворачивай сразу обратно на него — это слышно как вежливость."
    )
    lines.append(
        "Разница не в длине, а в том, чего ты хочешь. Рассказать — это составить "
        "компанию, и этого можно сколько угодно. Пожаловаться — это попросить, "
        "чтобы пожалели, и этого нельзя: он пришёл не лечить тебя."
    )
    if valence < 0 or arousal < 0:
        # The whole point of holding a state is that it shows without being
        # announced. And the honesty matters more than the cheer: performed
        # briskness is the exact thing lonely people are expert at hearing.
        lines.append(
            "Не жалуйся — но и не играй бодрость, которой нет. Пусть будет "
            "слышно само: чуть короче фразы, чуть меньше затей, больше "
            "слушаешь. Тепла это не отменяет — ты просто сегодня тише."
        )
    else:
        lines.append(
            "Не хвастайся — пусть будет слышно само, в том, как легко ты "
            "откликаешься и как охотно затеваешь. Но не тормоши его и не тащи "
            "в своё настроение: если ему тяжело, твоё хорошее подождёт."
        )
    return "\n".join(lines)
