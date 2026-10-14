"""How he listens (listening.py): read from the talk by a model, timed by the
live channel with a person's unevenness.

What is pinned: only what is allowed comes out of the model's answer — its
sounds from his palette, in the colour it chose; a wrong answer changes
nothing; the spans differ by the moment and are drawn anew; the model is
asked with the talk itself and what real listeners do.
"""

from __future__ import annotations

import asyncio
import json
import random

import pytest

from app import brain, config, first_sound, listening


def _answer(**kw) -> str:
    return json.dumps({"mood": "спор", "pace": "jump in", "listen": "rarely", "tone": "heated",
                       "go_on": ["Ну-ну.", "Да ну?"], "nudge": ["Ну и?"], **kw},
                      ensure_ascii=False)


def test_a_stance_is_what_the_model_chose_from_what_is_allowed():
    stance = listening.parse("Вот: " + _answer() + " — всё.")
    assert stance == listening.Stance(mood="спор", pace="jump in", listen="rarely", tone="heated",
                                      go_on=("Ну-ну.", "Да ну?"), nudge=("Ну и?",))


def test_sounds_not_in_his_palette_for_that_colour_are_left_out():
    # «Ого!» is a lively sound, not a heated one; «Ну, блин» is not his at all.
    stance = listening.parse(_answer(go_on=["Ого!", "Ну, блин", "Хм."], nudge=["Ого!"]))
    assert stance.go_on == ("Хм.",)
    assert stance.nudge and all(s in first_sound.LISTENER["heated"] for s in stance.nudge)


def test_none_chosen_and_his_plain_ones_of_that_colour_stand_in():
    stance = listening.parse(_answer(tone="soft", go_on=[], nudge=[]))
    assert stance.go_on and set(stance.go_on) <= set(first_sound.LISTENER["soft"])
    assert all(s.endswith("?") for s in stance.nudge)


@pytest.mark.parametrize("raw", ["", "не знаю", "{не json}", "[1, 2]",
                                 _answer(pace="very fast"), _answer(listen="always"),
                                 _answer(tone="angry")])
def test_an_answer_that_makes_no_sense_changes_nothing(raw):
    assert listening.parse(raw) is None


def test_before_anything_is_read_an_ordinary_talk_given_time_if_older():
    young, old = listening.opening(older=False), listening.opening(older=True)
    assert (young.pace, old.pace) == ("easy", "patient")
    assert young.go_on and young.nudge and young.tone == "calm"


def test_the_spans_differ_by_the_moment_and_are_never_the_same_twice():
    rng = random.Random(1)
    quarrel = listening.plan(listening.Stance(pace="jump in"), rng)
    easy = listening.plan(listening.Stance(pace="easy"), rng)
    hard = listening.plan(listening.Stance(pace="patient"), rng)
    # In a quarrel he does not nudge, he comes in; a hard talk lets a sentence rest.
    assert quarrel.nudge is None and quarrel.cut_in is not None and quarrel.rest is None
    assert easy.cut_in is None and easy.rest is None and easy.nudge < easy.give_up
    assert hard.rest is not None and hard.give_up > easy.give_up > quarrel.give_up
    gaps = {round(listening.plan(listening.Stance(), rng).give_up, 3) for _ in range(20)}
    assert len(gaps) > 15


def test_a_listener_who_says_little_says_it_seldom():
    rng = random.Random(2)
    often = [listening.apart(listening.Stance(listen="often"), rng) for _ in range(50)]
    rarely = [listening.apart(listening.Stance(listen="rarely"), rng) for _ in range(50)]
    assert max(often) < min(rarely)
    assert listening.GO_ON_CHANCE["silent"] == 0.0


def test_the_model_is_asked_with_the_talk_and_his_palette(monkeypatch):
    asked = {}

    async def generate_text(system, user, **kwargs):
        asked.update(system=system, user=user, **kwargs)
        return _answer()

    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(brain, "generate_text", generate_text)
    lines = [("user", "старое " * 3)] * 10 + [("assistant", "Ну и зачем ты так?"),
                                               ("user", "да потому что ты не прав!")]
    stance = asyncio.run(listening.read(lines, name="Андрей", older=True))
    assert stance.pace == "jump in"
    assert asked["model"] == config.LISTENER_MODEL and asked["effort"] == "none"
    assert "Андрей" in asked["system"] and "real listeners" in asked["system"]
    assert "АНДРЕЙ: Ну и зачем ты так?" in asked["user"]
    assert "THEM: да потому что ты не прав!" in asked["user"]
    assert asked["user"].count("THEM:") + asked["user"].count("АНДРЕЙ:") == listening.LINES
    assert "older" in asked["user"]
    assert "heated: " in asked["user"] and "Ну-ну." in asked["user"]


def test_without_a_key_or_with_a_failure_he_listens_as_he_was(monkeypatch):
    assert asyncio.run(listening.read([("user", "привет")])) is None    # no key in tests

    async def broken(*args, **kwargs):
        raise TimeoutError("slow")

    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(brain, "generate_text", broken)
    assert asyncio.run(listening.read([("user", "привет")])) is None


def test_his_sounds_come_in_colours_his_own_voice_told_how():
    from app import voices

    voice = voices.key({"name": sorted(voices.NAMES)[0], "style": "a man of 70, warm"})
    assert first_sound._toned(voice, "calm") == voice
    soft = first_sound._toned(voice, "soft")
    assert soft != voice and voices.parse(soft)[1].startswith("a man of 70: quietly")
    assert first_sound._toned(None, "soft") is None
    first_sound._made[(soft, "Ох…")] = [(16000, b"OH" * 10)]
    assert first_sound.listener(voice, "Ох…", "soft") == (16000, b"OH" * 10)
    assert first_sound.listener(voice, "Ох…", "heated") is None
