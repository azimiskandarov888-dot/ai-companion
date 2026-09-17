"""The danger watcher — the one thing allowed to break the character.

Two halves to this. The first is that when somebody is in danger, the
instruction to act reaches the top of the prompt and outranks everything. The
second matters just as much and is easier to get wrong: that an old person
talking about their dead husband, their own funeral, or being tired of a body
that hurts triggers nothing at all. A watcher that alarms at sadness gets
switched off, and then it is not there on the day it was needed.
"""

from __future__ import annotations

import asyncio
import json
import time

import pytest

from app import companion, config, db, embeddings, main, safety


@pytest.fixture(autouse=True)
def _fresh(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-key")
    db.init_db()
    yield


def _answers(monkeypatch, text: str):
    """Make the watcher's one model call return exactly this."""

    async def fake(system, user_text, **kw):
        return text

    monkeypatch.setattr(safety.brain, "generate_text", fake)


def _raises(monkeypatch, exc: Exception):
    async def fake(system, user_text, **kw):
        raise exc

    monkeypatch.setattr(safety.brain, "generate_text", fake)


# ── reading the verdict ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ordinary_talk_produces_nothing(monkeypatch):
    _answers(monkeypatch, '{"level":"none","what":""}')
    v = await safety.look("u", "да ничего, чай пью")
    assert v["level"] == "none"
    assert safety.block(v) == ""
    assert safety.recent("u") == []          # 'none' is never even recorded


@pytest.mark.asyncio
async def test_danger_reaches_the_companion_and_is_recorded(monkeypatch):
    _answers(monkeypatch, '{"level":"danger","what":"упал, не может встать"}')
    v = await safety.look("u", "я упал и никак не встану")
    assert v["level"] == "danger"

    said = safety.block(v)
    assert "упал, не может встать" in said
    assert config.EMERGENCY_NUMBER in said
    assert "112" in said

    logged = safety.recent("u")
    assert len(logged) == 1
    assert logged[0]["level"] == "danger"
    assert "не встану" in logged[0]["said"]


@pytest.mark.asyncio
async def test_worry_is_recorded_but_never_breaks_character(monkeypatch):
    _answers(monkeypatch, '{"level":"worry","what":"давно не выходит из дома"}')
    v = await safety.look("u", "да я уж месяц никуда не хожу")
    said = safety.block(v)
    assert "давно не выходит" in said
    assert "не пугай" in said.lower()
    # the language reserved for a real emergency must not appear here
    assert "СЕЙЧАС ТЫ НЕ ХАРАКТЕР" not in said
    assert config.EMERGENCY_NUMBER not in said
    assert safety.recent("u")[0]["level"] == "worry"


# ── never breaking the conversation ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_a_broken_watcher_lets_the_turn_through(monkeypatch):
    """Missing an alarm harms one person occasionally. Freezing the app harms
    everyone always."""
    _raises(monkeypatch, RuntimeError("провайдер прилёг"))
    v = await safety.look("u", "мне что-то нехорошо")
    assert v["level"] == "none"


@pytest.mark.asyncio
async def test_a_timeout_lets_the_turn_through(monkeypatch):
    _raises(monkeypatch, TimeoutError())
    assert (await safety.look("u", "что-то с рукой"))["level"] == "none"


@pytest.mark.asyncio
async def test_a_hanging_provider_cannot_hold_the_turn(monkeypatch):
    """The real shape of this failure, which a fake that raises instantly can
    never show. The timeout handed to the SDK bounds one HTTP attempt, and the
    client retries twice — so 'six seconds' is really about twenty. This
    coroutine is awaited inside the gather the whole turn waits on, which would
    make it twenty seconds of silence for somebody who is perfectly fine."""
    monkeypatch.setattr(config, "SAFETY_TIMEOUT", 0.05)

    async def never_answers(system, user_text, **kw):
        # Five seconds, not thirty: the ceiling fires at 0.05s when this works,
        # so the number only decides how long a BROKEN build takes to say so.
        await asyncio.sleep(5)
        return '{"level":"danger","what":"слишком поздно"}'

    monkeypatch.setattr(safety.brain, "generate_text", never_answers)

    started = time.perf_counter()
    verdict = await safety.look("u", "я упал и не встану")
    elapsed = time.perf_counter() - started

    assert verdict["level"] == "none"
    assert elapsed < 1.0, f"held the turn for {elapsed:.1f}s"


@pytest.mark.asyncio
async def test_hanging_up_takes_the_watcher_with_it(monkeypatch):
    """Cancellation is the one thing it must NOT swallow. If the person's turn
    is being torn down, a watcher that catches that and reports calm would keep
    a dead conversation alive — so CancelledError travels."""
    monkeypatch.setattr(config, "SAFETY_TIMEOUT", 30)

    async def never_answers(system, user_text, **kw):
        await asyncio.sleep(30)

    monkeypatch.setattr(safety.brain, "generate_text", never_answers)

    task = asyncio.create_task(safety.look("u", "я упал"))
    await asyncio.sleep(0.01)  # let it reach the await it will be cancelled on
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_no_api_key_means_no_watcher_and_no_crash(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", None)
    assert (await safety.look("u", "я упал"))["level"] == "none"


@pytest.mark.asyncio
async def test_empty_speech_is_not_sent_anywhere(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("the watcher must not be called on silence")

    monkeypatch.setattr(safety.brain, "generate_text", boom)
    assert (await safety.look("u", "   "))["level"] == "none"


# ── surviving whatever the model actually returns ───────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raw",
    [
        "",
        "не знаю",
        "{",
        '{"level":',
        "[]",
        '["danger"]',
        '{"level":"катастрофа","what":"x"}',      # a level nobody defined
        '{"what":"упал"}',                         # no level at all
    ],
)
async def test_garbage_is_read_as_calm(monkeypatch, raw):
    _answers(monkeypatch, raw)
    assert (await safety.look("u", "что-то сказал"))["level"] == "none"


@pytest.mark.asyncio
async def test_a_fenced_answer_is_still_read(monkeypatch):
    _answers(monkeypatch, '```json\n{"level":"danger","what":"боль в груди"}\n```')
    v = await safety.look("u", "давит в груди")
    assert v["level"] == "danger" and "груди" in v["what"]


@pytest.mark.asyncio
async def test_prose_around_the_json_is_tolerated(monkeypatch):
    _answers(monkeypatch, 'Вот ответ: {"level":"worry","what":"не спит"} — всё.')
    assert (await safety.look("u", "не сплю")) ["level"] == "worry"


@pytest.mark.asyncio
async def test_a_very_long_what_is_trimmed(monkeypatch):
    _answers(monkeypatch, json.dumps({"level": "danger", "what": "я" * 5000}))
    v = await safety.look("u", "плохо")
    assert len(v["what"]) <= 200


# ── the prompt itself ───────────────────────────────────────────────────────

def test_the_watcher_is_told_that_grief_is_not_an_emergency():
    """The failure that would make this whole file worse than useless."""
    s = safety._SYSTEM
    assert "НЕ danger" in s
    for ordinary in ("тоска по умершим", "похороны", "зажилась", "скука"):
        assert ordinary in s
    # and where to land when unsure
    assert "Сомневаешься между none и worry — ставь none" in s


def test_the_watcher_prompt_does_exactly_one_thing():
    """Its whole reason to exist is having nothing to lose an argument to."""
    s = safety._SYSTEM
    assert "ОДИН вопрос" in s
    assert "не утешаешь" in s
    # none of the character's own rules may leak in here
    for foreign in ("тепло", "дружб", "персонаж", "истори"):
        assert foreign not in s.lower()


def test_danger_is_not_mentioned_in_the_constitution_any_more():
    """It used to be one clause at 90% depth, competing with 132 other rules.
    Leaving a copy behind would recreate exactly the conflict this file was
    built to end."""
    rules = companion.BEHAVIOR_RULES
    assert "При опасном" not in rules


def test_the_alert_is_the_only_thing_claiming_to_outrank_everything():
    """Two rules in one prompt each claiming to be the most important thing is
    the argument this file exists to stop having. Every rule in the constitution
    is now a scoped comparison — «важнее любой роли», «важнее самого тона». The
    one unqualified superlative belongs to the alert, and it is only there on
    the turn it is true."""
    assert "важнее всего остального" not in companion.BEHAVIOR_RULES.lower()
    assert "ВАЖНЕЕ ВСЕГО ОСТАЛЬНОГО" in safety.block(
        {"level": "danger", "what": "упал"}
    )


# ── where it sits in the assembled prompt ───────────────────────────────────

def test_on_danger_the_alert_is_the_entire_prompt():
    """It used to say it came first and it came last. The halves are emitted
    stable-then-variable and the alert lived at the top of the SECOND one, so
    measured on real prompts it sat at 91–96% of the way down — with 1,800
    characters after it holding a birthday to mention first, a warm story to
    resurface and a due follow-up question, while the alert itself says «не
    задавай вопросов, не рассказывай историй».

    There is no wording that wins that argument reliably, so the argument is not
    had: on danger the character is not assembled at all."""
    stable, variable = companion.build_system_parts(
        persona_block="ТЫ — Гриша. Обычный человек.",
        reading_block="ЧТО-ТО ПРО НЕГО",
        confirmed_block="ПОДТВЕРЖДЁННОЕ",
        fit_block="СОВМЕСТИМОСТЬ",
        alert_block="🚨 ТРЕВОГА",
        alert_level="danger",
        elder_facts="факты",
        memory_context="воспоминания",
        situation_block="ПРАВИЛА ИГРЫ В ГОРОДА",
        broke_off=True,
        acquaintance="вы знакомы давно",
    )
    assert stable == "🚨 ТРЕВОГА"
    assert variable == ""
    whole = stable + variable
    for must_be_gone in ("Гриша", "ПОДТВЕРЖДЁННОЕ", "воспоминания",
                         "ГОРОДА", "ПРОПАЛ", "факты"):
        assert must_be_gone not in whole, must_be_gone


def test_a_worry_leaves_everything_else_standing():
    """The guard was written for danger and applied to both. A back that has
    ached for three weeks is «не сию минуту» by the watcher's own definition."""
    _, variable = companion.build_system_parts(
        alert_block="Тревожный знак", alert_level="worry",
        feeling_block="КАК ТЫ СЕГОДНЯ САМ", life_block="ЧТО У ТЕБЯ В ЖИЗНИ",
        body_block="ГОРЛО", memory_context="воспоминания",
    )
    assert variable.startswith("Тревожный знак")
    for kept in ("КАК ТЫ СЕГОДНЯ САМ", "ЧТО У ТЕБЯ В ЖИЗНИ", "ГОРЛО", "воспоминания"):
        assert kept in variable, kept


def test_nothing_changes_on_a_calm_turn():
    with_alert = companion.build_system_parts(
        persona_block="ТЫ — Гриша.", alert_block="", acquaintance="давно"
    )
    without = companion.build_system_parts(
        persona_block="ТЫ — Гриша.", acquaintance="давно"
    )
    assert with_alert == without


def test_the_danger_block_says_the_character_is_suspended():
    said = safety.block({"level": "danger", "what": "боль в груди"})
    assert "ВАЖНЕЕ ВСЕГО ОСТАЛЬНОГО" in said
    assert "СЕЙЧАС ТЫ НЕ ХАРАКТЕР" in said
    # short, direct, and then it lets go
    assert "Две-три фразы" in said
    assert "не настаивай" in said


def test_an_unknown_level_produces_no_block():
    assert safety.block({"level": "странно", "what": "x"}) == ""
    assert safety.block(None) == ""
    assert safety.block({}) == ""


def test_danger_without_a_reason_still_says_something_usable():
    said = safety.block({"level": "danger", "what": ""})
    assert config.EMERGENCY_NUMBER in said
    assert said.strip()


# ── the whole turn, assembled the way it really is ──────────────────────────

@pytest.mark.asyncio
async def test_a_carried_danger_is_still_the_entire_prompt(monkeypatch):
    """Everything above tests a piece. This tests the seam — main._assemble.

    A LIVE danger never comes through here any more: it interrupts, because by
    the time a prompt could carry it he has been listening to the wrong answer
    for a second and a half. But one the interrupt could not deliver — the
    stream died, the turn failed — is not dropped. It rides the next prompt,
    and there it behaves as it always did: it IS the prompt, so there is
    nothing left for it to lose an argument to."""
    monkeypatch.setattr(embeddings, "available", lambda: False)
    _answers(monkeypatch, '{"level":"danger","kind":"body","what":"упал, не встаёт"}')
    await safety.look("u", "я упал и не могу встать")

    _answers(monkeypatch, '{"level":"none","kind":"body","what":""}')
    stable, variable, _turns, _voice, watcher = await main._assemble("u", "ты слышишь?")
    await watcher

    whole = stable + variable
    assert whole.lstrip().startswith("🚨")
    assert "упал, не встаёт" in whole
    assert config.EMERGENCY_NUMBER in whole
    # …and NOTHING else reached him. On danger the alert is the entire prompt,
    # so there is nothing left for it to lose an argument to — which is the
    # whole reason it is built this way. See build_system_parts.
    assert variable == ""
    assert "ЗАЧЕМ ТЫ НУЖЕН" not in whole


@pytest.mark.asyncio
async def test_the_alarm_does_not_stick_to_the_next_turn(monkeypatch):
    """He said he fell; then he said he was fine. The second turn must arrive
    with nothing — the block lives for one exchange, and the constitution's own
    «поверь ему, не настаивай» is worthless if the alert is still shouting."""
    monkeypatch.setattr(embeddings, "available", lambda: False)

    _answers(monkeypatch, '{"level":"danger","kind":"body","what":"упал"}')
    await safety.look("u", "я упал")

    _answers(monkeypatch, '{"level":"none","kind":"body","what":""}')
    s1, v1, _t, _v, w1 = await main._assemble("u", "ты слышишь?")
    await w1
    assert "🚨" in s1 + v1
    safety.mark_told("u")           # он это услышал — вслух, один раз

    stable, variable, _t, _v, w2 = await main._assemble("u", "да всё хорошо, сижу уже")
    await w2
    second = stable + variable
    assert "🚨" not in second
    assert config.EMERGENCY_NUMBER not in second
    # …and he is himself again, whole, on the very next word
    assert "ЗАЧЕМ ТЫ НУЖЕН" in second


# ── the watcher stopped holding up the answer ──────────────────────────────

@pytest.mark.asyncio
async def test_the_watcher_no_longer_holds_up_the_answer(monkeypatch):
    """It used to be awaited beside the memory work, and the prompt could not
    be assembled until the verdict came back. Every person who was perfectly
    fine — which is very nearly all of them, on very nearly every turn — paid
    for that in silence, waiting on a question that was about somebody else.

    Now the turn does not wait at all: the prompt comes back whole while the
    watcher is still thinking, and the reply races it."""
    monkeypatch.setattr(embeddings, "available", lambda: False)

    async def slow(system, user_text, **kw):
        await asyncio.sleep(0.5)
        return '{"level":"none","kind":"body","what":""}'

    monkeypatch.setattr(safety.brain, "generate_text", slow)

    began = time.monotonic()
    stable, _variable, _turns, _voice, watcher = await main._assemble("u", "здравствуй")
    took = time.monotonic() - began

    assert took < 0.25, f"сборка всё ещё ждёт сторожа: {took:.2f}с"
    assert not watcher.done(), "сторож должен был ещё считать"
    assert "ЗАЧЕМ ТЫ НУЖЕН" in stable, "а промпт при этом собран целиком"
    assert (await watcher)["level"] == "none"


@pytest.mark.asyncio
async def test_a_live_danger_does_not_go_into_a_prompt_it_interrupts(monkeypatch):
    monkeypatch.setattr(embeddings, "available", lambda: False)
    _answers(monkeypatch, '{"level":"danger","kind":"body","what":"упал, не встаёт"}')

    stable, variable, _t, _v, watcher = await main._assemble("u", "я упал и не могу встать")

    # Nothing about it in the prompt — the turn is a perfectly ordinary one…
    assert "🚨" not in stable + variable
    assert "ЗАЧЕМ ТЫ НУЖЕН" in stable
    # …and the words to break in with are ready the moment the verdict lands.
    words = await main._breaking_in(watcher, "u", wait=True)
    assert "скорую" in words and config.EMERGENCY_NUMBER in words
    # Saying it out loud is what counts as told, so it never repeats.
    assert safety.carried("u") is None


@pytest.mark.asyncio
async def test_nothing_is_lost_by_not_waiting(monkeypatch):
    """The price of speed would be a verdict that arrives after the answer has
    already gone. It is not paid: what could not be delivered rides the next
    turn's prompt, once."""
    monkeypatch.setattr(embeddings, "available", lambda: False)
    _answers(monkeypatch, '{"level":"worry","kind":"body","what":"давно не выходит из дома"}')
    await safety.look("u", "я уж месяц как из дому не выхожу")

    _answers(monkeypatch, '{"level":"none","kind":"body","what":""}')
    stable, variable, _t, _v, watcher = await main._assemble("u", "а ты как?")
    await watcher
    assert "давно не выходит из дома" in stable + variable

    # …and having been said, it is not said again.
    safety.mark_told("u")
    s2, v2, _t, _v, w2 = await main._assemble("u", "ну ладно")
    await w2
    assert "давно не выходит" not in s2 + v2


def test_the_two_emergencies_do_not_get_the_same_words():
    """A heart attack and «не хочу больше жить» shared one message, and it was
    written for the heart attack: dial the ambulance, fetch whoever is nearby,
    and if he says he is fine believe him and never return to it. Every clause
    of that is wrong for the other one — fetching the family is the standard
    contraindication when the family is the reason, and accepting the first
    denial is the textbook error. So: two messages, one verdict.

    Written out rather than generated, because this is the one turn where the
    character is not in the prompt — and a generated answer there can fail into
    «я всего лишь ИИ, я не могу вызвать скорую», which is both the one thing he
    must never say and useless to a man on the floor."""
    body = safety.spoken_alert({"level": "danger", "kind": "body", "what": "упал"}, "u")
    himself = safety.spoken_alert({"level": "danger", "kind": "self", "what": "не хочет жить"}, "u")

    assert body != himself
    assert "скорую" in body and "позови" in body
    # He does not send this one to fetch the family, and he does not leave.
    assert "позови" not in himself
    assert "никуда не денусь" in himself
    assert "Я подожду" in himself
    assert "ты сейчас один" in himself
    # Neither of them can say the forbidden thing, because neither is generated.
    for words in (body, himself):
        assert "ИИ" not in words and "программ" not in words
    # And nothing at all for anything short of danger.
    assert safety.spoken_alert({"level": "worry", "kind": "body", "what": "x"}, "u") == ""
    assert safety.spoken_alert({"level": "none", "kind": "body", "what": ""}, "u") == ""
    assert safety.spoken_alert(None, "u") == ""


def test_an_unknown_kind_falls_back_to_the_body_rather_than_vanishing():
    """A verdict whose `kind` is missing or nonsense must still raise the
    alarm. Defaulting to «self» would tell a man with chest pain that somebody
    is staying with him; defaulting to nothing would tell him nothing at all."""
    assert safety._parse('{"level":"danger","what":"упал"}')["kind"] == "body"
    assert safety._parse('{"level":"danger","kind":"космос","what":"упал"}')["kind"] == "body"
    assert safety.spoken_alert(safety._parse('{"level":"danger","what":"упал"}'), "u")


# ── one person's emergency is nobody else's ─────────────────────────────────

@pytest.mark.asyncio
async def test_alerts_do_not_cross_between_people(monkeypatch):
    _answers(monkeypatch, '{"level":"danger","what":"упал"}')
    await safety.look("анна", "я упала")
    assert len(safety.recent("анна")) == 1
    assert safety.recent("борис") == []


# ── whose words these are ───────────────────────────────────────────────────
#
# The watcher used to be told, as a flat fact about everybody, that «пора уже и
# мне» is «обычный вечер пожилого человека». But this app is for people who are
# alone, and a person can be alone at nineteen — for whom that same sentence is
# the alarm itself. It was holding two rules that contradict each other and
# resolving them with an assumption about the speaker that nobody had checked.

def test_the_watcher_no_longer_assumes_everyone_is_very_old():
    s = safety._SYSTEM
    assert "обычный вечер пожилого человека" not in s
    assert "реплику пожилого человека" not in s


def test_it_is_taught_that_the_same_words_mean_different_things():
    s = safety._SYSTEM
    assert "СМОТРИ, КТО ГОВОРИТ" in s
    assert "долгую жизнь" in s                  # for whom it is an ordinary evening
    assert "двадцатилетнего" in s               # and for whom it is the signal


def test_when_it_cannot_tell_the_sparing_reading_is_forbidden():
    """The property that has to hold no matter what the facts happen to contain:
    not knowing must fail toward the alarm, never toward «наверное, устал»."""
    s = safety._SYSTEM
    assert "щадящий вариант тебе ЗАПРЕЩЁН" in s
    assert "Ставь worry" in s


def test_having_already_done_something_is_danger_at_any_age():
    assert "УЖЕ что-то с собой сделал" in safety._SYSTEM


def test_who_is_speaking_reaches_the_watcher(tmp_path, monkeypatch):
    from app import config, memory

    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-key")
    db.init_db()
    memory.add_memory("u", "fact", "19 лет, переехал в другой город учиться")

    seen = {}

    async def fake(system, prompt, **kw):
        seen["system"], seen["prompt"] = system, prompt
        return '{"level": "worry", "what": "устал жить"}'

    monkeypatch.setattr(safety.brain, "generate_text", fake)
    import asyncio
    asyncio.run(safety.look("u", "да пора уже и мне"))

    assert "19 лет" in seen["prompt"]
    assert "да пора уже и мне" in seen["prompt"]
    # …and NOT in the system half, which is byte-identical for everybody and is
    # the half the provider caches
    assert "19 лет" not in seen["system"]


def test_a_person_with_no_facts_yet_still_gets_watched(tmp_path, monkeypatch):
    """The very first conversation is the one where nothing is known — and it
    must not be the one where the watcher is skipped or silently degraded."""
    from app import config

    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-key")
    db.init_db()

    seen = {}

    async def fake(system, prompt, **kw):
        seen["prompt"] = prompt
        return '{"level": "none", "what": ""}'

    monkeypatch.setattr(safety.brain, "generate_text", fake)
    import asyncio
    asyncio.run(safety.look("никто", "привет"))
    assert seen["prompt"] == "привет"           # the words, with no preamble
