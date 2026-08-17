"""«Пока его нет» — the conversation that replaced the blank page.

A blank «расскажите о себе» box is a form, and a form is the one thing this
app must not put in front of a lonely person. It also produced exactly the
register the reading cannot work with: a composed paragraph, in which none of
the psycholinguistic signals survive. These tests pin the properties that make
the replacement better rather than merely different.
"""

from __future__ import annotations

import asyncio
import json
import random

import pytest
from fastapi.testclient import TestClient

from app import brain, intake, main, matchmaker, reading


def test_the_first_question_costs_nothing_and_cannot_go_wrong(monkeypatch):
    """The opener decides whether someone engages at all, so it is fixed, not
    generated: instant, and never a bad question on the one that matters most."""
    def explode(*a, **k):
        raise AssertionError("the opener must never call the model")

    monkeypatch.setattr(brain, "generate_text", explode)

    first = intake.opening(random.Random(1))
    assert first["say"] in intake._OPENERS
    assert not first["enough"]
    # And it says the true thing that makes the whole conversation work.
    assert "Его ещё нет" in first["preamble"]


def test_every_opener_is_easy_AND_obviously_about_them():
    """Two jobs, not one — and the second is the one the first draft missed.

    Optimising only for "easy to answer" produced «что видно у вас из окна?»,
    which was rejected on sight: *what does that gotta do with anything?* The
    trivially-concrete opener is a real technique, but it only works once
    trust exists; on a cold first screen a question with no visible purpose
    reads as a machine working through a list. So each opener must also be
    plainly about the person's own life.
    """
    for opener in intake._OPENERS:
        assert opener.endswith("?")
        assert len(opener) < 70
        # Never a feeling asked about directly — that's a therapist, not a friend.
        for forbidden in ("чувств", "переживa", "на душе"):
            assert forbidden not in opener.lower()
        # …and it must be addressed to them, not to the room around them.
        assert any(word in opener.lower() for word in ("вы", "ваш", "вас"))


class _Seen(list):
    """What each call was shown (`self`, as a plain list of prompts) — plus,
    tacked on, the `timeout` each call was made with. A subclass rather than a
    tuple so every existing `asker[-1]` / `asker[0]` keeps working unchanged."""
    timeouts: list[float | None]


@pytest.fixture
def asker(monkeypatch):
    """Fake the question model; record what it was shown and asked to bound."""
    seen = _Seen()
    seen.timeouts = []

    async def fake_generate(system_prompt, user_text, max_tokens=1500, model=None, timeout=None):
        seen.append(user_text)
        seen.timeouts.append(timeout)
        return json.dumps({"reaction": "Река — хорошо.",
                           "say": "А кто вас научил рыбачить?",
                           "kind": "short", "enough": False}, ensure_ascii=False)

    monkeypatch.setattr(brain, "generate_text", fake_generate)
    return seen


def test_the_question_call_is_bounded_under_the_phones_ceiling(asker):
    """/api/intake/next has a real client-side timeout (25s — see
    BackendClient.intakeNext). Left unbounded, a stalled connection to Claude
    has the backend waiting up to ten minutes while the phone has long since
    given up — which is exactly what a frozen onboarding screen looks like,
    because nothing has failed yet on this end to explain it."""
    asyncio.run(intake.next_question(_talked(5)))
    assert asker.timeouts and all(t is not None and t < 25 for t in asker.timeouts)


def _talked(n: int) -> list[dict]:
    return [{"q": f"в{i}", "a": f"о{i}"} for i in range(n)]


def test_the_ladder_is_paced_by_us_not_guessed_by_the_model(asker):
    """Escalating self-disclosure only works if it actually escalates.

    Left to judge "is it time for the deep one?", the model either fires it
    at someone who has said four words — which closes people, the exact
    failure the ladder exists to avoid — or never arrives at it at all. So
    the stage is computed here and handed over.
    """
    # Only the browser dev page reaches this rung — the app's own warm-up has
    # already produced nine answers before the backend is ever called.
    asyncio.run(intake.next_question(_talked(1)))
    assert "рано для настоящего вопроса" in asker[-1]

    # Where the app actually hands over: plenty of room, so ask about a life.
    asyncio.run(intake.next_question(_talked(9)))
    assert "Спроси про его жизнь" in asker[-1]

    # Nearing the end: their people, and hold the real question back.
    asyncio.run(intake.next_question(_talked(intake.MAX_TURNS - 4)))
    assert "про людей" in asker[-1] and "прибереги на конец" in asker[-1]

    # The last rung, and the only one that may ask for a written answer.
    asyncio.run(intake.next_question(_talked(intake.MAX_TURNS - 1)))
    assert "Пора" in asker[-1] and '"open"' in asker[-1]


def test_the_deep_question_gets_a_bigger_box(monkeypatch):
    """`kind` is how the app knows to hand over a taller field — the size of
    the space you're given is itself an instruction about how much to say."""
    async def deep(system_prompt, user_text, max_tokens=1500, model=None, timeout=None):
        return json.dumps({"reaction": "", "say": "О чём думаете, когда не спится?",
                           "kind": "open", "enough": False}, ensure_ascii=False)

    monkeypatch.setattr(brain, "generate_text", deep)
    assert asyncio.run(intake.next_question(_talked(2)))["kind"] == "open"


def test_an_unknown_kind_degrades_to_the_safe_one(monkeypatch):
    async def odd(system_prompt, user_text, max_tokens=1500, model=None, timeout=None):
        return json.dumps({"say": "Кем работали?", "kind": "gigantic"}, ensure_ascii=False)

    monkeypatch.setattr(brain, "generate_text", odd)
    assert asyncio.run(intake.next_question(_talked(2)))["kind"] == "short"


def test_ending_needs_no_question(monkeypatch):
    """A turn that ends the conversation carries no question, and that is not
    a malformed reply — refusing it would strand people at the last step."""
    async def done(system_prompt, user_text, max_tokens=1500, model=None, timeout=None):
        return json.dumps({"say": "", "enough": True}, ensure_ascii=False)

    monkeypatch.setattr(brain, "generate_text", done)
    assert asyncio.run(intake.next_question(_talked(5)))["enough"] is True


def test_the_next_question_sees_the_whole_conversation(asker):
    result = asyncio.run(intake.next_question([
        {"q": "Что видно из окна?", "a": "Река. Я там рыбачил с отцом."},
    ]))
    assert result["say"] == "А кто вас научил рыбачить?"
    assert "Река. Я там рыбачил с отцом." in asker[0]
    assert "Что видно из окна?" in asker[0]


def test_it_always_stops_eventually(monkeypatch):
    """MAX_TURNS is a stop, not a target. Someone tiring must never be held."""
    def explode(*a, **k):
        raise AssertionError("past the cap it must stop without asking the model")

    monkeypatch.setattr(brain, "generate_text", explode)
    conversation = [{"q": f"в{i}", "a": f"о{i}"} for i in range(intake.MAX_TURNS)]
    assert asyncio.run(intake.next_question(conversation))["enough"] is True


def test_unanswered_questions_do_not_count_toward_the_cap(asker):
    """Someone who skips three questions has not had three turns of talking —
    counting them would end the conversation before it started."""
    conversation = [{"q": f"в{i}", "a": ""} for i in range(intake.MAX_TURNS)]
    result = asyncio.run(intake.next_question(conversation))
    assert result["enough"] is False   # still asking, because nothing was said


def test_the_story_is_their_words_not_the_questions():
    """The reading weighs HOW they said things. Handed an undifferentiated
    transcript it reads the interviewer's vocabulary as the person's own."""
    story = intake.as_story([
        {"q": "Что видно из окна?", "a": "Река."},
        {"q": "А кто рядом живёт?", "a": ""},          # skipped — must vanish
        {"q": "Что сегодня ели?", "a": "Гречку. Мне не готовится в последнее время."},
    ])
    assert "Река." in story
    assert "Мне не готовится" in story                  # the dative survives
    assert "А кто рядом живёт?" not in story            # skipped question gone
    assert story.count("—") == 2                        # only answered ones kept


def test_a_broken_question_ends_the_conversation_instead_of_stranding_anyone(monkeypatch):
    async def broken(*a, **k):
        raise RuntimeError("модель недоступна")

    monkeypatch.setattr(brain, "generate_text", broken)
    with TestClient(main.app) as client:
        r = client.post("/api/intake/next", json={
            "conversation": [{"q": "Что видно из окна?", "a": "Двор."}],
        })
        assert r.status_code == 200
        assert r.json()["enough"] is True     # graceful end, not a 500


def test_the_endpoint_opens_without_a_model(monkeypatch):
    def explode(*a, **k):
        raise AssertionError("opening must not call the model")

    monkeypatch.setattr(brain, "generate_text", explode)
    with TestClient(main.app) as client:
        body = client.post("/api/intake/next", json={"conversation": []}).json()
        assert body["say"] in intake._OPENERS
        assert "Его ещё нет" in body["preamble"]


def test_the_conversation_becomes_the_story_a_friend_is_built_from(monkeypatch):
    """The point of the whole change: what someone SAYS out loud becomes the
    material, instead of what they can bring themselves to type into a box."""
    read: list[str] = []

    async def fake_read(about, wishes=""):
        read.append(about)
        return {"register": "коротко", "would_reach_them": "спокойно"}

    async def fake_generate(system_prompt, user_text, max_tokens=1500, model=None, timeout=None):
        return "1. Зоя, 31, север, крановщица.\n2. Пётр, 44, село, пасечник."

    async def fake_think(system_prompt, user_text, **kwargs):
        return json.dumps({
            "name": "Зоя", "age": "31 год", "home": "северный город",
            "backstory": "выросла у реки", "personality": "прямая",
            "speech_style": "коротко",
        }, ensure_ascii=False)

    monkeypatch.setattr(reading, "read_person", fake_read)
    monkeypatch.setattr(brain, "generate_text", fake_generate)
    monkeypatch.setattr(brain, "think", fake_think)

    with TestClient(main.app) as client:
        r = client.post("/api/companion/create", json={
            "conversation": [
                {"q": "Что видно из окна?", "a": "Река. Мне не спится последнее время."},
                {"q": "А кто рядом?", "a": "Да никого."},
            ],
            "wishes": "кого-нибудь спокойного",
        })
        assert r.status_code == 200
        assert r.json()["name"] == "Зоя"

    # Their exact words reached the reading — including the dative impersonal
    # and the absence, which is what the reading exists to notice.
    assert "Мне не спится" in read[0]
    assert "Да никого." in read[0]


def test_an_empty_conversation_is_still_refused(monkeypatch):
    """Someone who says nothing at all cannot be read, and a friend invented
    from nothing is exactly the generic stranger this app removed."""
    with TestClient(main.app) as client:
        assert client.post("/api/companion/create", json={"conversation": []}).status_code == 400
        assert client.post(
            "/api/companion/create",
            json={"conversation": [{"q": "Что видно из окна?", "a": "   "}]},
        ).status_code == 400


def test_free_writing_still_works(monkeypatch):
    """The browser dev page and anyone who'd rather type keep the old path."""
    async def fake_read(about, wishes=""):
        return {"register": "коротко", "would_reach_them": "спокойно"}

    async def fake_generate(system_prompt, user_text, max_tokens=1500, model=None, timeout=None):
        return "1. Гриша, 73, посёлок, сварщик.\n2. Нина, 52, горы, фельдшер."

    async def fake_think(system_prompt, user_text, **kwargs):
        return json.dumps({
            "name": "Гриша", "age": "73 года", "home": "посёлок",
            "backstory": "варил всю жизнь", "personality": "ворчливый",
            "speech_style": "коротко",
        }, ensure_ascii=False)

    monkeypatch.setattr(reading, "read_person", fake_read)
    monkeypatch.setattr(brain, "generate_text", fake_generate)
    monkeypatch.setattr(brain, "think", fake_think)

    with TestClient(main.app) as client:
        r = client.post("/api/companion/create", json={"about": "Люблю рыбалку и тишину."})
        assert r.status_code == 200
        assert r.json()["name"] == "Гриша"
