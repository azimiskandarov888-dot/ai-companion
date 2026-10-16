"""What he has said is law; what is only written may be put right (consistency.py).

The owner, 2026-10-16: «вдруг написанное раньше было не совсем точным, и нам
все-таки нужно его хоть как-то исправить». Pinned here: a revision passes only
when the check says it touches nothing he said aloud; a fix corrects what is
written and never writes what was not; neither may replace him with somebody
else, whatever a model sends; and a check that cannot run changes nothing.
"""

from __future__ import annotations

import asyncio
import datetime
import json

import pytest

from app import brain, config, consistency

BEFORE = {
    "name": "Лукас", "gender": "мужской", "address": "ты", "age": 40,
    "home": "Лиссабон, квартира над булочной",
    "roots": "из Одессы, отец — моряк, мать — учительница музыки, переехали, когда ему было десять",
    "likes": ["дождь", "старые велосипеды"],
    "cast": [{"name": "Жозе", "who": "дядя", "between": "долг"}],
    "more": ["свистит, когда думает"],
}


@pytest.fixture
def checker(monkeypatch):
    """The checker model, answering what the test puts in `said`."""
    asked: list[dict] = []
    said = {"answer": {"rejected": [], "fixes": {}}}

    async def answer(system, user, max_tokens=1500, model=None, timeout=None, effort=None):
        asked.append({"system": system, "user": user, "model": model, "effort": effort})
        got = said["answer"]
        if isinstance(got, Exception):
            raise got
        return got if isinstance(got, str) else json.dumps(got, ensure_ascii=False)

    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(config, "CHECKER_MODEL", "vendor/checker")
    monkeypatch.setattr(brain, "generate_text", answer)
    return {"asked": asked, "said": said}


def _check(**kw):
    kw.setdefault("before", BEFORE)
    return asyncio.run(consistency.check(**kw))


def test_what_he_said_aloud_is_law_and_what_is_only_written_may_be_put_right(checker):
    checker["said"]["answer"] = {"rejected": ["home"], "fixes": {}}
    got = _check(proposed={"home": "Порту, квартира у реки", "likes": ["дождь", "джаз"]},
                 spoken="- живёт в Лиссабоне")
    assert got == {"revise": {"likes": ["дождь", "джаз"]}, "fixes": {}}
    sent = checker["asked"][0]
    assert sent["model"] == config.CHECKER_MODEL and sent["effort"] == "low"
    assert "- живёт в Лиссабоне" in sent["user"] and "Порту, квартира у реки" in sent["user"]


def test_silence_about_a_revision_is_not_a_yes(checker):
    checker["said"]["answer"] = {"fixes": {"home": "Лиссабон, квартира над пекарней"}}
    got = _check(proposed={"likes": ["джаз"]})
    assert got == {"revise": {}, "fixes": {"home": "Лиссабон, квартира над пекарней"}}


def test_a_fix_puts_right_what_contradicts_and_wins(checker):
    """Born a sailor's son in Odessa — but he told the person his father was a
    doctor: the line is corrected, the rest of it kept."""
    fixed = BEFORE["roots"].replace("моряк", "врач")
    checker["said"]["answer"] = {"rejected": [], "fixes": {"roots": fixed}}
    got = _check(spoken="- отец был врачом")
    assert got["fixes"] == {"roots": fixed}
    assert f"СЕГОДНЯ: {datetime.date.today().isoformat()}" in checker["asked"][0]["user"]


@pytest.mark.parametrize("fixes", [
    {"roots": "Родился в Канаде, всю жизнь работал лесорубом на севере, детей нет"},  # somebody else
    {"likes": "дождь"},                                  # a list made a line
    {"cast": ["Жозе — дядя"]},                           # people made strings
    {"wound": "отец уехал рано"},                        # nothing was written: that is writing
    {"name": "Педро"}, {"gender": "женский"}, {"address": "вы"},   # who he is to them,
    {"age": "22"},                    # and his age: a live check «fixed» a teen's friend to 22
    {"roots": "   "}, {"likes": []},
])
def test_a_fix_never_replaces_him_nor_writes_what_was_not(checker, fixes):
    checker["said"]["answer"] = {"rejected": [], "fixes": fixes}
    assert _check()["fixes"] == {}


def test_a_revision_too_puts_right_and_never_replaces(checker):
    got = _check(proposed={
        "roots": "Родился в Канаде, всю жизнь работал лесорубом на севере, детей нет",
        "home": ["Порту"],                      # a line made a list
        "name": "Педро", "age": "22",           # never
        "humor": "сухой",                       # nothing written there: not a revision
    })
    assert got["revise"] == {}


def test_what_the_layer_adds_is_what_a_fix_must_keep(checker):
    """The new layer's own fields, and a list it adds to, are checked as they
    will be — a fix of them is held to that, not to the old alone."""
    layer = {"humor": "смеётся над собой, когда что-то не выходит, и никогда над человеком",
             "more": ["коллекционирует билеты"]}
    keeps = "смеётся над собой, когда что-то не выходит, и никогда над человеком напротив"
    checker["said"]["answer"] = {"rejected": [], "fixes": {
        "humor": keeps, "more": ["свистит, когда думает", "собирает марки"]}}
    got = _check(layer=layer)
    assert got["fixes"] == {"humor": keeps, "more": ["свистит, когда думает", "собирает марки"]}


@pytest.mark.parametrize("answer", ["", "не знаю", "[1, 2]", RuntimeError("timeout")])
def test_a_check_that_cannot_read_him_changes_nothing(checker, answer):
    checker["said"]["answer"] = answer
    assert _check(proposed={"likes": ["джаз"]}) == {"revise": {}, "fixes": {}}


def test_without_a_key_nothing_is_asked_and_nothing_changes(checker, monkeypatch):
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    assert _check(proposed={"likes": ["джаз"]}) == {"revise": {}, "fixes": {}}
    assert checker["asked"] == []


def test_put_right_is_measured_by_what_stays():
    assert consistency.keeps_him(BEFORE["roots"], BEFORE["roots"].replace("Одессы", "Николаева"))
    assert consistency.keeps_him("работал на заводе всю жизнь, потом ушёл в такси водителем",
                                 "работала на заводе всю жизнь, потом ушла в такси водителем")
    assert not consistency.keeps_him(BEFORE["roots"], "из Канады, лесоруб")
    assert consistency.keeps_him("из Одессы", "из Николаева")       # too short to tell: a fact


def test_the_checker_is_told_the_law_and_shown_no_answer_to_copy():
    assert "это закон: человек это слышал" in consistency._SYSTEM
    assert "Ничего не улучшай на свой вкус" in consistency._SYSTEM
    assert '{"rejected": [имена полей], "fixes": {имя поля: новое значение}}' in consistency._SYSTEM
    assert not {"name", "gender", "age", "address"} & consistency.REVISABLE
    assert "Имя, пол, возраст и обращение не меняются никогда" in consistency._SYSTEM
