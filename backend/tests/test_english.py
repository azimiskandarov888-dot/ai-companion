"""A conversation in English (lang.py, COMPANION_LANGUAGE=en) — with no Russian
left in it anywhere a model reads or a person hears.

The owner, 2026-10-02: everything was built for Russian, «and now we suddenly
change it to English, so we really need to make sure we don't have any
mistakes, any misses». So the whole prompt is assembled the way a turn
assembles it, with every block that can appear switched on at once — and not
one Russian letter may be in it, except his markers (//КОНЕЦ//, //СМЕХ//…),
which are taken out by code before anything is said.
"""

from __future__ import annotations

import asyncio
import re
import time

import pytest

from app import (body, companion, config, db, emergency, feeling, first_sound, life, live, main,
                 meeting, memory, mood, persona, reading, safety, situations, vow, young)

UID = "english-person"
LILY = {
    "name": "Lily", "gender": "female", "age": "16",
    "one_liner": "a schoolgirl who moved to Dublin with her parents two years ago",
    "home": "Dublin, an old terraced house", "roots": "from Manchester",
    "personality": "calm, observant; a bit shy at first",
    "current_life": "mock exams coming up; helps at her aunt's café on Saturdays",
    "intention": "to finish her sketchbook", "address": "ты",
    "cast": [{"name": "Aunt Clare", "who": "her aunt", "between": "owes her a Saturday"}],
}
_MARKERS = re.compile(r"//[А-ЯЁ]+//")
_RUSSIAN = re.compile(r"[А-Яа-яЁё]")


def russian_in(text: str) -> list[str]:
    """Every run of Russian in `text`, his markers aside."""
    return re.findall(r"[А-Яа-яЁё][А-Яа-яЁё\s,.!?«»—-]*", _MARKERS.sub("", text))


@pytest.fixture
def english(monkeypatch):
    monkeypatch.setattr(config, "LANGUAGE", "en")


@pytest.fixture
def everything(english, monkeypatch):
    """A person and a companion with every block of the prompt switched on."""
    persona.save_persona(UID, LILY)
    young.remember(UID, "15")
    memory.log_turn(UID, "assistant", "Hey. How's your day going?")
    memory.log_turn(UID, "user", "Fine, I guess. Made some progress on my game.")
    memory.add_memory(UID, "fact", "Tim is making a pixel platformer", owner="elder")
    memory.add_memory(UID, "fact", "birthday: March 3", owner="elder")
    memory.add_memory(UID, "fact", "Lily helps at her aunt's café", owner="bob")
    memory.add_memory(UID, "lesson", "how to draw a pixel character", owner="bob")
    memory.add_memory(UID, "follow_up", "how the maths test went", owner="elder")
    memory.add_memory(UID, "story", "Tim burnt the rice the first time he made plov",
                      title="The plov")
    for _ in range(2):
        mood.observe(UID, "поднял_юмор")
        mood.observe(UID, "оживился_на_теме", subject="his game")
        mood.observe(UID, "хотел_больше_вопросов")
        mood.observe(UID, "понравилось_несогласие")
    mood.record(UID, {"energy": -1.6, "warmth": 1.2, "lightness": -1.5, "clarity": 1.0,
                      "engagement": 1.7, "word": "tired", "note": "tired after school",
                      "because": "he said he's wiped"})
    monkeypatch.setattr(feeling, "_stored_now", lambda uid: (-1.4, -1.5, "slept badly"))
    monkeypatch.setattr(life, "current", lambda uid: {
        "state": "Your brother is visiting and you argued about the TV.", "day": 2,
        "shows": "a bit distracted, laughs less"})
    monkeypatch.setattr(body, "state", lambda uid: {"hoarse": False, "throat": 0.9, "tired": 0.9})
    monkeypatch.setattr(safety, "carried", lambda uid: {
        "level": "worry", "kind": "body", "what": "his knee has hurt for three weeks"})
    monkeypatch.setattr(memory, "broke_off_last_time", lambda uid: True)
    monkeypatch.setattr(memory, "how_long_since_last_time",
                        lambda uid: "You haven't talked for 5 days.")
    monkeypatch.setattr(reading, "load", lambda uid: {
        "verdict": "lonely after the move", "register": "plainly, like a mate",
        "would_ring_false": "praise", "do_not_touch": "his dad",
        "closeness": "likes being missed", "what_lifts_him": "jokes",
        "hurt_by": "being lectured", "learned": ["he opens up about games"]})

    async def quiet(*_a, **_k):
        return None

    monkeypatch.setattr(safety, "look", quiet)


def _assemble(line: str, *, by_ear: bool = True) -> tuple[str, str]:
    async def run():
        stable, variable, _h, _v, _w = await main._assemble(UID, line, pending=True, marks=[],
                                                            by_ear=by_ear)
        return stable, variable

    return asyncio.run(run())


def test_the_whole_prompt_of_an_english_conversation_has_no_russian(everything):
    stable, variable = _assemble("let's play word chain? oh and what's the weather like today?")
    assert not russian_in(stable), russian_in(stable)[:5]
    assert not russian_in(variable), russian_in(variable)[:5]
    # …and it really is all there, in English.
    for part in ("You are a living voice companion", "WHO YOU ARE", "WHAT YOU SENSE IN THEM",
                 "WHAT HAS BEEN CONFIRMED", "HOW THE TWO OF YOU GET ON BEST", "A worrying sign",
                 "YOU HEAR THEM", "WHERE THE TWO OF YOU ARE", "HOW YOU ARE TODAY YOURSELF",
                 "WHAT'S GOING ON IN YOUR LIFE", "YOUR BODY RIGHT NOW", "TODAY is",
                 "HOW PEOPLE TALK OUT LOUD", "RIGHT NOW IT'S ABOUT A GAME",
                 "IF THEY'RE ASKING ABOUT THE NEWS", "YOU'RE TALKING TO A TEENAGER",
                 "LAST TIME THEY JUST VANISHED", "LANGUAGE: the two of you talk in English"):
        assert part in stable + variable, part


@pytest.mark.parametrize("line, part", [
    ("Guess what happened today?", "THEY HAVEN'T FINISHED"),
    ("Fine, nothing much.", "THEY ANSWERED IN A WORD OR TWO"),
])
def test_the_turns_own_rules_are_english_too(everything, line, part):
    _, variable = _assemble(line)
    assert part in variable and not russian_in(variable)


def test_a_first_meeting_is_english(english):
    persona.save_persona(UID, LILY)
    assert not russian_in(meeting.block(0, named=False, heard=meeting.NAME_BY))
    assert all(not russian_in(meeting.where(w, named=False)) for w in (0, 400, 3000, 9000))
    assert not russian_in(meeting.HELLO_EN)


def test_danger_is_english(english):
    for kind in ("body", "self"):
        verdict = {"level": "danger", "kind": kind, "what": "chest pain"}
        assert not russian_in(safety.block(verdict, UID))
        assert not russian_in(safety.spoken_alert(verdict, UID))
    assert " or " in emergency.numbers(UID) or emergency.numbers(UID) == emergency.UNIVERSAL


def test_what_he_says_without_a_model_is_english(english):
    assert not russian_in(vow.last_resort())
    assert all(not russian_in(f) for f in live._FILLERS_EN)
    assert all(not russian_in(t) for t in first_sound._texts("listening") + first_sound._texts("thinking"))
    from app import allowance
    assert not russian_in(allowance._line("asleep")) and not russian_in(allowance._line("spent"))


def test_his_never_said_words_are_caught_in_english():
    for said in ("I'm just an AI, so I can't really feel things.", "As an AI language model, I…",
                 "I don't have feelings.", "I'm a real person, I promise."):
        assert vow.broken(said), said
    for said in ("My brother's a programmer.", "I'm real tired today.", "The robot vacuum broke."):
        assert not vow.broken(said), said


def test_a_russian_conversation_is_untouched(monkeypatch):
    """The default stays exactly what it was."""
    monkeypatch.setattr(config, "LANGUAGE", "ru")
    stable, variable = companion.build_system_parts(by_ear=True)
    assert stable == companion.BEHAVIOR_RULES
    assert companion.REACTING in variable and companion.IN_ENGLISH not in variable
    assert situations.block("Нормально.") and "THEY" not in situations.block("Нормально.")
