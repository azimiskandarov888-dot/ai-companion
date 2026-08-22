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
        "flaws": ["перебивает", "занудствует про давление"],
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
           "speech_style": "коротко", "wound": "брат", "flaws": ["перебивает"]}

    grown = persona.merge_growth(him, {
        "name": "Николай",                 # ← all of this
        "age": "45 лет",                   # ← must be
        "home": "Пермь",                   # ← ignored
        "backstory": "был лётчиком",
        "personality": "весёлый",
        "speech_style": "длинно",
        "wound": "ещё одна рана",
        "flaws": ["упрям в мелочах"],      # ← only this gets in
    })

    assert grown["name"] == "Фёдор"
    assert grown["age"] == "70 лет"
    assert grown["home"] == "Ростов"
    assert grown["backstory"] == "работал в литейном"
    assert grown["personality"] == "ворчливый"
    assert grown["speech_style"] == "коротко"
    assert grown["wound"] == "брат"        # no accumulating wounds, ever
    assert grown["flaws"] == ["перебивает", "упрям в мелочах"]


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
