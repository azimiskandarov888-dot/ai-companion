"""Pytest fixtures shared by the whole test suite.

Placing this at the backend/ root puts `backend/` on sys.path (pytest prepend
mode), so `from app import ...` works, and gives every test an isolated,
throwaway database + data directory.
"""

from __future__ import annotations

import pytest

from app import allowance, aloud, config, db


@pytest.fixture(autouse=True)
def temp_data(tmp_path, monkeypatch):
    """Point config at a fresh temp DB + data dir for each test, then init it."""
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "PERSONA_PATH", tmp_path / "persona.json")
    monkeypatch.setattr(config, "READING_PATH", tmp_path / "reading.json")
    # Dozing lives in module-level sets, not the database, so it survives a
    # fresh temp directory and leaks from one test into the next: six short
    # transcripts spread across six unrelated tests and he falls asleep in the
    # seventh, which then fails for a reason that has nothing to do with it.
    allowance._asleep.clear()
    allowance._stray.clear()
    # NO TEST REACHES A REAL SERVICE. config reads the developer's own .env,
    # and a key sitting there would otherwise turn an unpatched test into a
    # paid call — the voice, since «fish» with an OpenRouter key speaks through
    # OpenRouter (config.voice_provider). A test that needs a key sets a fake one.
    for key in ("OPENROUTER_API_KEY", "DEEPGRAM_API_KEY", "FISH_API_KEY", "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY", "ELEVENLABS_API_KEY", "YANDEX_API_KEY"):
        monkeypatch.setattr(config, key, None)
    # How he says things aloud is chosen by chance (aloud.py): a test that
    # compares what was said word for word would fail now and then for no
    # reason of its own. Off by default; tests/test_aloud.py turns it on.
    monkeypatch.setattr(aloud, "CHANCE", 0.0)
    db.init_db()
    yield
