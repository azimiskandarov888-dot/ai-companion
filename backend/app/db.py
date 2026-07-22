"""SQLite storage for the companion's memory.

Two tables:
  - turns:    the raw conversation log (nothing is ever lost).
  - memories: what the companion has *learned* — facts, stories, health notes,
              mood, and caring follow-ups — with an optional embedding for
              semantic recall.

SQLite keeps this zero-setup (no database to install) and is more than enough
for one person. It is wrapped behind this module + memory.py so Phase 2 can
swap in Postgres + pgvector without changing the rest of the app.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from collections.abc import Iterator

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
CREATE INDEX IF NOT EXISTS idx_memories_kind ON memories(kind, status);
"""


def init_db() -> None:
    with connect() as conn:
        conn.executescript(_SCHEMA)


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
