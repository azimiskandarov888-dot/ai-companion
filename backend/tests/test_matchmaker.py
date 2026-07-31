"""A friend walks in — created from the user's story, never designed by them.

The user writes about themselves and picks only age / gender / origin. The
friend's name and character are chosen for them (common ground included), and
he becomes the live persona the voice loop speaks as.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app import brain, main, matchmaker, persona

FRIEND = {
    "name": "Фёдор",
    "one_liner": "спокойный, тёплый, с хитрым юмором",
    "age": "62 года",
    "home": "город у гор",
    "backstory": "работал архитектором, теперь рисует и гуляет",
    "likes": ["футбол", "старые фильмы", "архитектура"],
    "dislikes": ["спешку"],
    "habits": ["утренние прогулки"],
    "cast": [{"name": "Гоша", "who": "сосед и напарник по шахматам"}],
}


@pytest.fixture
def pen(monkeypatch):
    """Fake the AI with a reply wrapped in prose + code fences (the messy case)."""
    calls: list[str] = []

    async def fake_generate(system_prompt, user_text, max_tokens=1500):
        calls.append(user_text)
        return "Вот его друг:\n```json\n" + json.dumps(FRIEND, ensure_ascii=False) + "\n```"

    monkeypatch.setattr(brain, "generate_text", fake_generate)
    return calls


def test_friend_is_created_and_becomes_the_persona(pen):
    created = asyncio.run(
        matchmaker.create_companion(
            "Люблю футбол, старые фильмы и архитектуру.",
            age="около 60",
            gender="мужчина",
            origin="Грузия",
        )
    )
    # The reveal: he has his own name — and the user's wishes reached the pen.
    assert created["name"] == "Фёдор"
    assert "возраст: около 60" in pen[0]
    assert "пол: мужчина" in pen[0]
    assert "откуда: Грузия" in pen[0]
    assert "Люблю футбол" in pen[0]

    # He is now the live persona (missing fields filled from the safe default).
    live = persona.load_persona()
    assert live["name"] == "Фёдор"
    assert live["age"] == "62 года"
    assert live["speech_style"]  # default filled in
    assert "_note" not in live


def test_unparseable_reply_fails_gently(monkeypatch):
    async def fake_generate(system_prompt, user_text, max_tokens=1500):
        return "Извини, сегодня без JSON."

    monkeypatch.setattr(brain, "generate_text", fake_generate)
    with pytest.raises(RuntimeError):
        asyncio.run(matchmaker.create_companion("про меня"))


def test_create_endpoint(pen):
    with TestClient(main.app) as client:
        r = client.post(
            "/api/companion/create",
            json={"about": "Люблю футбол и сериалы", "age": "30", "gender": "женщина"},
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Фёдор"

        # An empty story is the one thing we can't work with.
        assert (
            client.post("/api/companion/create", json={"about": "   "}).status_code
            == 400
        )
