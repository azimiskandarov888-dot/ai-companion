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

from app import brain, main, matchmaker, memory, persona

FRIEND = {
    "name": "Фёдор",
    "one_liner": "спокойный, тёплый, с хитрым юмором",
    "age": "62 года",
    "home": "город у гор",
    "backstory": "работал архитектором, теперь рисует и гуляет",
    "personality": "спокойный, наблюдательный, с хитрым юмором",
    "speech_style": "короткие фразы, любит словечко «стало быть»",
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
            wishes="Хотел бы кого-то спокойного, кто много читает.",
            age="около 60",
            gender="мужчина",
            origin="Грузия",
        )
    )
    # The reveal: he has his own name — and the user's wishes reached the pen.
    assert created["name"] == "Фёдор"
    assert "кого-то спокойного, кто много читает" in pen[0]
    assert "возраст: около 60" in pen[0]
    assert "пол: мужчина" in pen[0]
    assert "откуда: Грузия" in pen[0]
    assert "Люблю футбол" in pen[0]

    # He is now the live persona — exactly as created, never topped up from
    # the built-in template (that merge is how every friend got the same cat).
    live = persona.load_persona()
    assert live["name"] == "Фёдор"
    assert live["age"] == "62 года"
    assert live["speech_style"] == FRIEND["speech_style"]
    assert "opinions" not in live  # the pen didn't write it → it isn't there
    assert "_note" not in live


def test_no_wishes_is_fine(pen):
    # Leaving "who would you like to meet?" blank is a perfectly good choice —
    # the friend is then built from their story plus the dice alone.
    created = asyncio.run(matchmaker.create_companion("Люблю рыбалку и тишину."))
    assert created["name"] == "Фёдор"
    assert "Пожеланий о друге он не оставил" in pen[0]
    assert "СЛУЧАЙНАЯ ОСНОВА" in pen[0]


def test_dice_supply_the_variety_not_the_model():
    """Two rolls, two different skeletons.

    This is the sameness fix itself: asked to 'invent a person', a language
    model returns its most probable person — the same warm old man by the sea,
    every time. So the skeleton (age, place, trade, temper) is rolled by
    actual dice OUTSIDE the model, and the model only fleshes it out.
    """
    import random

    a = matchmaker._roll_scaffold(rng=random.Random(1))
    b = matchmaker._roll_scaffold(rng=random.Random(2))
    assert a != b
    # Rolling many skeletons must visit many trades — not orbit one archetype.
    trades = {
        line
        for seed in range(30)
        for line in matchmaker._roll_scaffold(rng=random.Random(seed)).splitlines()
        if line.startswith("Кем работает")
    }
    assert len(trades) >= 10


def test_wishes_beat_the_dice(pen):
    # What the user asked for is used verbatim — dice fill only the gaps.
    asyncio.run(
        matchmaker.create_companion(
            "Люблю горы.", age="около 30", gender="женщина", origin="с Урала"
        )
    )
    scaffold = pen[0].split("СЛУЧАЙНАЯ ОСНОВА")[1]
    assert "Возраст: около 30" in scaffold
    assert "Пол: женщина" in scaffold
    assert "Где живёт: с Урала" in scaffold


def test_new_friend_starts_with_a_clean_slate(pen):
    """A new person means a new life — and only HIS side of memory is wiped.

    Without this, friend number two inherits friend number one's stories about
    himself and contradicts his own biography mid-sentence. What was learned
    about the USER stays: their birthday is true no matter who they talk to.
    """
    memory.log_turn("default", "user", "привет")
    memory.add_memory("fact", "Я всю жизнь рыбачил", owner="bob")
    memory.add_memory("fact", "У него день рождения в мае", owner="elder")

    asyncio.run(matchmaker.create_companion("Люблю тишину."))

    assert memory.recent_turns("default") == []
    assert memory.counts("bob").get("fact", 0) == 0
    assert memory.counts("elder").get("fact", 0) == 1


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
            json={
                "about": "Люблю футбол и сериалы",
                "wishes": "Кого-нибудь весёлого",
                "age": "30",
                "gender": "женщина",
            },
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Фёдор"

        # …and the wishes are optional — the story alone is enough.
        assert (
            client.post(
                "/api/companion/create", json={"about": "Люблю тишину"}
            ).status_code
            == 200
        )

        # An empty story is the one thing we can't work with.
        assert (
            client.post("/api/companion/create", json={"about": "   "}).status_code
            == 400
        )
