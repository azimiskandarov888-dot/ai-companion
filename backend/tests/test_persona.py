"""Persona: config-driven, editable, and correctly assembled into the prompt."""

from __future__ import annotations

import json

import asyncio

from app import config, identity, persona

#: These tests write straight to config.PERSONA_PATH, which is the anonymous
#: user's file — so that is who they are about.
U = identity.ANONYMOUS


def test_default_persona_when_no_file():
    p = persona.load_persona(U)
    assert p is persona.DEFAULT_PERSONA
    assert p["name"]


def test_persona_loaded_from_file_is_taken_as_saved():
    config.PERSONA_PATH.write_text(
        json.dumps(
            {
                "name": "Гриша",
                "home": "маленький городок в горах",
                "address": "вы",
                "cast": [{"name": "Пётр", "who": "сосед и друг"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    p = persona.load_persona(U)
    assert p["name"] == "Гриша"
    # A saved character is NEVER topped up from the default template. A field
    # he doesn't have simply isn't there — the block builder skips it. This is
    # the fix for every friend arriving part-Мурзик.
    assert "likes" not in p


def test_build_persona_block_contains_key_fields():
    config.PERSONA_PATH.write_text(
        json.dumps(
            {
                "name": "Гриша",
                "home": "городок в горах",
                "address": "вы",
                "cast": [{"name": "Пётр", "who": "сосед"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    block = persona.build_persona_block(persona.load_persona(U))
    assert "Гриша" in block
    assert "городок в горах" in block
    assert "Пётр" in block
    assert "«вы»" in block  # respectful address honored


def test_default_block_uses_ty_address():
    block = persona.build_persona_block(persona.load_persona(U))
    assert "«ты»" in block


def test_invalid_persona_file_falls_back(monkeypatch):
    config.PERSONA_PATH.write_text("{ not valid json", encoding="utf-8")
    p = persona.load_persona(U)
    assert p is persona.DEFAULT_PERSONA


def test_save_never_borrows_from_the_template():
    """The regression that gave every friend the same cat.

    save_persona used to merge DEFAULT_PERSONA underneath whatever the pen
    wrote, so each field the pen left out arrived pre-filled with the
    template's life — the sea, Мурзик, the café. Three different characters,
    one identical cat. A created character must contain ONLY what was created.
    """
    saved = persona.save_persona(U, {"name": "Зоя", "age": "31 год", "home": "северный город"})
    assert saved["name"] == "Зоя"
    for field in ("likes", "habits", "cast", "backstory"):
        assert field not in saved

    # …and it stays clean through a reload.
    loaded = persona.load_persona(U)
    assert loaded["name"] == "Зоя"
    assert "cast" not in loaded

    # The block builder is happy with the gaps: no cat is mentioned anywhere.
    block = persona.build_persona_block(persona.load_persona(U))
    assert "Зоя" in block
    assert "Мурзик" not in block


# --------------------------------------------------------------------------- #
# What is wrong with him — and why it is not decoration
# --------------------------------------------------------------------------- #

def test_his_faults_reach_the_conversation():
    """The gap this closes: the persona described his character, his history,
    what's on his mind, what he's expert in, what he likes and dislikes — and
    had NOWHERE to say what is wrong with him. The behaviour rules said «be
    imperfect» to a persona holding no imperfections, which produces generic
    fallibility, i.e. none."""
    block = persona.build_persona_block({
        "name": "Фёдор",
        "flaws": ["перебивает", "занудствует про давление"], "intention": "перебрать лодку до заморозков",
        "contradiction": "ругает город и ездит туда каждый год",
        "wound": "не помирился с братом",
    })
    assert "перебивает" in block and "занудствует про давление" in block
    assert "ругает город и ездит туда каждый год" in block
    assert "не помирился с братом" in block


def test_the_wound_is_never_a_request():
    """A lonely eighty-year-old must never end up managing his feelings. The
    wound exists so he understands somebody else's pain without needing it
    explained — not so it can be brought to them."""
    block = persona.build_persona_block({"wound": "что-то"})
    assert "помощи не просишь" in block


def test_even_the_fallback_companion_has_faults():
    assert persona.DEFAULT_PERSONA["flaws"]
    assert persona.DEFAULT_PERSONA["contradiction"]
    block = persona.build_persona_block(persona.DEFAULT_PERSONA)
    assert "Твои недостатки" in block


# --------------------------------------------------------------------------- #
# He goes on becoming himself — but his facts never move
# --------------------------------------------------------------------------- #
#
# The split is the whole safety model. WHO HE IS is fixed; WHAT YOU HAVE COME
# TO KNOW OF HIM grows. A friend whose biography drifts is not deepening, he
# is a different man — and self-contradiction is the most fiction-breaking
# thing this app can do.

def test_identity_cannot_be_rewritten_by_a_deepening():
    """The one that matters. A model asked politely for additions will
    sometimes helpfully improve the backstory, and accepting that once is how
    somebody's friend quietly becomes another person."""
    him = {"name": "Фёдор", "age": "70 лет", "home": "Ростов",
           "backstory": "работал в литейном", "personality": "ворчливый",
           "speech_style": "коротко", "wound": "брат", "flaws": ["перебивает"], "intention": "перебрать лодку до заморозков"}

    grown = persona.merge_growth(him, {
        "name": "Николай",                 # ← all of this
        "age": "45 лет",                   # ← must be
        "home": "Пермь",                   # ← ignored
        "backstory": "был лётчиком",
        "personality": "весёлый",
        "speech_style": "длинно",
        "wound": "ещё одна рана",
        "flaws": ["упрям в мелочах"],      # ← only this and the intention get in
        "intention": "дописать письмо брату",
    })

    assert grown["name"] == "Фёдор"
    assert grown["age"] == "70 лет"
    assert grown["home"] == "Ростов"
    assert grown["backstory"] == "работал в литейном"
    assert grown["personality"] == "ворчливый"
    assert grown["speech_style"] == "коротко"
    assert grown["wound"] == "брат"        # no accumulating wounds, ever
    assert grown["flaws"] == ["перебивает", "упрям в мелочах"]
    # …and the one thing he is in the middle of is REPLACED rather than piled
    # up. An intention that can only accumulate is not an intention: a man who
    # has been about to mend the same boat for a year is more dead than one who
    # never meant to.
    assert grown["intention"] == "дописать письмо брату"


def test_what_a_friendship_reveals_accumulates():
    him = {"name": "Фёдор", "cast": [{"name": "Витя", "who": "сосед"}],
           "likes": ["уха"], "opinions": [], "habits": []}
    grown = persona.merge_growth(him, {
        "cast": [{"name": "Люся", "who": "сестра"}],
        "likes": ["старые песни"],
        "opinions": ["в городе жить нельзя"],
        "habits": ["курит на балконе"],
    })
    assert [c["name"] for c in grown["cast"]] == ["Витя", "Люся"]
    assert grown["likes"] == ["уха", "старые песни"]
    assert grown["opinions"] == ["в городе жить нельзя"]
    assert grown["habits"] == ["курит на балконе"]


def test_the_same_detail_twice_is_not_two_details():
    him = {"likes": ["уха"], "cast": [{"name": "Витя", "who": "сосед"}]}
    grown = persona.merge_growth(him, {
        "likes": ["Уха", "  уха  "],
        "cast": [{"name": "Витя", "who": "сосед"}],
    })
    assert grown["likes"] == ["уха"]
    assert len(grown["cast"]) == 1


def test_his_week_is_replaced_not_piled_up():
    """current_life is what is happening NOW, and last month's news is not."""
    him = {"current_life": "чинил крышу"}
    grown = persona.merge_growth(him, {"current_life": "приехала сестра"})
    assert grown["current_life"] == "приехала сестра"


def test_nothing_offered_changes_nothing():
    him = {"name": "Фёдор", "likes": ["уха"]}
    assert persona.merge_growth(him, {}) == him
    assert persona.merge_growth(him, {"likes": []}) == him


def test_the_deepening_waits_for_a_real_friendship(monkeypatch):
    called = False

    async def fake_think(*a, **kw):
        nonlocal called
        called = True
        return "{}"

    monkeypatch.setattr(persona.config, "WRITER_MODEL", "x", raising=False)
    asyncio.run(persona.deepen("nobody-has-a-companion"))
    assert not called


def test_nothing_that_makes_him_himself_can_ever_be_grown():
    """Walked as a whole set rather than spot-checked. If somebody later adds
    a field to GROWABLE without thinking, this is what catches it."""
    for field in ("name", "age", "gender", "home", "roots", "backstory",
                  "personality", "speech_style", "values", "wound",
                  "contradiction", "one_liner", "address", "expertise",
                  "inner_world"):
        assert field not in persona.GROWABLE, field
        assert field != persona.LIVE, field


def test_what_is_wrong_with_him_reaches_the_conversation_and_the_write():
    from app import matchmaker
    for field in ("flaws", "contradiction", "wound"):
        value = [f"ЗНАЧ-{field}"] if field == "flaws" else f"ЗНАЧ-{field}"
        assert f"ЗНАЧ-{field}" in persona.build_persona_block({field: value}), field
        assert field in matchmaker._WRITE_SYSTEM, field
        assert persona.DEFAULT_PERSONA.get(field), field


# ── the one field that points forward ──────────────────────────────────────

def test_he_is_in_the_middle_of_something():
    """The axis this character had nothing for. He has a past (backstory), a
    present (current_life), a wound and a contradiction — and until now not one
    field that pointed FORWARD. Things happened to him: a cold, a visiting
    brother. He never WANTED anything.

    A man to whom things happen is a setting. A man trying to get the boat
    mended before the frost is a person, and it is also the only thing in him
    a friend can ask after next week — «ну что, перебрал лодку?» is a question
    you ask somebody you know."""
    block = persona.build_persona_block({
        "name": "Пётр", "intention": "перебрать лодку до заморозков",
    })
    assert "перебрать лодку до заморозков" in block
    # It is background, not an agenda item: a friend who opens every call with
    # a progress report on his own boat is giving a report.
    assert "не докладывай об этом сам" in block


def test_a_companion_without_one_is_not_finished():
    """Required of the write, like flaws — and for the same kind of reason.
    A friend made only of virtues is the failure the schema exists to stop;
    a friend who wants nothing is the other half of it."""
    from app import matchmaker

    assert "intention" in matchmaker._REQUIRED
    assert "intention" in matchmaker._WRITE_SYSTEM


def test_the_deepening_can_finish_it_and_start_another():
    """It has to be able to END. An intention that only accumulates is not one:
    a man who has been about to mend the same boat for a year is more dead than
    one who never meant to."""
    assert "ЧТО ОН ЗАТЕЯЛ" in persona._DEEPEN_SYSTEM
    assert "доделал? бросил? застрял?" in persona._DEEPEN_SYSTEM
    # …and replacing is what merge_growth does with it, unlike the lists.
    assert persona.INTENTION not in persona.GROWABLE


def test_he_does_not_dissolve_into_a_list():
    """These lists only ever grew. A friendship of a year took him from under
    two thousand characters to over twenty — all of it riding in the cached
    half of every turn, and the cost is the smaller half of the problem. A man
    with sixty quirks has no character; he has an inventory, and nothing in an
    inventory is memorable because everything in it weighs the same."""
    him = {"name": "Пётр", "flaws": ["перебивает", "упрям", "занудствует про давление"]}
    for i in range(40):
        him = persona.merge_growth(him, {"flaws": [f"черта {i}"]})

    assert len(him["flaws"]) == persona._MOST["flaws"]
    # The character as WRITTEN survives — those are who he is. What a
    # friendship revealed is what ages out, newest kept.
    assert him["flaws"][:3] == ["перебивает", "упрям", "занудствует про давление"]
    assert "черта 39" in him["flaws"]
    assert "черта 0" not in him["flaws"]


def test_a_short_list_is_left_alone():
    """The ceiling must not become a target: most people are a handful of
    things, and nothing here should be padding him up to five."""
    him = {"name": "Пётр", "flaws": ["перебивает"]}
    grown = persona.merge_growth(him, {"flaws": ["упрям в мелочах"]})
    assert grown["flaws"] == ["перебивает", "упрям в мелочах"]
