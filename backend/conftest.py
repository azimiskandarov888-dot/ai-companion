"""Pytest fixtures shared by the whole test suite.

Placing this at the backend/ root puts `backend/` on sys.path (pytest prepend
mode), so `from app import ...` works, and gives every test an isolated,
throwaway database + data directory.
"""

from __future__ import annotations

import pytest

from app import allowance, config, db


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
    db.init_db()
    yield
