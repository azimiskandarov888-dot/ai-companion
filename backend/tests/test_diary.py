"""The companion's diary — beautiful for the user, cached, never raw memory.

The real (distilled) memory stays internal; the diary is the only memory view
users get. It is AI-written from that memory and rewritten only when the
memory has changed.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app import brain, diary, identity, main, memory

#: The endpoint tests call /api/diary with no token, so everything here is
#: about the anonymous user.
U = identity.ANONYMOUS


@pytest.fixture
def pen(monkeypatch):
    """Replace the AI writer with a fake pen that counts its uses."""
    calls: list[tuple[str, str]] = []

    async def fake_generate(system_prompt, user_text, max_tokens=1500):
        calls.append((system_prompt, user_text))
        return "Красивая запись о моём друге."

    monkeypatch.setattr(brain, "generate_text", fake_generate)
    return calls


def test_first_page_needs_no_ai(pen):
    # Before he knows anything, the book opens on a warm first page — free.
    result = asyncio.run(diary.get_diary(U))
    assert "только-только познакомились" in result["text"]
    assert pen == []  # no AI call for an empty memory


def test_writes_from_memory_and_caches(pen):
    memory.add_memory(U, "fact", "любит футбол и старые фильмы")
    memory.add_memory(U, "story", "рассказал, как в детстве жил у моря", title="Море")

    first = asyncio.run(diary.get_diary(U))
    assert first["text"] == "Красивая запись о моём друге."
    assert first["rewritten"] is True
    assert len(pen) == 1

    # The notes handed to the pen are his distilled memory, grouped and titled.
    _, notes = pen[0]
    assert "любит футбол" in notes
    assert "«Море»" in notes

    # Same memory → the cached page is reused, the pen stays down.
    second = asyncio.run(diary.get_diary(U))
    assert second["text"] == first["text"]
    assert second["rewritten"] is False
    assert len(pen) == 1


def test_rewritten_when_memory_grows(pen):
    memory.add_memory(U, "fact", "любит футбол")
    asyncio.run(diary.get_diary(U))
    memory.add_memory(U, "story", "съездил на рыбалку с внуком")
    result = asyncio.run(diary.get_diary(U))
    assert result["rewritten"] is True
    assert len(pen) == 2


def test_follow_ups_stay_his_own(pen):
    # Follow-ups are his private intentions — they never reach the book's notes.
    memory.add_memory(U, "fact", "любит футбол")
    memory.add_memory(U, "follow_up", "спросить, как прошло у врача")
    asyncio.run(diary.get_diary(U))
    _, notes = pen[0]
    assert "как прошло у врача" not in notes


def test_diary_endpoint(pen):
    memory.add_memory(U, "fact", "любит футбол")
    with TestClient(main.app) as client:
        data = client.get("/api/diary").json()
    assert data["text"] == "Красивая запись о моём друге."
    assert data["companion"]
