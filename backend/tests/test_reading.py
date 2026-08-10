"""The reading — understanding a person from HOW they wrote.

The most important stage in the app, and the one with the most ways to fail
quietly. These tests pin the three properties that matter: it never blocks a
friend from arriving, it never leaks into what the companion says, and the
slice that reaches every turn stays in the cached half of the prompt.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from app import brain, companion, config, matchmaker, persona, reading

READING = {
    "register": "пишет коротко и сухо; говори так же — без обилия нежности",
    "surface": "рассказал про работу и рыбалку",
    "beneath": "о себе почти всегда в дательном: «мне не спится», «так вышло»",
    "evidence": ["мне не спится", "так вышло"],
    "carrying": "усталость, которую он не называет",
    "longing": "чтобы не надо было держать лицо",
    "absent": "ни одного человека по имени",
    "self_image": "считает себя обычным",
    "would_ring_false": "бодрый оптимизм и «всё будет хорошо»",
    "would_reach_them": "спокойный, медленный, с паузами, без напора",
    "needs_pushback_on": "что он «никому не интересен»",
    "do_not_touch": "смерть жены",
    "common_ground_seeds": ["рыбалка", "старые машины"],
    "confidence": "твёрдое",
}


@pytest.fixture
def reader(monkeypatch):
    """Fake the deep model. Records what it was asked to read."""
    calls: list[str] = []

    async def fake_think(system_prompt, user_text, *, model=None, effort="high", max_tokens=8000):
        calls.append(user_text)
        return "Вот чтение:\n```json\n" + json.dumps(READING, ensure_ascii=False) + "\n```"

    monkeypatch.setattr(brain, "think", fake_think)
    return calls


def test_reads_the_person_and_keeps_the_reading(reader):
    result = asyncio.run(reading.read_person("Мне не спится. Так вышло.", "кого-то весёлого"))
    assert result["do_not_touch"] == "смерть жены"

    # The text is passed VERBATIM — the whole method depends on the exact
    # words, so anything that summarises before reading defeats the stage.
    assert "Мне не спится. Так вышло." in reader[0]
    assert "кого-то весёлого" in reader[0]

    reading.save(result)
    assert reading.load()["register"] == READING["register"]


def test_a_reading_without_the_essentials_is_refused(monkeypatch):
    """Half a reading is worse than none: it would silently shape a character
    on nothing. Refusing sends creation down the no-brief path instead."""
    async def thin(system_prompt, user_text, **kwargs):
        return json.dumps({"surface": "любит рыбалку"}, ensure_ascii=False)

    monkeypatch.setattr(brain, "think", thin)
    with pytest.raises(reading.ReadingFailed):
        asyncio.run(reading.read_person("про меня"))


def test_empty_story_is_refused_before_spending_anything(monkeypatch):
    def explode(*a, **k):
        raise AssertionError("should never call the model for an empty story")

    monkeypatch.setattr(brain, "think", explode)
    with pytest.raises(reading.ReadingFailed):
        asyncio.run(reading.read_person("   "))


def test_the_brief_carries_judgement_but_never_the_quotes(reader):
    """The pen gets what to DO with the person, not the person's own words.

    Handed the quotes, a model writes a character who echoes them back — which
    is the single most alarming thing this app could do: a stranger repeating
    your own sentences to you on the first evening.
    """
    brief = reading.as_brief(READING)
    assert "спокойный, медленный" in brief          # what would reach them
    assert "смерть жены" in brief                    # what never to touch
    assert "мне не спится" not in brief              # …but never their words
    assert "так вышло" not in brief


def test_the_standing_block_is_only_what_every_turn_needs():
    block = reading.standing_block(READING)
    assert "без обилия нежности" in block            # register
    assert "бодрый оптимизм" in block                # what rings false
    assert "смерть жены" in block                    # what not to touch
    # Everything else is already baked into who he is — carrying it per-turn
    # would be tokens spent on every reply for no behavioural change.
    assert "ни одного человека по имени" not in block
    assert "рыбалка" not in block


def test_the_standing_block_rides_in_the_cached_half():
    """It describes the person, not today — so it belongs beside WHO HE IS,
    where the cache reads it instead of re-processing it every turn."""
    stable, variable = companion.build_system_parts(
        persona_block="ТЫ — Фёдор.",
        reading_block=reading.standing_block(READING),
        memory_context="Вчера говорили о рыбалке.",
    )
    assert "смерть жены" in stable
    assert "смерть жены" not in variable
    assert "рыбалке" in variable      # today's context stays uncached


def test_no_reading_no_block():
    assert reading.standing_block(None) == ""
    assert reading.as_brief(None) == ""


def test_a_failed_reading_still_lets_a_friend_walk_in(monkeypatch, capsys):
    """The one property that outranks depth: a person who came to meet someone
    must meet someone. A dead reading degrades the character; it never denies
    it — and it says so loudly rather than vanishing."""
    async def broken_reading(*a, **k):
        raise RuntimeError("модель недоступна")

    async def fake_generate(system_prompt, user_text, max_tokens=1500, model=None):
        if "ДЕСЯТЬ" in system_prompt:
            return "1. Зоя, 31, северный город, крановщица.\n2. Пётр, 44, село, пасечник."
        return json.dumps(
            {
                "name": "Зоя", "age": "31 год", "home": "северный город",
                "backstory": "выросла у реки", "personality": "прямая",
                "speech_style": "коротко, по делу",
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(reading, "read_person", broken_reading)
    monkeypatch.setattr(brain, "generate_text", fake_generate)

    created = asyncio.run(matchmaker.create_companion("Люблю тишину."))
    assert created["name"] == "Зоя"
    assert "чтение человека не получилось" in capsys.readouterr().err


def test_the_reading_survives_starting_over(reader, monkeypatch):
    """A new companion doesn't make the person a different person. «Начать
    заново» replaces who they talk to, not who they are."""
    reading.save(READING)

    async def fake_generate(system_prompt, user_text, max_tokens=1500, model=None):
        if "ДЕСЯТЬ" in system_prompt:
            return "1. Гриша, 73, посёлок, сварщик.\n2. Нина, 52, горы, фельдшер."
        return json.dumps(
            {
                "name": "Гриша", "age": "73 года", "home": "посёлок",
                "backstory": "варил всю жизнь", "personality": "ворчливый",
                "speech_style": "короткие фразы",
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(brain, "generate_text", fake_generate)
    asyncio.run(matchmaker.create_companion("Люблю тишину."))

    assert persona.load_persona()["name"] == "Гриша"
    assert reading.load() is not None          # the person is still known
    assert config.READING_PATH.exists()
