"""From a shadow to somebody — and on (shaping.py).

The owner, 2026-10-08: no interviewer. From the first second the person talks
to him, and at first he is a shadow «with no exact personality»; after several
talks, once the reader is sure what this person needs, the writer writes him —
and from then on «its a build that we are always shaping and making better».
Pinned here is everything that would otherwise first show up in front of
somebody: what a shadow is told, how one is born, when he is written, that he
never changes mid-talk, and that nothing he said about himself is lost.
"""

from __future__ import annotations

import asyncio
import json
import random
import time

import pytest

from app import (brain, config, db, erase, main, matchmaker, memory, persona, reading, shaping,
                 voices)

U = "shaped-one"

STRANGERS = [
    {"name": "Лукас", "gender": "мужской", "age": "16 лет", "home": "Лиссабон, Португалия",
     "doing": "учится в школе и летом помогает дяде в веломастерской",
     "now": "готовится к экзамену по истории"},
    {"name": "Ира", "gender": "женский", "age": "17 лет", "home": "на пароме между Хельсинки и Таллином",
     "doing": "ездит с отцом-механиком", "now": "впервые сама ведёт его журнал рейсов"},
    {"name": "Тимур", "gender": "мужской", "age": "15 лет", "home": "Ванкувер, Канада",
     "doing": "учится и разносит газеты по утрам", "now": "копит на подержанный велосипед"},
]

WRITTEN = {
    "name": "Лука",                       # the writer slipped — the person has heard «Лукас»
    "gender": "женский",                  # and slipped again
    "age": "19 лет",
    "address": "вы",
    "home": "Лиссабон, Алфама, квартира над булочной матери",
    "one_liner": "спокойный, с сухим юмором",
    "backstory": "Вырос в Лиссабоне. Отец уехал рано.",
    "personality": "спокойный, наблюдательный, с сухим юмором",
    "speech_style": "короткие фразы",
    "flaws": ["упрям в мелочах"],
    "intention": "собрать велосипед из запчастей до осени",
    "things": ["ящик с запчастями под кроватью"],
    "expertise": "старые велосипеды",
}


@pytest.fixture
def models(monkeypatch):
    """Every model this file reaches, answered by what it is asked to be — told
    apart by its system prompt, as production tells them apart by model."""
    seen: list[dict] = []
    plan = {"verdicts": ["не с кем говорить всерьёз"] * 9, "same": [True] * 9,
            "strangers": json.dumps(STRANGERS, ensure_ascii=False)}

    async def answer(system, user_text, **kw):
        seen.append({"system": system, "user": user_text, **kw})
        if system.startswith("Ты придумываешь людей"):
            return plan["strangers"]
        if system.startswith("Ты читаешь человека по тому, КАК он говорил"):
            return json.dumps({"verdict": plan["verdicts"].pop(0), "register": "коротко",
                               "would_reach_them": "спокойно", "do_not_touch": "про отца"},
                              ensure_ascii=False)
        if system.startswith("Перед тобой два чтения"):
            return json.dumps({"same": plan["same"].pop(0), "why": "—"})
        if "знакомишь людей" in system:
            return json.dumps(WRITTEN, ensure_ascii=False)
        if "дописываешь человека" in system:
            return json.dumps({"likes": ["смотреть на звёзды с крыши"]}, ensure_ascii=False)
        return "{}"   # the scribe: nothing to keep

    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(brain, "generate_text", answer)
    monkeypatch.setattr(brain, "think", answer)
    return {"seen": seen, "plan": plan}


def _asked(seen: list[dict], opening: str) -> list[dict]:
    return [c for c in seen if c["system"].startswith(opening)]


def _shadow(**over) -> dict:
    shadow = matchmaker.as_shadow(STRANGERS[0], their_age="15", band="teen")
    return persona.save_persona(U, {**shadow, "voice": voices.choose(shadow), **over})


def _talk(words: int = 60, *, goodbye: bool = True) -> None:
    """One more talk, over: the person said `words` words, and each talk lies
    twenty minutes after the one before — two visits, not one — all of them
    well in the past."""
    with db.connect() as conn:
        held = conn.execute("SELECT COUNT(*) n FROM turns WHERE user_id=?", (U,)).fetchone()["n"]
    memory.log_turn(U, "user", " ".join(["слово"] * words))
    memory.log_turn(U, "assistant", "Понятно. А дальше?", farewell=goodbye)
    with db.connect() as conn:
        conn.execute("UPDATE turns SET ts=? WHERE user_id=? AND ts>?",
                     (time.time() - 36_000 + 1_200 * held, U, time.time() - 5))


def _after() -> None:
    asyncio.run(shaping.after_talk(U))


# ── what a shadow is ────────────────────────────────────────────────────────

def test_a_shadow_is_told_to_be_ordinary_and_that_what_he_says_is_kept():
    """Said to somebody with nothing written yet, «you live like a real person:
    friends, habits, your own stories» is an invitation to invent them on the
    spot — and everything he invents becomes law for the writer."""
    block = persona.build_persona_block(_shadow())
    assert "Ты живой обычный человек" in block
    assert "станет правдой о тебе навсегда" in block
    assert "Ты просто живёшь как настоящий человек" not in block
    assert "Лукас" in block and "Лиссабон" in block
    assert "Обращайся к нему на «ты»" in block
    # …and a man already written is not told he is a shadow.
    assert "Ты просто живёшь как настоящий человек" in persona.build_persona_block(WRITTEN)


def test_the_shadow_has_an_english_twin(monkeypatch):
    monkeypatch.setattr(config, "LANGUAGE", "en")
    block = persona.build_persona_block({**_shadow(), "name": "Lucas", "home": "Lisbon",
                                         "one_liner": "at school", "current_life": "exams",
                                         "age": "16"})
    assert "You're an ordinary living person" in block
    assert not any("а" <= ch.lower() <= "я" for ch in block)


# ── how one is born ─────────────────────────────────────────────────────────

def test_ten_strangers_from_the_door_and_the_dice_choose(models):
    born = asyncio.run(matchmaker.create_shadow(U, age="15", country="Узбекистан", band="teen",
                                                rng=random.Random(4)))
    assert persona.is_shadow(persona.load_persona(U))
    assert born["name"] in {s["name"] for s in STRANGERS}
    assert born["voice"]["name"] in voices.NAMES
    assert born["address"] == "ты"
    # The sketch is kept whole: it is what the writer unfolds later.
    assert born["name"] in born["sketch"] and "Где живёт" in born["sketch"]
    asked = _asked(models["seen"], "Ты придумываешь людей")[0]
    assert "РОВЕСНИКОМ" in asked["user"]                     # a teenager meets his own age
    assert "Узбекистан — друг живёт НЕ там" in asked["user"]  # never where the person lives
    assert "СЛУЧАЙНЫЕ ИСКРЫ" in asked["user"]
    assert asked["model"] == config.WRITER_MODEL and asked["effort"] == "low"


def test_a_new_shadow_replaces_the_old_friend_entirely(models):
    persona.save_persona(U, WRITTEN)
    memory.add_memory(U, "fact", "у него есть брат", owner="bob")
    asyncio.run(matchmaker.create_shadow(U, band="teen"))
    assert persona.is_shadow(persona.load_persona(U))
    assert memory.bob_self_context(U) == ""


def test_a_broken_list_of_strangers_is_asked_once_more_then_given_up(models):
    models["plan"]["strangers"] = "не знаю"
    with pytest.raises(RuntimeError):
        asyncio.run(matchmaker.create_shadow(U))
    assert len(_asked(models["seen"], "Ты придумываешь людей")) == 2
    assert not persona.has_persona(U)        # nobody erased for nobody


def test_ty_or_vy_between_two_strangers():
    assert matchmaker.address("15", "16 лет", "teen") == "ты"
    assert matchmaker.address("24", "27 лет") == "ты"
    assert matchmaker.address("45", "70 лет") == "вы"
    assert matchmaker.address("", "30 лет") == "вы"       # unknown: polite mends itself


# ── when he is written ──────────────────────────────────────────────────────

def test_one_talk_is_read_but_never_enough_to_write_him(models):
    _shadow()
    _talk()
    _after()
    kept = reading.load(U)
    assert kept["verdict"] == "не с кем говорить всерьёз"
    assert kept[shaping.STATE]["reads"] == 1
    assert "_portrait" not in persona.load_persona(U)


def test_two_readings_that_agree_write_him(models):
    _shadow()
    for _ in range(2):
        _talk()
        _after()
    written = persona.load_persona(U)["_portrait"]
    assert persona.is_shadow(persona.load_persona(U)), "he must not change until the next talk"
    # What the person has heard stays exactly as heard.
    assert (written["name"], written["gender"], written["age"], written["address"]) == (
        "Лукас", "мужской", "16 лет", "ты")
    assert written["voice"]["name"] == persona.load_persona(U)["voice"]["name"]
    assert "сухим юмором" in written["voice"]["style"]
    assert not written.get("shadow")
    write = [c for c in models["seen"] if "знакомишь людей" in c["system"]][0]
    assert "Лукас" in write["user"] and "разговор 2" in write["user"]
    assert "закон" in write["user"]


def test_readings_that_disagree_wait_but_never_past_the_fifth(models):
    _shadow()
    models["plan"]["same"] = [False] * 9
    for n in range(1, 6):
        _talk()
        _after()
        has = "_portrait" in persona.load_persona(U)
        assert has == (n == 5), f"after talk {n}"


def test_a_hello_and_goodbye_is_not_a_talk_worth_reading(models):
    _shadow()
    _talk(words=5)
    _after()
    assert not _asked(models["seen"], "Ты читаешь человека")


def test_what_wounds_him_survives_a_fresh_reading(models):
    """A person who starts over with a new friend has not become somebody else."""
    _shadow()
    reading.save(U, {"verdict": "старое", "hurt_by": ["когда торопят"], "learned": ["любит тишину"]})
    _talk()
    _after()
    kept = reading.load(U)
    assert "когда торопят" in kept["hurt_by"]
    assert "любит тишину" in kept["learned"]
    assert "про отца" in reading._as_lines(kept["do_not_touch"])


def test_held_for_the_owners_test_the_app_never_writes_him(models):
    _shadow(_held=True)
    for _ in range(3):
        _talk()
        _after()
    assert not models["seen"]


def test_only_a_shadow_is_read_this_way(models):
    persona.save_persona(U, WRITTEN)
    _talk()
    _after()
    assert not models["seen"]


# ── between talks, never during one ─────────────────────────────────────────

def test_he_becomes_the_written_man_only_once_the_talk_is_over(models):
    _shadow()
    for _ in range(2):
        _talk()
        _after()
    memory.log_turn(U, "user", "а, слушай, ещё одно")    # «пока» — and then they carried on
    assert not shaping.settle(U)
    assert persona.is_shadow(persona.load_persona(U))
    with db.connect() as conn:
        conn.execute("UPDATE turns SET ts=? WHERE user_id=?", (time.time() - 3600, U))
    assert shaping.settle(U)
    now = persona.load_persona(U)
    assert not persona.is_shadow(now) and "_portrait" not in now
    assert now["personality"] == WRITTEN["personality"] and now["name"] == "Лукас"


def test_a_goodbye_ends_a_talk(models, monkeypatch):
    began: list[str] = []

    async def noted(user_id):
        began.append(user_id)

    monkeypatch.setattr(shaping, "after_talk", noted)
    from fastapi import BackgroundTasks

    for farewell in (False, True):
        work = BackgroundTasks()
        main._remember(U, "пока", "Пока!", work, farewell=farewell)
        asyncio.run(work())
    assert began == [U]


def test_starting_over_starts_the_count_over(models):
    _shadow()
    _talk()
    _after()
    erase.the_companion(U)
    assert shaping.STATE not in (reading.load(U) or {})


# ── and then he goes on being shaped ────────────────────────────────────────

def test_a_shadow_has_no_week_is_not_deepened_and_not_re_read(models):
    """Not written yet: nothing of him to happen to, to add to, or to revise
    the reading of in between the shadow's own readings."""
    from app import life

    _shadow()
    reading.save(U, {"verdict": "а", "register": "б", "would_reach_them": "в"})
    for _ in range(45):
        memory.log_turn(U, "user", "ну да")
    asyncio.run(persona.deepen(U, now=True))
    asyncio.run(life.maybe_begin(U))
    asyncio.run(reading.keep_reading(U))
    assert not models["seen"]


def test_when_the_reader_learns_something_new_the_writer_adds_to_him(models, monkeypatch):
    persona.save_persona(U, WRITTEN)
    reading.save(U, {"verdict": "не с кем говорить всерьёз", "register": "коротко",
                     "would_reach_them": "спокойно"})
    for _ in range(reading.REREAD_MIN_TURNS):
        memory.log_turn(U, "user", "ну да")

    async def reread(user_id, existing, turns):
        return {**existing, "verdict": "некому показать то, что он рисует"}

    monkeypatch.setattr(reading, "reread", reread)
    asyncio.run(reading.keep_reading(U))
    assert "смотреть на звёзды с крыши" in persona.load_persona(U)["likes"]
    deepen = [c for c in models["seen"] if "дописываешь человека" in c["system"]][0]
    assert "некому показать то, что он рисует" in deepen["user"]


def test_a_reading_that_only_learned_a_line_does_not_reshape_him():
    before = {"verdict": "а", "learned": ["x"]}
    assert not reading.changed(before, {**before, "learned": ["x", "y"]})
    assert reading.changed(before, {**before, "verdict": "б"})
