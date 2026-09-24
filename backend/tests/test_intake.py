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
import re

import pytest
from fastapi.testclient import TestClient

from app import brain, intake, main, matchmaker, reading


def test_the_first_question_costs_nothing_and_cannot_go_wrong(monkeypatch):
    """The opener is fixed, not generated: instant, and the one question
    nobody needs a model for — there is nothing yet to react to."""
    def explode(*a, **k):
        raise AssertionError("the opener must never call the model")

    monkeypatch.setattr(brain, "generate_text", explode)

    first = intake.opening(random.Random(1))
    assert first["say"] == "Как вас зовут?" and first["target"] == "name"
    assert not first["enough"]
    # And it says the true thing that makes the whole conversation work.
    assert "Его ещё нет" in first["preamble"]
    assert "не об анкете" in first["preamble"]


class _Seen(list):
    """What each call was shown (`self`, as a plain list of prompts) — plus,
    tacked on, the `timeout` each call was made with. A subclass rather than a
    tuple so every existing `asker[-1]` / `asker[0]` keeps working unchanged."""
    timeouts: list[float | None]


@pytest.fixture
def asker(monkeypatch):
    """Fake the question model; record what it was shown and asked to bound.
    It asks whatever the list says is next — as a well-behaved model does."""
    seen = _Seen()
    seen.timeouts = []

    async def fake_generate(system_prompt, user_text, max_tokens=1500, model=None,
                            timeout=None, effort=None):
        seen.append(user_text)
        seen.timeouts.append(timeout)
        nxt = re.search(r"Сейчас по плану — (\w+)", user_text)
        return json.dumps({"reaction": "Река — хорошо.",
                           "say": "А кто вас научил рыбачить?",
                           "target": nxt.group(1) if nxt else "",
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
    """n answered turns, tagged with the list's targets in order."""
    ids = [t[0] for t in intake.TARGETS]
    return [{"q": f"в{i}", "a": f"о{i}", "target": ids[i] if i < len(ids) else ""}
            for i in range(n)]


def test_the_list_is_kept_by_us_not_guessed_by_the_model(asker):
    """A model left to cover topics follows a good thread and covers the first
    one three times — the owner's intake spent three questions on his startup.
    So every call is told what is done and what is next, from the targets the
    client hands back."""
    asyncio.run(intake.next_question(_talked(1)))
    assert "Сейчас по плану — days" in asker[-1]
    assert "Уже выяснено: как его зовут" in asker[-1]

    asyncio.run(intake.next_question(_talked(7)))
    assert "Сейчас по плану — strength" in asker[-1]

    # The last one, and the only one that asks for a written answer.
    asyncio.run(intake.next_question(_talked(len(intake.TARGETS) - 1)))
    assert "Сейчас по плану — closing" in asker[-1] and '"open"' in asker[-1]


def test_nichem_gets_a_follow_up_not_the_next_question(asker):
    """The owner answered «ничем» and the next question came as if nobody had
    heard. Now the call after any answer offers ONE follow-up to it — about a
    concrete case — before the list moves on."""
    asyncio.run(intake.next_question([
        {"q": "Как вас зовут?", "a": "Азим", "target": "name"},
        {"q": "А день обычно чем занят?", "a": "ничем", "target": "days"},
    ]))
    assert 'сначала ОДИН уточняющий вопрос к нему, и тогда "target": "days"' in asker[-1]
    assert "«ничем» — «А вчера, например, как прошёл?»" in intake._ASK_SYSTEM


def test_one_follow_up_per_answer_then_the_list_moves_on(asker):
    asyncio.run(intake.next_question([
        {"q": "Как вас зовут?", "a": "Азим", "target": "name"},
        {"q": "А день обычно чем занят?", "a": "ничем", "target": "days"},
        {"q": "А вчера, например?", "a": "спал", "target": "days"},
    ]))
    assert "уточняющий" not in asker[-1]
    assert "Сейчас по плану — love" in asker[-1]


def test_the_deep_question_gets_a_bigger_box(monkeypatch):
    """`kind` is how the app knows to hand over a taller field — the size of
    the space you're given is itself an instruction about how much to say. The
    last question gets it whatever the model says."""
    async def deep(system_prompt, user_text, **kw):
        return json.dumps({"reaction": "", "say": "А о чём бы поговорить, да не с кем?",
                           "target": "closing", "kind": "short", "enough": False},
                          ensure_ascii=False)

    monkeypatch.setattr(brain, "generate_text", deep)
    turns = _talked(len(intake.TARGETS) - 1)
    assert asyncio.run(intake.next_question(turns))["kind"] == "open"


def test_an_unknown_kind_degrades_to_the_safe_one(monkeypatch):
    async def odd(system_prompt, user_text, **kw):
        return json.dumps({"say": "А день чем занят?", "target": "days",
                           "kind": "gigantic"}, ensure_ascii=False)

    monkeypatch.setattr(brain, "generate_text", odd)
    assert asyncio.run(intake.next_question(_talked(1)))["kind"] == "short"


def test_a_model_that_stops_early_is_overruled_by_the_list(monkeypatch):
    """Country and age decide the emergency number and how a child is kept, so
    a model that decides «enough» before the list is done does not get its
    way: the list asks its own question next, keeping the model's reaction."""
    async def done(system_prompt, user_text, **kw):
        return json.dumps({"reaction": "Понятно.", "say": "", "enough": True},
                          ensure_ascii=False)

    monkeypatch.setattr(brain, "generate_text", done)
    result = asyncio.run(intake.next_question(_talked(4)))
    assert result["enough"] is False
    assert result["target"] == "country" and "стране" in result["say"]
    assert result["reaction"] == "Понятно."


def test_a_question_off_the_list_is_replaced_by_the_lists_own(monkeypatch):
    async def wander(system_prompt, user_text, **kw):
        return json.dumps({"say": "А какая у вас любимая песня?", "target": "music"},
                          ensure_ascii=False)

    monkeypatch.setattr(brain, "generate_text", wander)
    result = asyncio.run(intake.next_question(_talked(3)))
    assert result["target"] == "coming_up"
    assert result["say"] == "А на этой неделе что намечается?"


def test_trouble_ends_it_at_once(monkeypatch):
    """The one early end that is honoured: somebody in trouble right now."""
    async def trouble(system_prompt, user_text, **kw):
        return json.dumps({"reaction": "Об этом лучше поговорить с близкими.",
                           "say": "", "enough": True, "trouble": True}, ensure_ascii=False)

    monkeypatch.setattr(brain, "generate_text", trouble)
    result = asyncio.run(intake.next_question(_talked(3)))
    assert result["enough"] is True and "близкими" in result["reaction"]


def test_the_last_answer_gets_a_last_word(monkeypatch):
    """After «о чём бы поговорить, да не с кем?» — often the most private thing
    said all intake — it does not just stop: one warm line, and it ends."""
    seen = []

    async def parting(system_prompt, user_text, **kw):
        seen.append(user_text)
        return json.dumps({"reaction": "Спасибо, что сказал.", "say": "Ещё вопрос?",
                           "enough": False}, ensure_ascii=False)

    monkeypatch.setattr(brain, "generate_text", parting)
    result = asyncio.run(intake.next_question(_talked(len(intake.TARGETS))))
    assert result["enough"] is True and result["say"] == ""
    assert result["reaction"] == "Спасибо, что сказал."
    # Told to end with a warm line (or, once, to rescue a vague answer) — and
    # a question off the list here is not a rescue, so it ends.
    assert "больше не спрашивай" in seen[-1]


def test_the_next_question_sees_the_whole_conversation(asker):
    result = asyncio.run(intake.next_question([
        {"q": "Что видно из окна?", "a": "Река. Я там рыбачил с отцом.", "target": "name"},
    ]))
    assert result["say"] == "А кто вас научил рыбачить?"
    assert "Река. Я там рыбачил с отцом." in asker[0]
    assert "Что видно из окна?" in asker[0]


def test_it_always_stops_eventually(monkeypatch):
    """MAX_TURNS is a stop, not a target. Someone tiring must never be held."""
    async def parting(system_prompt, user_text, **kw):
        return json.dumps({"reaction": "", "say": "ещё?", "enough": False})

    monkeypatch.setattr(brain, "generate_text", parting)
    conversation = [{"q": f"в{i}", "a": f"о{i}", "target": "days"}
                    for i in range(intake.MAX_TURNS)]
    assert asyncio.run(intake.next_question(conversation))["enough"] is True


def test_a_skipped_question_is_not_asked_again(asker):
    """Somebody who skips «сколько вам лет» has answered it, in the only way
    they wanted to. Asked again, it would be a form that will not take no."""
    turns = _talked(5) + [{"q": "Сколько вам лет?", "a": "", "target": "age"}]
    asyncio.run(intake.next_question(turns))
    assert "Сейчас по плану — miss" in asker[-1]


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
        assert body["say"] == "Как вас зовут?" and body["target"] == "name"
        assert "Его ещё нет" in body["preamble"]


def test_the_conversation_becomes_the_story_a_friend_is_built_from(monkeypatch):
    """The point of the whole change: what someone SAYS out loud becomes the
    material, instead of what they can bring themselves to type into a box."""
    read: list[str] = []

    async def fake_read(about, wishes=""):
        read.append(about)
        return {"register": "коротко", "would_reach_them": "спокойно"}

    async def fake_generate(system_prompt, user_text, max_tokens=1500, model=None,
                            timeout=None, effort=None):
        return "1. Зоя, 31, север, крановщица.\n2. Пётр, 44, село, пасечник."

    async def fake_think(system_prompt, user_text, **kwargs):
        return json.dumps({
            "name": "Зоя", "age": "31 год", "home": "северный город",
            "backstory": "выросла у реки", "personality": "прямая", "flaws": ["перебивает"], "intention": "перебрать лодку до заморозков",
            "things": ["чайник, который свистит не так", "кресло у окна"],
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

    async def fake_generate(system_prompt, user_text, max_tokens=1500, model=None,
                            timeout=None, effort=None):
        return "1. Гриша, 73, посёлок, сварщик.\n2. Нина, 52, горы, фельдшер."

    async def fake_think(system_prompt, user_text, **kwargs):
        return json.dumps({
            "name": "Гриша", "age": "73 года", "home": "посёлок",
            "backstory": "варил всю жизнь", "personality": "ворчливый", "flaws": ["перебивает"], "intention": "перебрать лодку до заморозков",
            "things": ["чайник, который свистит не так", "кресло у окна"],
            "speech_style": "коротко",
        }, ensure_ascii=False)

    monkeypatch.setattr(reading, "read_person", fake_read)
    monkeypatch.setattr(brain, "generate_text", fake_generate)
    monkeypatch.setattr(brain, "think", fake_think)

    with TestClient(main.app) as client:
        r = client.post("/api/companion/create", json={"about": "Люблю рыбалку и тишину."})
        assert r.status_code == 200
        assert r.json()["name"] == "Гриша"


# ── the first conversation must not assume a life mostly behind him ─────────
#
# This is the app's first impression, and it feeds the reading that shapes
# everything downstream — so an intake that asks an old person's questions of a
# young one builds the whole friendship out of awkward, disengaged answers.

def test_the_questions_fit_any_life():
    """«Кем работали?» to a twenty-year-old is as far off as «а в школе как?»
    to an eighty-year-old. The six are written so that neither can happen:
    none of them assumes work, school, a family or an age."""
    ask = intake._ASK_SYSTEM
    for assumed in ("кем работали", "в школе", "какую музыку слушал в молодости",
                    "что сказал бы себе молодому", "внук"):
        assert assumed not in ask.lower(), assumed


def test_ty_or_vy_is_decided_and_no_longer_an_absolute():
    """«Вы» to somebody of twenty reads as a personnel department, which closes
    them on the first line — and before the age is known there is nothing to
    decide it by, so it starts polite and switches once it is."""
    ask = intake._ASK_SYSTEM
    assert "Обращайся на «вы», но по-домашнему" not in ask
    assert "НА «ТЫ» ИЛИ НА «ВЫ». Пока возраст не известен — «вы»" in ask
    # …and it fails toward politeness, which is the recoverable mistake
    assert "лишняя вежливость поправима, панибратство нет" in ask


def test_the_most_important_answer_gets_one_rescue(monkeypatch):
    """«Да ни о чём, всё равно не поймут» is an answer — a telling one — but
    it is not yet what about, and what about is why the interview exists. So
    after the last question, once, the model may ask about a past episode;
    after that, it ends whatever it says."""
    seen = []

    async def rescue(system_prompt, user_text, **kw):
        seen.append(user_text)
        return json.dumps({"reaction": "Понятно.",
                           "say": "А последний раз о чём хотелось рассказать, да некому было?",
                           "target": "closing", "kind": "short", "enough": False},
                          ensure_ascii=False)

    monkeypatch.setattr(brain, "generate_text", rescue)
    turns = _talked(len(intake.TARGETS))
    first = asyncio.run(intake.next_question(turns))
    assert first["enough"] is False and first["kind"] == "open"
    assert "А последний раз о чём хотелось рассказать, да некому было?" in seen[-1]

    turns.append({"q": first["say"], "a": "что выгораю", "target": "closing"})
    second = asyncio.run(intake.next_question(turns))
    assert second["enough"] is True and second["say"] == ""
