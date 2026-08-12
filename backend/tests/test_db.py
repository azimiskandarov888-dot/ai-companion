"""Migrations: an older database is upgraded without losing anybody.

These tests build the REAL prior schemas by hand and run init_db() over them.
That matters more than it looks: the only database that has ever held a real
person's life is one of these, and the upgrade path is the one piece of code
that gets exactly one chance to be right.
"""

from __future__ import annotations

import time

from app import db, identity, memory

ANON = identity.ANONYMOUS


def test_migration_adds_owner_column_to_old_db():
    # The pre-`owner` database: the exact prior schema (no owner, no user_id).
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

    db.init_db()

    with db.connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(memories)")}
    assert {"owner", "user_id"} <= cols

    # The existing row belongs to the elder, and to the person who has been
    # using this server — the anonymous user.
    assert "старое" in memory.facts_context(ANON, "elder")
    assert memory.add_memory(ANON, "fact", "новое", owner="bob") is not None


def _build_single_user_db() -> None:
    """The complete schema as it stood before multi-user, with data in it."""
    with db.connect() as conn:
        conn.execute("DROP TABLE memories")
        conn.execute("DROP TABLE turns")
        conn.execute("DROP TABLE usage")
        conn.execute("DROP TABLE diary")
        conn.execute(
            "CREATE TABLE turns ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, "
            "role TEXT NOT NULL, content TEXT NOT NULL, ts REAL NOT NULL)"
        )
        conn.execute("CREATE INDEX idx_turns_session ON turns(session_id, ts)")
        conn.execute(
            "CREATE TABLE memories ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "owner TEXT NOT NULL DEFAULT 'elder', kind TEXT NOT NULL, title TEXT, "
            "content TEXT NOT NULL, importance INTEGER DEFAULT 1, "
            "status TEXT DEFAULT 'open', embedding TEXT, meta TEXT, "
            "created_ts REAL NOT NULL, last_recalled_ts REAL, recall_count INTEGER DEFAULT 0)"
        )
        conn.execute(
            "CREATE TABLE usage (session_id TEXT NOT NULL, day TEXT NOT NULL, "
            "seconds REAL NOT NULL DEFAULT 0, turns INTEGER NOT NULL DEFAULT 0, "
            "PRIMARY KEY (session_id, day))"
        )
        conn.execute(
            "CREATE TABLE diary (id INTEGER PRIMARY KEY CHECK (id = 1), "
            "content TEXT NOT NULL, fingerprint TEXT NOT NULL, updated_ts REAL NOT NULL)"
        )
        # …and one real person's life inside it.
        conn.execute(
            "INSERT INTO turns(session_id, role, content, ts) "
            "VALUES ('default','user','здравствуй, дружочек',?)",
            (time.time(),),
        )
        conn.execute(
            "INSERT INTO memories(owner, kind, content, created_ts) "
            "VALUES ('elder','fact','внучка Настя',?)",
            (time.time(),),
        )
        conn.execute(
            "INSERT INTO usage(session_id, day, seconds, turns) "
            "VALUES ('default','2026-08-01', 640.0, 12)"
        )
        conn.execute(
            "INSERT INTO diary(id, content, fingerprint, updated_ts) "
            "VALUES (1,'Моя книга о друге.','abc',?)",
            (time.time(),),
        )


def test_the_single_user_database_becomes_user_default():
    """Nobody loses a friend to this upgrade.

    Everything from before multi-user belonged to one person, so it all lands
    under the anonymous id — which is exactly what that person's phone still
    sends until it gets the build with the token in it.
    """
    _build_single_user_db()
    db.init_db()

    with db.connect() as conn:
        assert {r["name"] for r in conn.execute("PRAGMA table_info(turns)")} >= {"user_id"}
        assert {r["name"] for r in conn.execute("PRAGMA table_info(usage)")} >= {"user_id"}

        # The conversation is still there, and still theirs.
        turns = conn.execute("SELECT user_id, content FROM turns").fetchall()
        assert [(t["user_id"], t["content"]) for t in turns] == [
            (ANON, "здравствуй, дружочек")
        ]

        # So is the day they'd already spent — an upgrade must not hand
        # anybody a free extra three hours, nor take one away.
        used = conn.execute(
            "SELECT seconds FROM usage WHERE user_id=? AND day='2026-08-01'", (ANON,)
        ).fetchone()
        assert used["seconds"] == 640.0

        # The diary was one row pinned by CHECK (id = 1) — a table that cannot
        # hold two books. It is rebuilt, and the existing book kept.
        book = conn.execute("SELECT content FROM diary WHERE user_id=?", (ANON,)).fetchone()
        assert book["content"] == "Моя книга о друге."

    assert "внучка Настя" in memory.facts_context(ANON, "elder")


def test_migrating_twice_changes_nothing():
    """init_db() runs on every server start, so it has to be a no-op the
    second time — and the thousandth."""
    _build_single_user_db()
    db.init_db()
    db.init_db()
    db.init_db()

    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) c FROM turns").fetchone()["c"] == 1
        assert conn.execute("SELECT COUNT(*) c FROM diary").fetchone()["c"] == 1
        assert conn.execute("SELECT COUNT(*) c FROM memories").fetchone()["c"] == 1
        # The old index, named after a column that no longer exists, is gone;
        # the user-first ones that replace it are there.
        names = {
            r["name"]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        }
    assert "idx_turns_session" not in names
    assert "idx_turns_user" in names
    assert "idx_memories_user_owner_kind" in names


def test_two_people_can_hold_a_diary_each():
    """The schema that made multi-user impossible: one diary row, pinned by
    CHECK (id = 1). The second person's book had nowhere to go."""
    _build_single_user_db()
    db.init_db()

    with db.connect() as conn:
        conn.execute(
            "INSERT INTO diary(user_id, content, fingerprint, updated_ts) "
            "VALUES ('abc123','Другая книга.','xyz',?)",
            (time.time(),),
        )
        books = conn.execute("SELECT user_id, content FROM diary ORDER BY user_id").fetchall()
    assert [(b["user_id"], b["content"]) for b in books] == [
        ("abc123", "Другая книга."),
        (ANON, "Моя книга о друге."),
    ]
