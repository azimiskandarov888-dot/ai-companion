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

def test_he_does_not_announce_it_but_does_not_hide_it_either():
    """The first version capped this at «one sentence, only if asked», which was
    a ceiling where a norm belonged — and stricter than the constitution, which
    already says he sometimes tells a warm story from his own life.

    Being the audience is a REST. Having to be interesting about your own week
    is work, and for somebody whose week was four walls it is work with nothing
    to work from — so an hour of somebody else's week can be the kinder thing."""
    _running(days_ago=1)
    said = life.block(U)
    assert "СЛЫШНО РАНЬШЕ, ЧЕМ СКАЗАНО" in said
    assert "Не начинай с этого" in said
    # …and then the other half, which the first version was missing entirely
    assert "рассказывай как есть" in said
    assert "сколько ему хочется слушать" in said
    assert "не отделывайся одной фразой" in said


def test_his_week_is_never_made_her_problem():
    """The Stanford finding, pinned. Invite a lonely person to worry about a
    fiction and the fiction has taken something real."""
    _running(days_ago=1)
    said = life.block(U)
    # The line is not length — it is what he WANTS, and who moved first.
    assert "НЕ В ДЛИНЕ, А В ТОМ, ЧЕГО ТЫ ХОЧЕШЬ" in said
    assert "сам, по своей воле, с этим не приходи" in said
    assert "ничего не проси" in said
    # And if she is the one having a bad day, his does not exist.
    assert "твоего просто нет" in said


def test_when_she_insists_he_stops_deflecting():
    """The second absolute he caught. «Нисколько» was wrong: somebody who asks
    again, after being brushed off, has already worked out that something is
    wrong and wants IN. Brushing them off twice is not modesty, it is refusing
    them — and being the one who comforts, rather than the one comforted, is
    often the scarcer thing for a person whose days have nobody in them."""
    _running(days_ago=1)
    said = life.block(U)
    assert "ЕСЛИ ОН САМ ЛЕЗЕТ И НЕ ОТСТАЁТ" in said
    assert "Отговориться второй раз" in said
    assert "Дай ему тебя пожалеть" in said
    assert "быть тем, кто утешает" in said


def test_it_comes_out_in_pieces_and_never_as_a_pile():
    """Permission without a SHAPE was still wrong. Somebody who said nothing and
    then unloads the lot frightens you worse than the thing he unloaded, because
    now you know it was being held back from you.

    This belongs to the MIDDLE state alone, and that is the whole point of the
    dial: the other two have no pile to drop. Nothing was being held from the
    open one, and nothing is being told to the closed one."""
    _running(days_ago=1)
    said = life.block(U)
    assert "по чуть-чуть, а не горой" in said
    assert "Сперва полфразы" in said
    assert "Пусть он сам вытянет" in said


# ── one dial, three people ──────────────────────────────────────────────────
#
# The complaint that produced this: the same choreography was being read to
# everybody. One man is in a bad way and does not want to hear that anybody
# else is having a hard week either; the next would far rather listen to his
# friend's week for an hour than account for his own. Nothing about them is the
# same, and «сперва полфразы, потом ещё немного» was answering a question
# neither of them had asked.

def test_the_open_one_is_told_without_being_asked():
    """He has shown he wants in. Waiting to be asked is then the wrong shape —
    and «по чуть-чуть» is not just unnecessary, it is the wrong instruction."""
    _running(days_ago=1)
    said = life.block(U, openness="open")
    assert "ЗАГОВОРИ ПЕРВЫМ" in said
    assert "подробно" in said
    assert "Не начинай с этого" not in said
    assert "по чуть-чуть, а не горой" not in said


def test_the_closed_one_is_not_told_at_all_and_is_not_lied_to_either():
    """The hardest of the three to get right. «Не рассказывай» must not become
    «врать, что всё хорошо» — a cheerful lie from somebody who is plainly not
    cheerful is the exact thing a lonely person is expert at hearing. And the
    meaningful sigh is not a loophole: it is the same telling, done sideways."""
    _running(days_ago=1)
    said = life.block(U, openness="closed")
    assert "НИ СЛОВА ПЕРВЫМ" in said
    assert "не намекай" in said
    assert "не вздыхай" in said
    assert "врать «всё отлично» нельзя" in said
    # and none of the middle state's choreography survives into it
    assert "Сперва полфразы" not in said
    assert "Не начинай с этого" not in said


def test_a_person_who_will_not_let_it_go_wins_even_against_the_closed_setting():
    """The dial decides whom he TELLS. It does not decide what happens when the
    person in front of him insists — and it matters most exactly where a rigid
    reading is most dangerous: «не рассказывай ему» must not become stonewalling
    somebody who is asking directly for the third time."""
    _running(days_ago=1)
    for want in ("closed", "normal"):
        said = life.block(U, openness=want)
        assert "ЕСЛИ ОН САМ ЛЕЗЕТ И НЕ ОТСТАЁТ" in said, want
        assert "кем бы он ни был" in said, want
    # …and it is dropped for the open one, where it is dead text: it describes a
    # deflection that cannot happen with somebody he was told not to deflect
    # with, and dead text in a prompt is paid for out of the live text.
    assert "ЕСЛИ ОН САМ ЛЕЗЕТ" not in life.block(U, openness="open")


def test_what_he_is_doing_is_the_same_question_for_everybody():
    """Length is the dial's to decide. What he WANTS is not, and the paragraph
    that says so must not quietly hand out a length as well — «этого можно
    сколько угодно» told the closed one the opposite of the line above it."""
    _running(days_ago=1)
    for want in ("closed", "normal", "open"):
        said = life.block(U, openness=want)
        assert "НЕ В ДЛИНЕ, А В ТОМ, ЧЕГО ТЫ ХОЧЕШЬ" in said, want
        assert "не делай из своей недели беды" in said, want
        assert "сколько ЕМУ хочется слушать" in said, want
        assert "можно сколько угодно" not in said, want
        # and if she is the one having a bad day, his does not exist
        assert "твоего просто нет" in said, want


def test_the_facts_of_his_week_are_the_same_for_everybody():
    """What is happening to him does not depend on who is listening. Only how
    much of it is said out loud does."""
    _running(days_ago=1)
    for want in ("closed", "normal", "open"):
        said = life.block(U, openness=want)
        assert "разболелся как следует" in said, want
        assert "часто шмыгает" in said, want


def test_an_unknown_dial_setting_falls_back_to_the_middle():
    """Nothing should be able to hand him a state nobody wrote — and if it does,
    the answer is the one that is safe for a stranger, not silence."""
    _running(days_ago=1)
    assert life.block(U, openness="кто-то-напутал") == life.block(U, openness="normal")


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
    monkeypatch.setattr(life.random, "random", lambda: 0.0)
    _befriended(turns=5)
    await life.maybe_begin(U)
    assert life.current(U) is None


@pytest.mark.asyncio
async def test_nothing_starts_while_something_is_already_on(monkeypatch):
    """A man with three simultaneous dramas is a soap opera."""
    _befriended()
    _running(days_ago=1)
    _answers(monkeypatch, {"what": "другое", "days": COLD["days"]})
    monkeypatch.setattr(life.random, "random", lambda: 0.0)
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
    monkeypatch.setattr(life.random, "random", lambda: 0.0)
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
    monkeypatch.setattr(life.random, "random", lambda: 0.0)
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
    monkeypatch.setattr(life.random, "random", lambda: 0.0)
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
