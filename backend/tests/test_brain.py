"""Brain wiring: the web-search tool is configured (real news/weather on ask)."""

from __future__ import annotations

from app import brain


def test_web_search_tool_configured():
    tool = brain._WEB_SEARCH_TOOL
    assert tool["name"] == "web_search"
    assert tool["type"].startswith("web_search_")
    # Capped so one question can't spiral into many searches.
    assert tool["max_uses"] >= 1


def test_search_only_when_the_world_is_asked_about():
    """The tool is attached per-turn, not always: its mere availability invites
    the model to consider it, and a search turn costs seconds of silence."""
    assert brain.wants_fresh_info("Какая сегодня погода?")
    assert brain.wants_fresh_info("что там в новостях?")
    assert brain.wants_fresh_info("Какой курс доллара?")
    # Ordinary warm talk — including HIS weather stories — stays offline.
    assert not brain.wants_fresh_info("Доброе утро!")
    assert not brain.wants_fresh_info("расскажи про свою молодость")
    assert not brain.wants_fresh_info("сыграем в города?")


def test_stable_head_is_cached_and_variable_tail_is_not():
    blocks = brain._system_blocks("КТО ТЫ: Фёдор", "Сегодня праздник")
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}
    assert "Фёдор" in blocks[0]["text"]
    assert "cache_control" not in blocks[1]
    assert "праздник" in blocks[1]["text"]
    # Nothing variable → nothing after the cached head (an empty block would
    # be a pointless cache-buster).
    assert len(brain._system_blocks("КТО ТЫ", "")) == 1


def test_persona_lives_in_the_stable_half():
    """The caching boundary: WHO he is must be byte-identical every turn, and
    everything that shifts (memory, occasions) must stay out of it — otherwise
    the cache misses every turn and silently buys nothing."""
    from app import companion

    stable, variable = companion.build_system_parts(
        persona_block="ТЫ — Фёдор.",
        elder_facts="Внучку зовут Аня.",
        memory_context="Вчера говорили о рыбалке.",
    )
    assert "Фёдор" in stable
    assert "рыбалке" not in stable
    assert "Аня" in variable
    assert "рыбалке" in variable
