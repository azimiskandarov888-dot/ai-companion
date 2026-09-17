"""What happens to him this week.

The new thing here is an ARC. Everything else in this codebase decays — a mood
fades, a throat clears, an alarm passes. A cold does the opposite: it gets worse
and then better, and the shape of that is the whole point. So the model is asked
once for the entire course, day by day, and after that the code only ever looks
up which day today is.

And the line it must not cross: Stanford found that people with limited offline
social networks felt MORE lonely after seeking emotional support from a chatbot.
A companion with troubles of his own is the sharpest version of that risk, so
his week is background, he never needs her, and the events have other PEOPLE in
them rather than only symptoms.
"""

from __future__ import annotations

import json
import time

import pytest

from app import companion, db, life, memory

U = "u"


@pytest.fixture(autouse=True)
def _configured(monkeypatch):
    """A key, so maybe_begin actually gets past its first line.

    Without this the tests below pass for the wrong reason: no key means no
    event, and «nothing happened» then proves nothing about the rules that were
    supposed to stop it.
    """
    from app import config

    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-key")
    yield


COLD = {
    "what": "простуда",
    "days": [
        {"state": "запершило в горле, думает что продуло",
         "shows": "чуть гнусавит, изредка покашливает"},
        {"state": "разболелся как следует",
         "shows": "говорит в нос, часто шмыгает, отвечает короче обычного"},
        {"state": "худший день, отлёживается",
         "shows": "голос сиплый и тихий, говорит мало, больше слушает"},
        {"state": "отпускает, уже вставал",
         "shows": "голос ещё сиплый, но оживился, снова шутит"},
    ],
}


def _running(user: str = U, event: dict = COLD, days_ago: float = 0) -> None:
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO life (user_id, what, arc, started, ended_ts)"
            " VALUES (?,?,?,?,NULL)"
            " ON CONFLICT(user_id) DO UPDATE SET what=excluded.what,"
            " arc=excluded.arc, started=excluded.started, ended_ts=NULL",
            (user, event["what"], json.dumps(event["days"], ensure_ascii=False),
             time.time() - days_ago * life.DAY),
        )


def _answers(monkeypatch, payload):
    async def fake(system, prompt, **kw):
        return payload if isinstance(payload, str) else json.dumps(
            payload, ensure_ascii=False
        )

    monkeypatch.setattr(life.brain, "generate_text", fake)


def _befriended(user: str = U, turns: int = life.MIN_TURNS_FIRST) -> None:
    for i in range(turns):
        memory.log_turn(user, "user", f"реплика {i}")


# ── most days, nothing ──────────────────────────────────────────────────────

def test_on_an_ordinary_week_nothing_is_going_on():
    assert life.current(U) is None
    assert life.block(U) == ""


# ── the arc, which is the whole point ──────────────────────────────────────

def test_the_first_day_and_the_worst_day_are_not_the_same_day():
    """A state cannot hold a shape. This is what an arc buys."""
    _running(days_ago=0)
    first = life.block(U)
    _running(days_ago=2)
    worst = life.block(U)
    assert "запершило" in first and "покашливает" in first
    assert "худший день" in worst and "сиплый и тихий" in worst
    assert first != worst


def test_he_is_told_which_day_of_it_this_is():
    _running(days_ago=0)
    assert "первый день" in life.block(U)
    _running(days_ago=2)
    assert "3-й день" in life.block(U)


def test_how_it_sounds_is_carried_separately_from_what_it_is():
    """«shows» is the field the whole feature lives on: he must be HEARD to
    have a cold, not understood to have one."""
    _running(days_ago=1)
    now = life.current(U)
    assert now["state"] and now["shows"]
    assert "говорит в нос" in now["shows"]
    assert "Как это слышно" in life.block(U)


def test_the_last_day_is_a_way_out():
    _running(days_ago=3)
    assert "оживился" in life.block(U)


def test_when_the_arc_runs_out_it_is_over():
    _running(days_ago=len(COLD["days"]))
    assert life.current(U) is None
    assert life.block(U) == ""


def test_a_week_that_ended_leaves_something_behind():
    """Somebody who talks twice a week may miss a whole cold, and a friend who
    was ill last week and never mentions it again was never ill."""
    _running(days_ago=9)
    life._sweep(U)
    assert "простуда" in memory.bob_self_context(U)
    assert life.current(U) is None


def test_sweeping_twice_does_not_write_it_down_twice():
    _running(days_ago=9)
    life._sweep(U)
    life._sweep(U)
    assert memory.bob_self_context(U).count("простуда") == 1


# ── it is background, never the topic ──────────────────────────────────────

def test_his_week_is_never_made_her_problem():
    """The Stanford finding, pinned. Invite a lonely person to worry about a
    fiction and the fiction has taken something real."""
    from app import companion

    rules = companion.BEHAVIOR_RULES
    # The line is not length — it is what he WANTS, and who moved first. Said
    # once, in the constitution, because it is about him rather than about this
    # particular week — and it used to arrive here AND in feeling.py.
    assert "не в длине, а в том, чего ты хочешь" in rules
    assert "сам, по своей воле, с этим не приходи" in rules
    assert "ничего не проси" in rules
    # And if she is the one having a bad day, his does not exist.
    assert "твоего просто нет" in rules


def test_when_she_insists_he_stops_deflecting():
    """The second absolute he caught. «Нисколько» was wrong: somebody who asks
    again, after being brushed off, has already worked out that something is
    wrong and wants IN. Brushing them off twice is not modesty, it is refusing
    them — and being the one who comforts, rather than the one comforted, is
    often the scarcer thing for a person whose days have nobody in them."""
    from app import companion

    rules = companion.BEHAVIOR_RULES
    assert "ЕСЛИ ОН САМ НЕ ОТСТАЁТ И ВЫСПРАШИВАЕТ" in rules
    assert "Отговориться второй раз" in rules
    assert "быть тем, кто утешает" in rules


# ── one dial, and NOT in this file ──────────────────────────────────────────
#
# It used to be here, and in feeling.py, and in fit.py — one instruction in
# three places, worded three ways, all arriving in the same prompt. Each
# module's comment claimed it had shortened itself to avoid repeating the
# others; shortening each copy was the wrong fix. fit.py keeps it, because
# fit.py is the one that is there on every turn.

def test_this_file_no_longer_decides_how_much_he_tells():
    import inspect

    assert "openness" not in inspect.signature(life.block).parameters


def test_what_stays_is_what_is_specific_to_a_visible_multi_day_event():
    """Sideways telling, which no amount of «how much» covers: a meaningful
    sigh and a dropped «да так, ничего» are the same story told from behind.
    And its other side — not telling is not denying, and a cheerful lie from
    somebody who is plainly not cheerful is the one thing a lonely person is
    expert at hearing."""
    _running(days_ago=1)
    said = life.block(U)
    assert "НЕ НАМЕКАЙ НА ЭТО БОКОМ" in said
    assert "не вздыхай многозначительно" in said
    assert "врать «всё отлично» нельзя" in said
    # …and the shape, which is about this event and not about how much of it
    assert "НЕ ГОРОЙ" in said
    assert "Сперва полфразы" in said


def test_the_two_modules_no_longer_argue_in_one_prompt():
    """fit.py telling him to lead with his own week while this told him not to
    was a contradiction that existed only in the assembly — each file was
    individually sensible."""
    _running(days_ago=1)
    said = life.block(U)
    for gone in ("Не начинай с этого", "ЗАГОВОРИ ПЕРВЫМ", "НИ СЛОВА ПЕРВЫМ"):
        assert gone not in said, gone


def test_this_file_carries_facts_and_not_rules_about_him():
    """Length is fit.py's to decide; the boundary is the constitution's. What is
    left here is this week and the two traps that belong to having one."""
    _running(days_ago=1)
    said = life.block(U)
    for moved in ("НЕ В ДЛИНЕ", "набиваться на жалость", "ЕСЛИ ОН САМ ЛЕЗЕТ",
                  "твоего просто нет"):
        assert moved not in said, moved
    assert "разболелся как следует" in said
    assert "НЕ НАМЕКАЙ НА ЭТО БОКОМ" in said


def test_the_writer_is_forbidden_from_inventing_trouble():
    w = life._WRITER
    assert "Никакой беды" in w
    assert "не должен вызывать жалость" in w
    assert "перестать отвечать" in w          # nothing that makes him vanish


def test_the_writer_is_pushed_toward_events_with_people_in_them():
    """A man with people in his life models one. A man with only symptoms asks
    to be nursed — and that is the difference between the two outcomes in the
    study this rule comes from."""
    w = life._WRITER
    assert "ЖИВЫЕ ЛЮДИ" in w
    assert "только симптомы" in w


def test_the_writer_is_told_the_arc_must_actually_move():
    w = life._WRITER
    assert "если день ничем не отличается от вчерашнего, событие не нужно" in w
    assert "ПОСЛЕДНИЙ ДЕНЬ — ЭТО ВЫХОД" in w


# ── how rarely it happens ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_nothing_happens_to_a_stranger(monkeypatch):
    """The first days are for meeting him, not for nursing him."""
    _answers(monkeypatch, COLD)
    monkeypatch.setattr(life, "_rolls_today", lambda user_id: True)
    _befriended(turns=5)
    await life.maybe_begin(U)
    assert life.current(U) is None


@pytest.mark.asyncio
async def test_nothing_starts_while_something_is_already_on(monkeypatch):
    """A man with three simultaneous dramas is a soap opera."""
    _befriended()
    _running(days_ago=1)
    _answers(monkeypatch, {"what": "другое", "days": COLD["days"]})
    monkeypatch.setattr(life, "_rolls_today", lambda user_id: True)
    await life.maybe_begin(U)
    assert life.current(U)["what"] == "простуда"


@pytest.mark.asyncio
async def test_nothing_starts_straight_after_something_ended(monkeypatch):
    _befriended()
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO life (user_id, what, arc, started, ended_ts)"
            " VALUES (?,'','[]',NULL,?)",
            (U, time.time() - 2 * life.DAY),
        )
    _answers(monkeypatch, COLD)
    monkeypatch.setattr(life, "_rolls_today", lambda user_id: True)
    await life.maybe_begin(U)
    assert life.current(U) is None


@pytest.mark.asyncio
async def test_after_a_quiet_stretch_something_can_start(monkeypatch):
    _befriended()
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO life (user_id, what, arc, started, ended_ts)"
            " VALUES (?,'','[]',NULL,?)",
            (U, time.time() - (life.QUIET_DAYS + 1) * life.DAY),
        )
    _answers(monkeypatch, COLD)
    monkeypatch.setattr(life, "_rolls_today", lambda user_id: True)
    await life.maybe_begin(U)
    assert life.current(U)["what"] == "простуда"


def test_a_new_thing_is_rare_enough_that_most_days_are_quiet():
    assert life.CHANCE_PER_DAY <= 0.2
    assert life.QUIET_DAYS >= 5


@pytest.mark.asyncio
async def test_a_broken_writer_just_means_an_uneventful_week(monkeypatch):
    async def explode(*a, **k):
        raise RuntimeError("провайдер прилёг")

    monkeypatch.setattr(life.brain, "generate_text", explode)
    monkeypatch.setattr(life, "_rolls_today", lambda user_id: True)
    _befriended()
    await life.maybe_begin(U)          # must not raise
    assert life.current(U) is None


# ── what the writer is allowed to come back with ───────────────────────────

def test_a_single_day_is_a_mood_and_belongs_elsewhere():
    """feeling.py already holds how he is today. If it does not have a shape,
    it is not an arc and this file should not carry it."""
    assert life._parse(json.dumps({"what": "грустно", "days": [{"state": "грустно"}]})) is None


def test_something_that_runs_for_a_fortnight_is_not_his_week_any_more():
    long = {"what": "затяжное", "days": [{"state": f"день {i}"} for i in range(15)]}
    assert life._parse(json.dumps(long)) is None


@pytest.mark.parametrize(
    "raw",
    ["", "не знаю", "{", "[]", '{"what": "простуда"}', '{"days": []}',
     '{"what": "", "days": [{"state": "a"}, {"state": "b"}, {"state": "c"}]}'],
)
def test_anything_unusable_is_simply_no_event(raw):
    assert life._parse(raw) is None


def test_a_fenced_answer_is_still_read():
    fenced = "```json\n" + json.dumps(COLD, ensure_ascii=False) + "\n```"
    parsed = life._parse(fenced)
    assert parsed and parsed["what"] == "простуда" and len(parsed["days"]) == 4


def test_a_very_long_day_is_trimmed_not_dropped():
    huge = {"what": "простуда",
            "days": [{"state": "я" * 900, "shows": "б" * 900} for _ in range(3)]}
    parsed = life._parse(json.dumps(huge, ensure_ascii=False))
    assert parsed and len(parsed["days"][0]["state"]) <= 300


# ── where it sits ──────────────────────────────────────────────────────────

def test_an_emergency_silences_his_week_completely():
    stable, variable = companion.build_system_parts(
        persona_block="ТЫ — Гриша.",
        alert_block="🚨 ТРЕВОГА",
        alert_level="danger",
        life_block="ЧТО У ТЕБЯ СЕЙЧАС В ЖИЗНИ:\nПростуда.",
    )
    assert "🚨 ТРЕВОГА" in stable       # on danger the alert IS the prompt
    assert "ЧТО У ТЕБЯ СЕЙЧАС В ЖИЗНИ" not in variable


def test_it_never_lands_in_the_cached_half():
    """It changes every day. In the stable half it would freeze Tuesday's cold
    into his character and miss the cache besides."""
    stable, _variable = companion.build_system_parts(
        persona_block="ТЫ — Гриша.", life_block="ЧТО У ТЕБЯ СЕЙЧАС В ЖИЗНИ:\nПростуда."
    )
    assert "ЖИЗНИ" not in stable


def test_nothing_changes_on_a_week_when_nothing_is_happening():
    with_empty = companion.build_system_parts(
        persona_block="ТЫ — Гриша.", life_block="", acquaintance="давно"
    )
    without = companion.build_system_parts(
        persona_block="ТЫ — Гриша.", acquaintance="давно"
    )
    assert with_empty == without


# ── one life per friendship ────────────────────────────────────────────────

def test_his_week_is_not_shared_between_people():
    _running(user="анна", days_ago=1)
    assert life.block("анна") != ""
    assert life.block("борис") == ""


# ── his life is not a metronome ────────────────────────────────────────────

def test_the_day_is_rolled_once_however_often_it_is_asked():
    """CHANCE_PER_DAY means per DAY, and it did not. maybe_begin runs after
    every exchange, so a fresh 0.15 was rolled twenty-five times in a single
    conversation — a 98% chance per conversation, which turned «roughly one
    thing every two and a half weeks» into something starting on the first day
    the quiet week was up, every single time. A metronome: exactly the
    «television programme rather than somebody you know» that the constant's
    own note warns against."""
    answers = {life._rolls_today("one-man") for _ in range(50)}
    assert len(answers) == 1, "один день — один ответ, сколько ни спрашивай"


def test_the_chance_is_the_chance_it_says_it_is():
    fired = sum(life._rolls_today(f"person-{i}") for i in range(3000))
    assert abs(fired / 3000 - life.CHANCE_PER_DAY) < 0.03, (
        f"{fired / 3000:.1%} против обещанных {life.CHANCE_PER_DAY:.0%}"
    )


def test_two_people_do_not_get_the_same_week():
    """Seeded on the person as well as the date, or every companion on the
    server catches a cold on the same Tuesday."""
    a = [life._rolls_today(f"a{i}") for i in range(200)]
    b = [life._rolls_today(f"b{i}") for i in range(200)]
    assert a != b
