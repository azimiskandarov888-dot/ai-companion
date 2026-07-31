"""SQLite storage for the companion's memory.

Tables:
  - turns:    the raw conversation log (nothing is ever lost).
  - memories: what the companion has *learned* — facts, stories, health notes,
              mood, and caring follow-ups — with an optional embedding for
              semantic recall. The `owner` column separates memory about the
              elder ('elder') from Bob's own life-details ('bob'), so Bob stays
              consistent about himself without polluting the elder's memory.
              This distilled memory is INTERNAL — users never see it.
  - diary:    the single living book the user *does* see — the companion's
              beautifully written diary about his friend, composed from the
              memories above (see diary.py) and cached here.

SQLite keeps this zero-setup (no database to install) and is more than enough
for one person. It is wrapped behind this module + memory.py so a later phase
can swap in Postgres + pgvector without changing the rest of the app.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS turns (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    role        TEXT NOT NULL,          -- 'user' | 'assistant'
    content     TEXT NOT NULL,
    ts          REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id, ts);

CREATE TABLE IF NOT EXISTS memories (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    owner             TEXT NOT NULL DEFAULT 'elder',  -- 'elder' | 'bob'
    kind              TEXT NOT NULL,     -- fact | story | health | mood | follow_up
    title             TEXT,
    content           TEXT NOT NULL,
    importance        INTEGER DEFAULT 1,
    status            TEXT DEFAULT 'open',  -- follow_up: open|done
    embedding         TEXT,              -- JSON list[float], or NULL
    meta              TEXT,              -- JSON, optional
    created_ts        REAL NOT NULL,
    last_recalled_ts  REAL,
    recall_count      INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS diary (
    id          INTEGER PRIMARY KEY CHECK (id = 1),  -- one living book
    content     TEXT NOT NULL,
    fingerprint TEXT NOT NULL,                       -- of the memory it was written from
    updated_ts  REAL NOT NULL
);
"""


def init_db() -> None:
    with connect() as conn:
        # 1) Create tables (fresh installs get the full schema, incl. `owner`).
        conn.executescript(_SCHEMA)
        # 2) Upgrade older databases that predate a column.
        _migrate(conn)
        # 3) Only now build indexes that reference migrated columns — otherwise
        #    an index ON `owner` would fail on a pre-`owner` database.
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_owner_kind "
            "ON memories(owner, kind, status)"
        )


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns introduced after a DB was first created (dev-safe)."""
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(memories)")}
    if "owner" not in cols:
        conn.execute(
            "ALTER TABLE memories ADD COLUMN owner TEXT NOT NULL DEFAULT 'elder'"
        )


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        yield conn
        conn.commit()
    finally:
        conn.close()
