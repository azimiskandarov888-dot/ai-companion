"""Database migration: an older DB without `owner` is upgraded safely."""

from __future__ import annotations

from app import db, memory


def test_migration_adds_owner_column_to_old_db():
    # Simulate the real pre-`owner` database: the exact prior schema (every
    # column except `owner`).
    with db.connect() as conn:
        conn.execute("DROP TABLE memories")
        conn.execute(
            "CREATE TABLE memories ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, title TEXT, "
            "content TEXT NOT NULL, importance INTEGER DEFAULT 1, "
            "status TEXT DEFAULT 'open', embedding TEXT, meta TEXT, "
            "created_ts REAL NOT NULL, last_recalled_ts REAL, recall_count INTEGER DEFAULT 0)"
        )
        conn.execute(
            "INSERT INTO memories(kind, content, created_ts) VALUES ('fact','старое',0)"
        )

    # init_db() must upgrade it without error…
    db.init_db()

    with db.connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(memories)")}
    assert "owner" in cols

    # …and the existing row defaults to the elder's memory.
    assert "старое" in memory.facts_context("elder")
    # …and new writes work.
    assert memory.add_memory("fact", "новое", owner="bob") is not None
