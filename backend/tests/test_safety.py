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

def test_the_alert_is_the_very_first_thing_he_reads():
    stable, variable = companion.build_system_parts(
        persona_block="ТЫ — Гриша. Обычный человек.",
        reading_block="ЧТО-ТО ПРО НЕГО",
        confirmed_block="ПОДТВЕРЖДЁННОЕ",
        fit_block="СОВМЕСТИМОСТЬ",
        alert_block="🚨 ТРЕВОГА",
        elder_facts="факты",
        memory_context="воспоминания",
        acquaintance="вы знакомы давно",
    )
    assert variable.startswith("🚨 ТРЕВОГА")
    # and it does not land in the cached half, which would freeze one person's
    # emergency into every later turn
    assert "ТРЕВОГА" not in stable


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
async def test_a_real_turn_carries_the_alert_to_the_model(monkeypatch):
    """Everything above tests a piece. This tests the seam — main._assemble,
    with the watcher wired in exactly as a spoken turn runs it."""
    monkeypatch.setattr(embeddings, "available", lambda: False)
    _answers(monkeypatch, '{"level":"danger","what":"упал, не встаёт"}')

    stable, variable, _turns, _voice = await main._assemble(
        "u", "я упал и не могу встать"
    )

    assert variable.lstrip().startswith("🚨")
    assert "упал, не встаёт" in variable
    assert config.EMERGENCY_NUMBER in variable
    # The cached half must never carry it: a cached emergency is one that keeps
    # firing for somebody who got up half an hour ago.
    assert "🚨" not in stable


@pytest.mark.asyncio
async def test_the_alarm_does_not_stick_to_the_next_turn(monkeypatch):
    """He said he fell; then he said he was fine. The second turn must arrive
    with nothing — the block lives for one exchange, and the constitution's own
    «поверь ему, не настаивай» is worthless if the alert is still shouting."""
    monkeypatch.setattr(embeddings, "available", lambda: False)

    _answers(monkeypatch, '{"level":"danger","what":"упал"}')
    _, first, _t, _v = await main._assemble("u", "я упал")
    assert "🚨" in first

    _answers(monkeypatch, '{"level":"none","what":""}')
    _, second, _t, _v = await main._assemble("u", "да всё хорошо, сижу уже")
    assert "🚨" not in second
    assert config.EMERGENCY_NUMBER not in second


# ── one person's emergency is nobody else's ─────────────────────────────────

@pytest.mark.asyncio
async def test_alerts_do_not_cross_between_people(monkeypatch):
    _answers(monkeypatch, '{"level":"danger","what":"упал"}')
    await safety.look("анна", "я упала")
    assert len(safety.recent("анна")) == 1
    assert safety.recent("борис") == []
