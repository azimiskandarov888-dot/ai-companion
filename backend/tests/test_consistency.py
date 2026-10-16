"""What he has said is law; what is only written may be put right (consistency.py).

The owner, 2026-10-16: «вдруг написанное раньше было не совсем точным, и нам
все-таки нужно его хоть как-то исправить» — and, of a second model to check
him, «просто поставить запрет». Pinned here: no model is asked; the writer's
revisions go in only as far as the code allows — never who he is to the
person, never another kind of value, never somebody else in his place; and
before every reply what he said wins over what is written of him.
"""

from __future__ import annotations

import datetime

import pytest

from app import companion, consistency, matchmaker

BEFORE = {
    "name": "Лукас", "gender": "мужской", "address": "ты", "age": 40,
    "home": "Лиссабон, квартира над булочной",
    "roots": "из Одессы, отец — моряк, мать — учительница музыки, переехали, когда ему было десять",
    "likes": ["дождь", "старые велосипеды"],
    "cast": [{"name": "Жозе", "who": "дядя", "between": "долг"}],
}


def test_what_is_only_written_is_put_right():
    proposed = {"roots": BEFORE["roots"].replace("моряк", "врач"),
                "home": "Лиссабон, квартира над пекарней", "likes": ["дождь", "джаз"],
                "cast": [{"name": "Жозе", "who": "брат", "between": "долг"}]}
    assert consistency.admit(BEFORE, proposed) == proposed


@pytest.mark.parametrize("proposed", [
    {"roots": "Родился в Канаде, всю жизнь работал лесорубом на севере, детей нет"},  # somebody else
    {"likes": "дождь"},                                  # a list made a line
    {"home": ["Порту"]},                                 # a line made a list
    {"cast": ["Жозе — брат"]},                           # people made strings
    {"wound": "отец уехал рано"},                        # nothing was written: that is writing
    {"name": "Педро"}, {"gender": "женский"}, {"address": "вы"},   # who he is to them,
    {"age": "22"},                                       # his age too: a peer stays a peer
    {"roots": "   "}, {"likes": []}, {"nonsense": "x"},
])
def test_a_revision_never_replaces_him(proposed):
    assert consistency.admit(BEFORE, proposed) == {}


def test_put_right_is_measured_by_what_stays():
    assert consistency.keeps_him(BEFORE["roots"], BEFORE["roots"].replace("Одессы", "Николаева"))
    assert consistency.keeps_him("работал на заводе всю жизнь, потом ушёл в такси водителем",
                                 "работала на заводе всю жизнь, потом ушла в такси водителем")
    assert not consistency.keeps_him(BEFORE["roots"], "из Канады, лесоруб")
    assert consistency.keeps_him("из Одессы", "из Николаева")       # too short to tell: a fact


def test_the_writer_checks_him_against_what_he_said_in_the_same_call():
    """No second model: the writer is told to put right what disagrees with
    what he said aloud — and what year it is, so that years add up."""
    system = matchmaker._layer_system(2, {})
    assert "Сверь уже написанное о нём с тем, что он сам сказал вслух" in system
    assert "Имя, пол, возраст и обращение не меняются никогда" in system
    shown = matchmaker.layer_context(now=BEFORE, his_words="- вырос в Херсоне", facts="",
                                     brief="", talks="")
    assert f"СЕГОДНЯ: {datetime.date.today().isoformat()}" in shown
    assert "- вырос в Херсоне" in shown


@pytest.mark.parametrize("en", [False, True])
def test_before_every_reply_what_he_said_wins_over_what_is_written(en):
    _stable, variable = companion.build_system_parts(
        persona_block="Вырос в Одессе.", bob_facts="- вырос в Херсоне",
        language="en" if en else "ru")
    told = ("where «WHO YOU ARE» above says otherwise, what you said is true" if en
            else "если «КТО ТЫ» выше говорит иначе — верно то, что ты сказал")
    assert told in variable and "- вырос в Херсоне" in variable
