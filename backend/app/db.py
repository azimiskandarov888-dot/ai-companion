"""SQLite storage for the companion's memory.

Every table is keyed by `user_id` (see identity.py) — the sha256 of the
caller's bearer token. One server, any number of people, and no query in this
codebase may touch a row without saying whose it is.

Tables:
  - turns:    the raw conversation log (nothing is ever lost).
  - memories: what the companion has *learned* — facts, stories, health notes,
              mood, and caring follow-ups — with an optional embedding for
              semantic recall. The `owner` column separates memory about the
              user ('elder') from the companion's own life-details ('bob'), so
              he stays consistent about himself without polluting the user's
              memory. This distilled memory is INTERNAL — users never see it.
  - usage:    seconds of conversation per person per day — the daily allowance
              is counted here, on the server, because a limit that lives in the
              phone app is defeated by a modified app and, more likely, by a bug
              in the app itself.
  - diary:    the living book the user *does* see — the companion's beautifully
              written diary about his friend, composed from the memories above
              (see diary.py) and cached here. One book per person.

SQLite keeps this zero-setup (no database to install). In WAL mode it handles
many readers alongside one writer comfortably, which is the shape of this
workload — a few short writes per spoken turn. It is wrapped behind this module
+ memory.py so a later phase can swap in Postgres + pgvector without changing
the rest of the app.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from . import config

# Indexes live in _INDEXES, not here, because they are built only AFTER
# _migrate() has brought an older database up to this shape — an index on a
# column that doesn't exist yet fails, and that failure would take the whole
# server down at startup.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS turns (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL,          -- whose conversation this is
    role        TEXT NOT NULL,          -- 'user' | 'assistant'
    content     TEXT NOT NULL,
    ts          REAL NOT NULL,
    -- 1 on the line he ended with a goodbye. The marker itself never survives
    -- as far as this table — it is stripped before anything is spoken or
    -- stored — so THIS is the only record that a conversation was closed
    -- properly rather than abandoned. memory.broke_off_last_time() reads it.
    farewell    INTEGER NOT NULL DEFAULT 0,
    -- When the learner read this turn; NULL means it has not. The extractor
    -- used to run on every single exchange, which was the most expensive thing
    -- in a conversation by a wide margin and gave the worst extraction, since
    -- it saw one exchange at a time. It reads in batches now, and this is how
    -- a batch knows where it starts — see learn.unread().
    read_ts     REAL
);

CREATE TABLE IF NOT EXISTS memories (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           TEXT NOT NULL DEFAULT 'default', -- whose memory this is
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
    recall_count      INTEGER DEFAULT 0,
    -- WHEN THIS STOPPED BEING TRUE OF HIS LIFE TODAY. NULL means it still is,
    -- which is almost always. Nothing is ever deleted: «жена Валя» does not
    -- become false when Valya dies, it becomes PAST — and the diary, which is
    -- meant to outlive the subscription, still has to be able to write about
    -- her. What must stop is the present tense reaching the companion, so
    -- every read path that tells him what IS filters on this being NULL.
    superseded_ts     REAL,
    superseded_why    TEXT               -- his own words that ended it
);

CREATE TABLE IF NOT EXISTS usage (
    user_id     TEXT NOT NULL,
    day         TEXT NOT NULL,          -- 'YYYY-MM-DD', local time
    seconds     REAL NOT NULL DEFAULT 0,
    turns       INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, day)
);

CREATE TABLE IF NOT EXISTS diary (
    user_id     TEXT PRIMARY KEY,                    -- one living book per person
    content     TEXT NOT NULL,
    fingerprint TEXT NOT NULL,                       -- of the memory it was written from
    updated_ts  REAL NOT NULL
);

-- One numeric read of how he seemed, per exchange. A word ("устал") cannot be
-- compared with the word before it, so a word can never show a CHANGE — and the
-- change is the whole point. Five small scales can. See mood.py.
CREATE TABLE IF NOT EXISTS mood_readings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL,
    ts          REAL NOT NULL,
    energy      REAL,      -- -2..+2, higher is better on every one of these,
    warmth      REAL,      --         so they can be averaged without thinking
    lightness   REAL,      --         about which way each one points
    clarity     REAL,
    engagement  REAL,
    word        TEXT,      -- the one-word mood, kept for the diary
    note        TEXT,      -- one human sentence about how he seemed
    because     TEXT       -- his own words that showed it
);

-- Every time the danger watcher saw something. Written for BOTH levels and
-- for every user, because the only way to know whether it is calibrated is to
-- read what it fired on and what it let past — and a watcher nobody can audit
-- is a watcher nobody should trust. `said` holds the person's own words: the
-- turns table has them too, but a false alarm has to be readable without
-- reconstructing the conversation around it.
CREATE TABLE IF NOT EXISTS alerts (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id  TEXT NOT NULL,
    ts       REAL NOT NULL,
    level    TEXT NOT NULL,          -- worry | danger  ('none' is not stored)
    kind     TEXT,                   -- body | self — what is threatening him
    what     TEXT,                   -- what the watcher thought it saw
    said     TEXT,                   -- what the person actually said
    told_ts  REAL                    -- when it reached him; NULL = it has not
);

-- Where he lives, learned from the conversation rather than asked for. It
-- decides which emergency number he is told to dial, which is the whole reason
-- it is stored at all — so only a country this app recognises is ever written
-- here (see emergency.py), and one row per person, overwritten if he moves.
CREATE TABLE IF NOT EXISTS places (
    user_id  TEXT PRIMARY KEY,
    country  TEXT NOT NULL,
    ts       REAL NOT NULL
);

-- WHETHER THE PERSON IS A GROWN-UP. One word per person, and it is the ONLY
-- thing kept about somebody who is not: see young.py. It has to be kept, or
-- the app forgets it is talking to a child between one sentence and the next
-- and the careful behaviour lasts exactly one reply.
--
-- A row here means «not an adult». Adults have no row, so absence and presence
-- say two different things and neither of them is a guess.
CREATE TABLE IF NOT EXISTS ages (
    user_id  TEXT PRIMARY KEY,
    band     TEXT NOT NULL,          -- child (<13) | teen (13-17)
    keeps    INTEGER,                -- a teenager's own answer: NULL not asked
    ts       REAL NOT NULL
);

-- WHAT IS HAPPENING TO HIM THIS WEEK. One row per friendship, holding at most
-- one thing at a time — a man with three simultaneous dramas is a soap opera.
-- `arc` is the whole course, day by day, written once by the model that knows
-- what a cold is; the code only ever looks up which day today is. `ended_ts` is
-- when the last one finished, and is what keeps the quiet gap between them.
CREATE TABLE IF NOT EXISTS life (
    user_id   TEXT PRIMARY KEY,
    what      TEXT NOT NULL DEFAULT '',  -- «простуда», or '' when nothing is on
    arc       TEXT NOT NULL DEFAULT '[]',-- JSON: [{"state": …, "shows": …}, …]
    started   REAL,
    ended_ts  REAL
);

-- HIS THROAT. One row per friendship, decayed when read like the mood above,
-- so nothing has to run between conversations and somebody who comes back next
-- morning finds a friend who has rested. `hoarse_ts` is when he last coughed —
-- the consequence half, which is what keeps a cough from being a sound effect.
CREATE TABLE IF NOT EXISTS body (
    user_id   TEXT PRIMARY KEY,
    throat    REAL NOT NULL DEFAULT 0,   -- 0..1, dryness from talking
    tired     REAL NOT NULL DEFAULT 0,   -- 0..1, from a conversation gone long
    hoarse_ts REAL,                      -- when he last coughed, or NULL
    ts        REAL NOT NULL              -- when this last MOVED
);

-- HIS OWN weather, one row per friendship. Not a log: this is a state, and the
-- only question ever asked of it is "how is he right now". It is stored at the
-- moment it changed and DECAYED WHEN READ (see feeling.py), so sitting still
-- costs nothing and a mood nobody asked about still fades on its own — which is
-- what moods do. `note` is his own reason in his own words, kept short because
-- it is his to mention once, not to dwell on.
CREATE TABLE IF NOT EXISTS companion_feeling (
    user_id  TEXT PRIMARY KEY,
    valence  REAL NOT NULL DEFAULT 0,   -- -2..+2, how good he feels
    arousal  REAL NOT NULL DEFAULT 0,   -- -2..+2, how awake and lively he feels
    note     TEXT,
    ts       REAL NOT NULL              -- when it last MOVED, not when last read
);

-- The "seen once, watching" register. Several rules in companion.py say some
-- version of «по одному разу не решай» — decide only when it happens twice.
-- That is unenforceable with nowhere to hold the first time, so this is that
-- place. `times` is what makes something true; a single occurrence is kept and
-- deliberately not acted on.
CREATE TABLE IF NOT EXISTS observations (
    user_id     TEXT NOT NULL,
    tag         TEXT NOT NULL,               -- from mood.TAGS, never free text
    subject     TEXT NOT NULL DEFAULT '',    -- the topic it was about, if any
    times       INTEGER NOT NULL DEFAULT 0,
    first_ts    REAL NOT NULL,
    last_ts     REAL NOT NULL,
    evidence    TEXT,
    PRIMARY KEY (user_id, tag, subject)
);
"""

# Every index leads with user_id. Nothing is ever read across users, so a
# user-first index turns each lookup into a scan of that one person's rows —
# which is what keeps a server with many people on it as fast as the server
# that had one.
_INDEXES = (
    # recent_turns: WHERE user_id=? ORDER BY id DESC LIMIT ?
    "CREATE INDEX IF NOT EXISTS idx_turns_user ON turns(user_id, id)",
    # facts_context / _rows / resurface / due_follow_ups: user + owner + kind.
    "CREATE INDEX IF NOT EXISTS idx_memories_user_owner_kind "
    "ON memories(user_id, owner, kind, status)",
    # add_memory's duplicate check, which runs before every single write.
    "CREATE INDEX IF NOT EXISTS idx_memories_user_owner_created "
    "ON memories(user_id, owner, created_ts)",
    # mood.recent(): WHERE user_id=? ORDER BY ts DESC LIMIT ?
    "CREATE INDEX IF NOT EXISTS idx_mood_user_ts ON mood_readings(user_id, ts)",
    # safety.recent(): WHERE user_id=? ORDER BY ts DESC LIMIT ?
    "CREATE INDEX IF NOT EXISTS idx_alerts_user_ts ON alerts(user_id, ts)",
)

#: Indexes from the single-user schema. After a RENAME COLUMN, SQLite rewrites
#: an index's definition to follow the new name — so these still work, they are
#: just named after a column that no longer exists. Dropping them keeps the
#: schema honest and costs nothing (the replacements above cover the same
#: queries).
_STALE_INDEXES = ("idx_turns_session",)


def init_db() -> None:
    with connect() as conn:
        # 1) Create tables (fresh installs get the full, final schema).
        conn.executescript(_SCHEMA)
        # 2) Upgrade older databases to that shape, losing nothing.
        _migrate(conn)
        # 3) Only now build indexes, which reference migrated columns.
        for name in _STALE_INDEXES:
            conn.execute(f"DROP INDEX IF EXISTS {name}")
        for statement in _INDEXES:
            conn.execute(statement)


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def _migrate(conn: sqlite3.Connection) -> None:
    """Bring a database created before multi-user up to the current schema.

    Idempotent and lossless: every row that existed keeps existing, and keeps
    belonging to somebody. Everything from the single-user era belongs to the
    one person who has been using this server, so it lands under 'default' —
    the id a request with no token gets. Nobody loses a friend to this upgrade,
    and running it twice does nothing the second time.
    """
    # The watcher stopped blocking the reply, so a `worry` it finds can now
    # land after the answer has already gone out. NULL means nobody has heard
    # about this one yet, and the next turn picks it up — see safety.carried().
    # `kind` splits a heart attack from «не хочу больше жить»: the same words
    # are wrong for both, and before this column there was only one message.
    turn_cols = _columns(conn, "turns")
    if turn_cols and "read_ts" not in turn_cols:
        # Everything said before the batching existed was read one exchange at
        # a time, as it happened. Stamping it read is the truth, and leaving it
        # NULL would hand the first batch the entire history of the friendship.
        conn.execute("ALTER TABLE turns ADD COLUMN read_ts REAL")
        conn.execute("UPDATE turns SET read_ts = ts WHERE read_ts IS NULL")

    # `ages` gained the teenager's own answer about memory a day after it was
    # added, so a database from in between has the table and not the column.
    age_cols = _columns(conn, "ages")
    if age_cols and "keeps" not in age_cols:
        conn.execute("ALTER TABLE ages ADD COLUMN keeps INTEGER")

    alert_cols = _columns(conn, "alerts")
    if alert_cols and "told_ts" not in alert_cols:
        conn.execute("ALTER TABLE alerts ADD COLUMN told_ts REAL")
    if alert_cols and "kind" not in alert_cols:
        conn.execute("ALTER TABLE alerts ADD COLUMN kind TEXT")

    memory_cols = _columns(conn, "memories")
    if memory_cols and "owner" not in memory_cols:
        conn.execute(
            "ALTER TABLE memories ADD COLUMN owner TEXT NOT NULL DEFAULT 'elder'"
        )
    if memory_cols and "user_id" not in memory_cols:
        conn.execute(
            "ALTER TABLE memories ADD COLUMN user_id TEXT NOT NULL DEFAULT 'default'"
        )
    # Everything remembered before this existed is still true as far as anyone
    # knows — NULL is exactly that statement, and it is the column default, so
    # the upgrade neither invents an ending for anything nor loses a row.
    if memory_cols and "superseded_ts" not in memory_cols:
        conn.execute("ALTER TABLE memories ADD COLUMN superseded_ts REAL")
    if memory_cols and "superseded_why" not in memory_cols:
        conn.execute("ALTER TABLE memories ADD COLUMN superseded_why TEXT")

    # `turns` and `usage` were keyed by a client-supplied `session_id`, which
    # every device sent as the literal string "default". The column is renamed
    # rather than replaced: the values are already right, and the rename makes
    # it impossible to keep believing this id comes from the client. It does
    # not — it is derived from the token, server-side, and always will be.
    turn_cols = _columns(conn, "turns")
    if "session_id" in turn_cols and "user_id" not in turn_cols:
        conn.execute("ALTER TABLE turns RENAME COLUMN session_id TO user_id")

    # Conversations recorded before he could tell a goodbye from a pause all
    # count as ended-without-one, which is the truth: back then there was no
    # way to say goodbye to him at all.
    if turn_cols and "farewell" not in turn_cols:
        conn.execute("ALTER TABLE turns ADD COLUMN farewell INTEGER NOT NULL DEFAULT 0")

    usage_cols = _columns(conn, "usage")
    if "session_id" in usage_cols and "user_id" not in usage_cols:
        conn.execute("ALTER TABLE usage RENAME COLUMN session_id TO user_id")

    # The diary was one row pinned by CHECK (id = 1) — a schema that cannot
    # hold two books. SQLite can't redefine a primary key in place, so the
    # table is rebuilt and the existing book handed to 'default'.
    diary_cols = _columns(conn, "diary")
    if diary_cols and "user_id" not in diary_cols:
        conn.execute("ALTER TABLE diary RENAME TO diary_single_user")
        conn.execute(
            """
            CREATE TABLE diary (
                user_id     TEXT PRIMARY KEY,
                content     TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                updated_ts  REAL NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO diary(user_id, content, fingerprint, updated_ts) "
            "SELECT 'default', content, fingerprint, updated_ts FROM diary_single_user"
        )
        conn.execute("DROP TABLE diary_single_user")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        # WAL: readers never block the writer and the writer never blocks
        # readers. With several people talking at once, the alternative is
        # "database is locked" in the middle of somebody's sentence.
        conn.execute("PRAGMA journal_mode=WAL")
        # NORMAL is the pairing WAL is designed for: no fsync per commit, so a
        # spoken turn doesn't wait on the disk. The worst case is losing the
        # last commit or two in a power cut — never a corrupt database. For a
        # log of conversation turns that is the right trade.
        conn.execute("PRAGMA synchronous=NORMAL")
        # If another writer holds the lock, wait for it rather than failing.
        # (`timeout=` above sets the same thing; stated here so it survives a
        # future edit to the connect call.)
        conn.execute("PRAGMA busy_timeout=30000")
        yield conn
        conn.commit()
    finally:
        conn.close()
