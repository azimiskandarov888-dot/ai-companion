"""One companion, from a blank to somebody, written in layers (shaping.py).

The owner, 2026-10-09: no separate «shadow» — the same companion from the
first second, «как пустая бланка», a random name and the person's own wishes;
then «дописываться и раскрываться» the way people open up, because to write
him we must know the person. Pinned here: he is born with no model at all,
the person's wishes hold from the first minute, the layers come in the order
people open up and only when it is time, a layer only fills what is empty —
what he has said aloud is never replaced, what is only written is put right
only when checked (consistency.py) — and he never changes in the middle of a talk.
"""

from __future__ import annotations

import asyncio
import json
import random
import time

import pytest

from app import (brain, config, db, erase, main, matchmaker, memory, meeting, persona,
                 reading, shaping, voices, young)

U = "being-written"

#: What the writer would give for every field; each layer takes only its own.
EVERYTHING = {
    "name": "Кто-то другой", "gender": "женский", "age": "40 лет",   # never taken: law
    "one_liner": "спокойный, с сухим юмором", "home": "Лиссабон, квартира над булочной",
    "roots": "из Одессы", "personality": "спокойный, наблюдательный, с сухим юмором",
    "speech_style": "короткие фразы", "values": "честность", "current_life": "чинит велосипед",
    "expertise": "старые велосипеды", "wants_to_learn": "программировать",
    "hopeless": ["деньги"], "likes": ["дождь"], "dislikes": ["спешку"],
    "opinions": ["зима лучше лета"], "habits": ["встаёт рано"],
    "things": ["ящик с запчастями"], "cast": [{"name": "Жозе", "who": "дядя", "between": "долг"}],
    "intention": "собрать велосипед до осени",
    "backstory": "Вырос у моря. Учился на механика.", "flaws": ["упрям в мелочах"],
    "contradiction": "ругает город, а уезжать не хочет", "wound": "отец уехал рано",
    "inner_world": "думает о море",
}


@pytest.fixture
def models(monkeypatch):
    """Every model this file reaches, answered by what it is asked to be."""
    seen: list[dict] = []
    plan = {"verdicts": ["не с кем говорить всерьёз"] * 9, "same": [True] * 9,
            "check": {"rejected": [], "fixes": {}}}

    async def answer(system, user_text, **kw):
        seen.append({"system": system, "user": user_text, **kw})
        if system.startswith("Ты читаешь человека по тому, КАК он говорил"):
            return json.dumps({"verdict": plan["verdicts"].pop(0), "register": "коротко",
                               "would_reach_them": "спокойно", "do_not_touch": "про отца"},
                              ensure_ascii=False)
        if system.startswith("Перед тобой два чтения"):
            return json.dumps({"same": plan["same"].pop(0), "why": "—"})
        if system.startswith("Ты пишешь человека, который уже существует"):
            revise = {"revise": plan["revise"]} if plan.get("revise") else {}
            return json.dumps({**EVERYTHING, **revise}, ensure_ascii=False)
        if system.startswith("Ты сверщик собеседника"):
            return json.dumps(plan["check"], ensure_ascii=False)
        if "дописываешь человека" in system:
            return json.dumps({"likes": ["смотреть на звёзды с крыши"]}, ensure_ascii=False)
        return "{}"   # the scribe: nothing to keep

    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(brain, "generate_text", answer)
    monkeypatch.setattr(brain, "think", answer)
    return {"seen": seen, "plan": plan}


def _asked(seen: list[dict], opening: str) -> list[dict]:
    return [c for c in seen if c["system"].startswith(opening)]


def _born(**over) -> dict:
    him = matchmaker.blank(wants="парень, любит футбол", their_age="15", band="teen",
                           rng=random.Random(1))
    return persona.save_persona(U, {**him, "voice": voices.choose(him), **over})


def _talk(words: int = 60, *, goodbye: bool = True) -> None:
    """One more talk, over: the person said `words` words, each talk twenty
    minutes after the one before — separate visits — all in the past."""
    with db.connect() as conn:
        held = conn.execute("SELECT COUNT(*) n FROM turns WHERE user_id=?", (U,)).fetchone()["n"]
    memory.log_turn(U, "user", " ".join(["слово"] * words))
    memory.log_turn(U, "assistant", "Понятно. А дальше?", farewell=goodbye)
    with db.connect() as conn:
        conn.execute("UPDATE turns SET ts=? WHERE user_id=? AND ts>?",
                     (time.time() - 36_000 + 1_200 * held, U, time.time() - 5))


def _after_and_settle() -> int:
    """A talk ends; the next begins. Returns how many layers he has then."""
    asyncio.run(shaping.after_talk(U))
    shaping.settle(U)
    return persona.written(persona.load_persona(U))


# ── born blank ──────────────────────────────────────────────────────────────

def test_he_is_born_with_no_model_at_all(monkeypatch):
    """A random name and the person's wishes — instant, free."""
    async def nobody(*a, **k):
        raise AssertionError("no model may be asked to make a blank")

    monkeypatch.setattr(brain, "generate_text", nobody)
    monkeypatch.setattr(brain, "think", nobody)
    him = matchmaker.create_blank(U, wants="с девушкой постарше, весёлой", their_age="30",
                                  rng=random.Random(2))
    assert persona.written(him) == 0
    assert him["gender"] == "женский" and int(him["age"]) > 30
    assert him["name"] in matchmaker._NAMES[("ru", "ж")]["middle"]
    assert him["given"] == "с девушкой постарше, весёлой"
    assert him["voice"]["name"] in voices.NAMES


@pytest.mark.parametrize("wants,their_age,band,gender,age", [
    ("с парнем", "15", "teen", "мужской", range(14, 19)),      # a teenager: always a peer
    ("a girl my age", "40", "", "женский", range(37, 44)),
    ("мне бы собеседника лет 70", "35", "", None, range(70, 71)),
])
def test_their_words_decide_what_they_say(wants, their_age, band, gender, age):
    for seed in range(5):
        g, a = matchmaker.wished(wants, their_age=their_age, band=band, rng=random.Random(seed))
        assert int(a) in age and (gender is None or g == gender)


def test_with_nothing_said_his_age_stays_blank_until_he_says_it():
    for seed in range(5):
        assert matchmaker.blank(their_age="45", rng=random.Random(seed)).get("age") is None


def test_a_blank_is_told_to_be_ordinary_and_what_was_wished_is_true_at_once():
    block = persona.build_persona_block(_born())
    assert "вы только начинаете знакомиться" in block
    assert "станет правдой о тебе навсегда" in block
    assert "не там, где он" in block
    assert "любит футбол" in block                    # the wish, true from the first minute
    assert "Ты просто живёшь как настоящий человек" not in block


def test_he_opens_up_and_then_simply_lives(monkeypatch):
    base = _born()
    assert "понемногу открываешься" in persona.build_persona_block({**base, "layers": 1})
    assert "понемногу открываешься" in persona.build_persona_block({**base, "layers": 2})
    assert "Ты просто живёшь как настоящий человек" in persona.build_persona_block(
        {**base, "layers": 3})
    # …and a companion written whole at once (the intake path) simply lives.
    assert persona.written({"name": "Фёдор"}) == 3


def test_the_blank_has_an_english_twin(monkeypatch):
    monkeypatch.setattr(config, "LANGUAGE", "en")
    him = matchmaker.blank(wants="a guy", their_age="30", rng=random.Random(3))
    assert him["name"] in matchmaker._NAMES[("en", "м")]["middle"]
    block = persona.build_persona_block({**him, "given": "a guy"})
    assert "only starting to get to know each other" in block
    assert not any("а" <= ch.lower() <= "я" for ch in block)


# ── written in layers ───────────────────────────────────────────────────────

def test_after_the_first_real_talk_he_shows_what_he_is_like(models):
    _born()
    _talk()
    assert _after_and_settle() == 1
    him = persona.load_persona(U)
    assert him["personality"] == EVERYTHING["personality"] and him["home"]
    # …and nothing of the later layers yet: no subject, no wound.
    assert "expertise" not in him and "wound" not in him
    # What the person has been hearing stays as heard.
    assert (him["name"], him["gender"]) == (_born()["name"], "мужской")


def test_a_hello_is_not_a_talk_worth_writing_from(models):
    _born()
    _talk(words=5)
    assert _after_and_settle() == 0
    assert not models["seen"]


def test_what_he_is_for_waits_for_the_reader_to_be_sure(models):
    _born()
    models["plan"]["same"] = [False] * 9
    layers = []
    for _ in range(6):
        _talk()
        layers.append(_after_and_settle())
    # Layer 1 at once; layer 2 at the 5th reading, the reader never sure.
    assert layers[:5] == [1, 1, 1, 1, 2]
    assert persona.load_persona(U)["expertise"] == EVERYTHING["expertise"]


def test_two_readings_that_agree_bring_what_he_is_for_sooner(models):
    _born()
    _talk()
    assert _after_and_settle() == 1
    _talk()
    assert _after_and_settle() == 2


def test_his_depths_wait_until_they_know_each_other(models, monkeypatch):
    _born()
    for _ in range(2):
        _talk()
        _after_and_settle()
    assert persona.written(persona.load_persona(U)) == 2
    _talk()
    assert _after_and_settle() == 2, "depths before they know each other"
    _talk(words=meeting.KNOWN_AT[1])
    assert _after_and_settle() == 3
    him = persona.load_persona(U)
    assert him["wound"] == EVERYTHING["wound"] and him["flaws"]


def test_a_layer_only_fills_what_is_empty(models):
    """Whatever the model sends as a layer, it fills only empty places — what
    was written changes only through a checked revision (below)."""
    _born(home="Порту, у реки")           # he already said where he lives
    _talk()
    _after_and_settle()
    him = persona.load_persona(U)
    assert him["home"] == "Порту, у реки"
    assert him["name"] != EVERYTHING["name"] and him["gender"] == "мужской"
    write = _asked(models["seen"], "Ты пишешь человека, который уже существует")[0]
    assert "home —" not in write["system"]          # not even asked for
    assert "Порту, у реки" in write["user"]         # and shown as law


def _two_layers(models, *, revise: dict, check: dict, said_aloud: str = "") -> dict:
    """Layer 1, then layer 2 with the writer's revisions and the checker's
    answer; `said_aloud` is what he told the person about himself meanwhile."""
    _born()
    _talk()
    _after_and_settle()
    if said_aloud:
        memory.add_memory(U, "fact", said_aloud, owner="bob", importance=2)
    models["plan"].update(revise=revise, check=check)
    _talk()
    _after_and_settle()
    return persona.load_persona(U)


def test_what_is_only_written_may_be_put_right(models):
    him = _two_layers(models, revise={"roots": "из Николаева", "name": "Педро"},
                      check={"rejected": [], "fixes": {}})
    assert him["roots"] == "из Николаева"
    assert him["name"] == _born()["name"]               # who he is to them: never
    assert him["expertise"] == EVERYTHING["expertise"]  # and the layer itself is in


def test_what_he_said_aloud_is_not_revised(models):
    him = _two_layers(models, revise={"home": "Порту, у реки", "roots": "из Николаева"},
                      check={"rejected": ["home"], "fixes": {}},
                      said_aloud="живёт в Лиссабоне, над булочной")
    assert him["home"] == EVERYTHING["home"] and him["roots"] == "из Николаева"
    check = _asked(models["seen"], "Ты сверщик собеседника")[-1]
    assert "живёт в Лиссабоне, над булочной" in check["user"]
    assert "Порту, у реки" in check["user"]


def test_what_contradicts_what_he_said_is_corrected_and_the_fix_wins(models):
    him = _two_layers(models, revise={"roots": "из Николаева"},
                      check={"rejected": [], "fixes": {"roots": "из Херсона",
                                                       "expertise": "старые мотоциклы"}},
                      said_aloud="вырос в Херсоне")
    assert him["roots"] == "из Херсона" and him["expertise"] == "старые мотоциклы"


def test_a_check_that_could_not_run_lets_the_layer_in_and_nothing_else(models):
    him = _two_layers(models, revise={"roots": "из Николаева"}, check="не знаю")
    assert him["roots"] == EVERYTHING["roots"] and him["expertise"] == EVERYTHING["expertise"]


def test_he_changes_only_between_talks(models):
    _born()
    _talk()
    asyncio.run(shaping.after_talk(U))
    memory.log_turn(U, "user", "а, слушай, ещё одно")    # «пока» — and they carried on
    assert not shaping.settle(U)
    assert persona.written(persona.load_persona(U)) == 0
    with db.connect() as conn:
        conn.execute("UPDATE turns SET ts=? WHERE user_id=?", (time.time() - 3600, U))
    assert shaping.settle(U)
    assert persona.written(persona.load_persona(U)) == 1


def test_his_voice_stays_and_sounds_like_who_he_is_becoming(models):
    born = _born()
    _talk()
    _after_and_settle()
    him = persona.load_persona(U)
    assert him["voice"]["name"] == born["voice"]["name"]
    assert "сухим юмором" in him["voice"]["style"]


def test_held_for_the_owners_test_the_app_writes_nothing(models):
    _born(_held=True)
    for _ in range(3):
        _talk()
        _after_and_settle()
    assert not models["seen"]


def test_a_companion_written_whole_is_left_alone(models):
    persona.save_persona(U, {"name": "Фёдор", "personality": "был"})
    _talk()
    _after_and_settle()
    assert not models["seen"]


def test_what_wounds_him_survives_a_fresh_reading(models):
    """Somebody who starts over with a new friend has not become somebody else."""
    _born()
    reading.save(U, {"verdict": "старое", "hurt_by": ["когда торопят"], "learned": ["любит тишину"]})
    _talk()
    asyncio.run(shaping.after_talk(U))
    kept = reading.load(U)
    assert "когда торопят" in kept["hurt_by"] and "любит тишину" in kept["learned"]


def test_starting_over_starts_the_count_over(models):
    _born()
    _talk()
    asyncio.run(shaping.after_talk(U))
    erase.the_companion(U)
    assert shaping.STATE not in (reading.load(U) or {})


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


# ── and then he goes on being shaped ────────────────────────────────────────

def test_before_he_is_whole_no_week_no_deepening_no_re_reading_of_its_own(models):
    """Written in order: a flaw slipped in now would be his depths arriving in
    the second week."""
    from app import life

    _born(layers=1)
    reading.save(U, {"verdict": "а", "register": "б", "would_reach_them": "в"})
    for _ in range(45):
        memory.log_turn(U, "user", "ну да")
    asyncio.run(persona.deepen(U, now=True))
    asyncio.run(reading.keep_reading(U))
    assert not models["seen"]
    persona.save_persona(U, {**persona.load_persona(U), "layers": 0})
    asyncio.run(life.maybe_begin(U))
    assert not models["seen"]


def test_when_the_reader_learns_something_new_the_writer_adds_to_him(models, monkeypatch):
    persona.save_persona(U, {k: v for k, v in EVERYTHING.items()} | {"name": "Лукас",
                                                                        "gender": "мужской"})
    reading.save(U, {"verdict": "не с кем говорить всерьёз", "register": "коротко",
                     "would_reach_them": "спокойно"})
    for _ in range(reading.REREAD_MIN_TURNS):
        memory.log_turn(U, "user", "ну да")

    async def reread(user_id, existing, turns):
        return {**existing, "verdict": "некому показать то, что он рисует"}

    monkeypatch.setattr(reading, "reread", reread)
    asyncio.run(reading.keep_reading(U))
    assert "смотреть на звёзды с крыши" in persona.load_persona(U)["likes"]


def test_what_he_grows_is_checked_against_what_he_said(models):
    """Deepening adds, and then all of him is read again against what he has
    said aloud — a contradiction anywhere in him is put right."""
    persona.save_persona(U, {**EVERYTHING, "name": "Лукас", "gender": "мужской"})
    memory.add_memory(U, "fact", "вырос в Херсоне", owner="bob", importance=2)
    memory.log_turn(U, "user", "ну да")
    models["plan"]["check"] = {"rejected": [], "fixes": {"roots": "из Херсона"}}
    asyncio.run(persona.deepen(U, now=True))
    him = persona.load_persona(U)
    assert him["roots"] == "из Херсона" and "смотреть на звёзды с крыши" in him["likes"]
    check = _asked(models["seen"], "Ты сверщик собеседника")[-1]
    assert "смотреть на звёзды с крыши" in check["user"] and "вырос в Херсоне" in check["user"]


def test_a_reading_that_only_learned_a_line_does_not_reshape_him():
    before = {"verdict": "а", "learned": ["x"]}
    assert not reading.changed(before, {**before, "learned": ["x", "y"]})
    assert reading.changed(before, {**before, "verdict": "б"})


# ── a floor, not a ceiling — for him too ────────────────────────────────────

def test_his_humour_comes_with_what_he_is_like_and_his_dream_with_his_depths(models):
    _born()
    _talk()
    _after_and_settle()
    assert "humor" in matchmaker.LAYERS[0]["fields"] and "dream" in matchmaker.LAYERS[2]["fields"]
    write = _asked(models["seen"], "Ты пишешь человека, который уже существует")[0]
    assert "humor —" in write["system"] and "минимум, а не потолок" in write["system"]


def test_more_only_grows_from_layer_to_layer():
    """The one open field: each layer adds to it, nothing in it is replaced."""
    him = shaping.grown({"name": "Лукас", "layers": 0}, 1, {"more": ["свистит, когда думает"]})
    him = shaping.grown(him, 2, {"more": ["коллекционирует билеты"], "humor": "чужое"})
    assert him["more"] == ["свистит, когда думает", "коллекционирует билеты"]
    block = persona.build_persona_block(him)
    assert "Ещё о тебе: свистит, когда думает; коллекционирует билеты" in block


def test_we_complement_and_sometimes_the_best_complement_is_matching():
    """The owner, 2026-10-09: «Мы не мэтчим, мы дополняем. Но иногда самое
    лучшее дополнение это matching»."""
    for prompt in (matchmaker._WRITE_SYSTEM, matchmaker._layer_system(2, {})):
        assert "МЫ ДОПОЛНЯЕМ" in prompt and "иногда лучшее дополнение — совпадение" in prompt
