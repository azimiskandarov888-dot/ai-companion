"""Brain wiring: the web-search tool is configured (real news/weather on ask)."""

from __future__ import annotations

from app import brain


def test_web_search_tool_configured():
    tool = brain._WEB_SEARCH_TOOL
    assert tool["name"] == "web_search"
    assert tool["type"].startswith("web_search_")
    # Capped so one question can't spiral into many searches.
    assert tool["max_uses"] >= 1
