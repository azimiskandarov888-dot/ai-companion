"""Persona: config-driven, editable, and correctly assembled into the prompt."""

from __future__ import annotations

import json

from app import config, persona


def test_default_persona_when_no_file():
    p = persona.load_persona()
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
    p = persona.load_persona()
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
    block = persona.build_persona_block()
    assert "Гриша" in block
    assert "городок в горах" in block
    assert "Пётр" in block
    assert "«вы»" in block  # respectful address honored


def test_default_block_uses_ty_address():
    block = persona.build_persona_block()
    assert "«ты»" in block


def test_invalid_persona_file_falls_back(monkeypatch):
    config.PERSONA_PATH.write_text("{ not valid json", encoding="utf-8")
    p = persona.load_persona()
    assert p is persona.DEFAULT_PERSONA


def test_save_never_borrows_from_the_template():
    """The regression that gave every friend the same cat.

    save_persona used to merge DEFAULT_PERSONA underneath whatever the pen
    wrote, so each field the pen left out arrived pre-filled with the
    template's life — the sea, Мурзик, the café. Three different characters,
    one identical cat. A created character must contain ONLY what was created.
    """
    saved = persona.save_persona({"name": "Зоя", "age": "31 год", "home": "северный город"})
    assert saved["name"] == "Зоя"
    for field in ("likes", "habits", "cast", "backstory"):
        assert field not in saved

    # …and it stays clean through a reload.
    loaded = persona.load_persona()
    assert loaded["name"] == "Зоя"
    assert "cast" not in loaded

    # The block builder is happy with the gaps: no cat is mentioned anywhere.
    block = persona.build_persona_block()
    assert "Зоя" in block
    assert "Мурзик" not in block
