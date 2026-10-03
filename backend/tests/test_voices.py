"""Every companion his own voice, for good (voices.py).

The owner, 2026-10-03: «we are not having 2 ai companions. we need hundred of
them voices, and atleast 10 out of them must be russian» — and of Gemini's
thirty, heard in Russian, blind: «all of them are briliant. but 23rd is more
musculine voice rather then femenine».
"""

from __future__ import annotations

from app import persona, tts, voices

UID = "voices-person"
GENDERS = {name: gender for name, gender, _ in voices.CATALOG}
TRAITS = {name: trait for name, _, trait in voices.CATALOG}


def test_the_pool_is_google_s_voices_but_the_one_the_owner_heard_as_a_man():
    assert len(voices.CATALOG) == 29
    assert "Pulcherrima" in voices.EXCLUDED and "Pulcherrima" not in GENDERS
    assert sum(g == "male" for g in GENDERS.values()) == 16
    assert sum(g == "female" for g in GENDERS.values()) == 13
    # «at least 10 must be russian»: every one of them was heard in Russian.
    assert len(voices.CATALOG) >= 10


def test_a_woman_gets_a_woman_s_voice_and_a_man_a_man_s():
    for gender, expected in (("женский", "female"), ("female", "female"), ("мужской", "male"), ("", "male")):
        chosen = voices.choose({"name": "Саша", "gender": gender, "age": "30"})
        assert GENDERS[chosen["name"]] == expected


def test_the_same_him_always_gets_the_same_voice_and_different_people_differ():
    who = {"name": "Фёдор", "gender": "мужской", "age": "68", "home": "Калининград"}
    assert voices.choose(who) == voices.choose(dict(who))
    many = {voices.choose({"name": f"Имя{i}", "gender": "мужской", "age": "40", "home": "Город"})["name"]
            for i in range(40)}
    assert len(many) > 5                                   # not everybody the same voice


def test_the_voice_fits_who_he_is():
    calm_old = voices.choose({"name": "Фёдор", "gender": "мужской", "age": "71",
                              "personality": "спокойный, неторопливый, добрый"})
    assert TRAITS[calm_old["name"]] in voices._OLD
    lively_girl = voices.choose({"name": "Лиза", "gender": "женский", "age": "16",
                                 "personality": "весёлая, живая, болтушка"})
    assert TRAITS[lively_girl["name"]] in voices._YOUNG


def test_whom_the_voice_plays_is_his_age_and_his_manner_said_plainly():
    style = voices.style_for({"gender": "мужской", "age": "68", "personality": "спокойный, основательный"})
    assert style.startswith("a man of 68 (спокойный, основательный)") and voices.MANNER in style
    assert voices.style_for({"gender": "женский", "age": "16"}).startswith("a 16-year-old girl")
    assert voices.style_for({}).startswith("a man,")
    long = voices.style_for({"personality": "очень " * 60})
    assert len(long) < len(voices.MANNER) + 120             # a line, not his whole portrait


def test_his_voice_is_given_once_and_kept_as_his_portrait_grows():
    persona.save_persona(UID, {"name": "Лиза", "gender": "женский", "age": "16",
                               "personality": "спокойная, наблюдательная"})
    first = voices.ensure(UID)["voice"]
    assert persona.load_persona(UID)["voice"] == first
    grown = {**persona.load_persona(UID), "personality": "весёлая, живая, громкая, задорная"}
    persona.save_persona(UID, grown)
    assert voices.ensure(UID)["voice"] == first             # the same friend
    assert voices.parse(tts.voice_for(persona.load_persona(UID)))[0] == first["name"]


def test_the_template_is_nobody_s_and_gets_no_file():
    assert not persona.has_persona(UID)
    who = voices.ensure(UID)
    assert not persona.has_persona(UID)
    assert voices.of(who)["name"] in GENDERS


def test_a_voice_key_says_both_halves_and_nothing_else_parses():
    voice = {"name": "Callirrhoe", "style": "a 16-year-old girl, " + voices.MANNER}
    assert voices.parse(voices.key(voice)) == ("Callirrhoe", voice["style"])
    for other in (None, "", "c962ed46edfd419abc530d1e33a7435f", "gemini:Nobody|x", "alena"):
        assert voices.parse(other) is None


def test_a_kept_voice_that_is_no_longer_in_the_pool_is_replaced():
    who = {"name": "Лиза", "gender": "женский", "voice": {"name": "Pulcherrima", "style": "x"}}
    assert voices.of(who)["name"] != "Pulcherrima"
