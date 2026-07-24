"""Pytest fixtures shared by the whole test suite.

Placing this at the backend/ root puts `backend/` on sys.path (pytest prepend
mode), so `from app import ...` works, and gives every test an isolated,
throwaway database + data directory.
"""

from __future__ import annotations

import pytest

from app import config, db


@pytest.fixture(autouse=True)
def temp_data(tmp_path, monkeypatch):
    """Point config at a fresh temp DB + data dir for each test, then init it."""
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "PERSONA_PATH", tmp_path / "persona.json")
    db.init_db()
    yield
