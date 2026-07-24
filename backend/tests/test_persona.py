"""Persona: config-driven, editable, and correctly assembled into the prompt."""

from __future__ import annotations

import json

from app import config, persona


def test_default_persona_when_no_file():
    p = persona.load_persona()
    assert p is persona.DEFAULT_PERSONA
    assert p["name"]


def test_persona_loaded_from_file_overrides_default():
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
    # Missing fields fall back to the default (merge).
    assert p["likes"] == persona.DEFAULT_PERSONA["likes"]


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
