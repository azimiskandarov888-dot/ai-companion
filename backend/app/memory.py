"""The companion's memory — what makes it feel like a real friend.

Every function here takes `user_id` FIRST, and none of them has a default for
it. That is deliberate and it is the whole safety model of this module: a
forgotten argument becomes a TypeError the first time the code runs, instead
of a silent read from somebody else's life. A default value would have made
every missed call site a privacy bug that never raises — which is exactly the
bug this file was written to end.

Two owners share the store, per user (see db.py):
  - owner='elder' : memory ABOUT the person — facts, stories, health, mood, and
                    caring follow-ups. This is what gets recalled to make them
                    feel known.
  - owner='bob'   : durable details the companion has revealed about his OWN
                    life, so he stays consistent about himself.

Kinds: fact | story | health | mood | follow_up.

How it's used:
  - Before each reply → facts_context(uid, 'elder') + bob_self_context(uid) +
    build_memory_context(uid, ...) load what he should have in mind.
  - After each reply → learn.py extracts new memories in the background.

Storage-agnostic on purpose. A later phase can swap SQLite/cosine for
Postgres + pgvector without changing callers.
"""

from __future__ import annotations

import json
import random
import time

from . import db, embeddings

# How many recent turns to feed the brain as live conversation. 12 covers the
# thread of a spoken chat; anything older that mattered has been distilled into
# memory and comes back through recall. Every extra turn here is tokens the
# brain re-reads before EVERY reply — this is spoken conversation, where that
# wait is a silence — so the window stays small on purpose.
RECENT_TURNS = 12
# How many semantically-recalled stories to surface per reply.
RECALL_K = 4
# Only keep recalled stories at least this related (cosine) to what he just said.
RECALL_MIN_SCORE = 0.2
# Chance of spontaneously resurfacing an old warm memory in a reply.
RESURFACE_CHANCE = 0.25
# A follow-up stops being raised after it's been surfaced this many times.
FOLLOW_UP_MAX_SURFACES = 2
# Don't check back on something in the same conversation — wait at least this long
# (so "как твоё колено?" comes next time he talks, not two sentences later).
FOLLOW_UP_MIN_AGE = 3 * 3600
# Once raised, don't raise the same follow-up again for this long.
FOLLOW_UP_COOLDOWN = 12 * 3600
# Follow-ups older than this (seconds) are considered stale and dropped.
FOLLOW_UP_MAX_AGE = 21 * 24 * 3600


# --------------------------------------------------------------------------- #
# Raw conversation log
# --------------------------------------------------------------------------- #
def log_turn(user_id: str, role: str, content: str) -> None:
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO turns(user_id, role, content, ts) VALUES (?,?,?,?)",
            (user_id, role, content, time.time()),
        )


def recent_turns(user_id: str, limit: int = RECENT_TURNS) -> list[dict[str, str]]:
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM turns WHERE user_id=? "
            "ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


# --------------------------------------------------------------------------- #
# Storing what the companion learns
# --------------------------------------------------------------------------- #
def add_memory(
    user_id: str,
    kind: str,
    content: str,
    *,
    owner: str = "elder",
    title: str | None = None,
    embedding: list[float] | None = None,
    importance: int = 1,
    status: str = "open",
    meta: dict | None = None,
) -> int | None:
    """Store one memory, skipping exact duplicates. Returns the new id or None."""
    content = content.strip()
    if not content:
        return None
    with db.connect() as conn:
        dup = conn.execute(
            "SELECT id FROM memories WHERE user_id=? AND owner=? AND kind=? "
            "AND content=? LIMIT 1",
            (user_id, owner, kind, content),
        ).fetchone()
        if dup:
            return None
        cur = conn.execute(
            "INSERT INTO memories(user_id, owner, kind, title, content, importance, "
            "status, embedding, meta, created_ts, recall_count) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,0)",
            (
                user_id,
                owner,
                kind,
                title,
                content,
                importance,
                status,
                json.dumps(embedding) if embedding else None,
                json.dumps(meta, ensure_ascii=False) if meta else None,
                time.time(),
            ),
        )
        return cur.lastrowid


def _mark_recalled(ids: list[int]) -> None:
    if not ids:
        return
    now = time.time()
    with db.connect() as conn:
        conn.executemany(
            "UPDATE memories SET last_recalled_ts=?, recall_count=recall_count+1 "
            "WHERE id=?",
            [(now, i) for i in ids],
        )


# --------------------------------------------------------------------------- #
# Facts
# --------------------------------------------------------------------------- #
def facts_context(user_id: str, owner: str = "elder") -> str:
    """The known facts for an owner, formatted for the prompt."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT content FROM memories WHERE user_id=? AND kind='fact' AND owner=? "
            "ORDER BY importance DESC, created_ts ASC",
            (user_id, owner),
        ).fetchall()
    return "\n".join(f"- {r['content']}" for r in rows)


def bob_self_context(user_id: str) -> str:
    """Durable details the companion has said about his own life (consistency)."""
    return facts_context(user_id, owner="bob")


def seed_facts_from_file(user_id: str, path=None) -> int:
    """Import hand-written facts about the user from data/facts.json (once).

    Lets family pre-load what they know — family, birthdays, routine, his
    doctor/contact. Safe to run every startup: duplicates are skipped.

    This file belongs to whoever runs the server, so it seeds the anonymous
    user at startup. It is not a multi-user feature and deliberately hasn't
    become one: a shared server has no business reading one family's notes
    into everybody's memory.
    """
    from . import config

    path = path or (config.DATA_DIR / "facts.json")
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0
    if not isinstance(data, dict):
        return 0
    added = 0
    for key, value in data.items():
        if isinstance(value, (list, tuple)):
            value = ", ".join(str(v) for v in value)
        if add_memory(
            user_id, "fact", f"{key}: {value}", title=str(key), importance=3
        ):
            added += 1
    return added


# --------------------------------------------------------------------------- #
# Recall (the user's memory)
# --------------------------------------------------------------------------- #
def _rows(user_id: str, kinds: tuple[str, ...], owner: str = "elder") -> list:
    marks = ",".join("?" for _ in kinds)
    with db.connect() as conn:
        return conn.execute(
            f"SELECT * FROM memories WHERE user_id=? AND owner=? AND kind IN ({marks})",
            (user_id, owner, *kinds),
        ).fetchall()


async def recall_relevant(
    user_id: str, query_text: str, k: int = RECALL_K, exclude: set[int] | None = None
) -> list[dict]:
    """Semantically recall the stories/health notes most relevant right now."""
    exclude = exclude or set()
    rows = [r for r in _rows(user_id, ("story", "health")) if r["id"] not in exclude]
    if not rows:
        return []

    q = None
    if embeddings.available() and query_text.strip():
        try:
            q = await embeddings.embed(query_text)
        except Exception:
            q = None

    if q is not None:
        scored = [
            (embeddings.cosine(q, json.loads(r["embedding"]) if r["embedding"] else None), r)
            for r in rows
        ]
        scored.sort(key=lambda t: t[0], reverse=True)
        picked = [r for score, r in scored[:k] if score > RECALL_MIN_SCORE]
    else:
        # No embeddings → fall back to the most recent stories.
        picked = sorted(rows, key=lambda r: r["created_ts"], reverse=True)[:k]

    _mark_recalled([r["id"] for r in picked])
    return [dict(r) for r in picked]


def resurface(user_id: str, exclude: set[int] | None = None) -> dict | None:
    """Pick a warm story he hasn't been reminded of in a while (spaced recall)."""
    exclude = exclude or set()
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM memories WHERE user_id=? AND owner='elder' AND kind='story' "
            "ORDER BY (last_recalled_ts IS NULL) DESC, last_recalled_ts ASC, "
            "created_ts ASC LIMIT 5",
            (user_id,),
        ).fetchall()
    candidates = [r for r in rows if r["id"] not in exclude]
    if not candidates:
        return None
    chosen = candidates[0]
    _mark_recalled([chosen["id"]])
    return dict(chosen)


def due_follow_ups(user_id: str, limit: int = 1) -> list[dict]:
    """Caring things that are *due* to be checked back on now (never nagging)."""
    now = time.time()
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM memories WHERE user_id=? AND owner='elder' AND kind='follow_up' "
            "AND status='open' AND created_ts < ? AND created_ts > ? "
            "AND recall_count < ? AND (last_recalled_ts IS NULL OR last_recalled_ts < ?) "
            "ORDER BY created_ts ASC LIMIT ?",
            (
                user_id,
                now - FOLLOW_UP_MIN_AGE,
                now - FOLLOW_UP_MAX_AGE,
                FOLLOW_UP_MAX_SURFACES,
                now - FOLLOW_UP_COOLDOWN,
                limit,
            ),
        ).fetchall()
    return [dict(r) for r in rows]


def surface_follow_up(user_id: str, follow_up_id: int) -> None:
    """Mark a follow-up as raised; auto-close it once it's been raised enough."""
    _mark_recalled([follow_up_id])
    with db.connect() as conn:
        conn.execute(
            "UPDATE memories SET status='done' "
            "WHERE id=? AND user_id=? AND kind='follow_up' AND recall_count >= ?",
            (follow_up_id, user_id, FOLLOW_UP_MAX_SURFACES),
        )


def latest_mood(user_id: str) -> str | None:
    with db.connect() as conn:
        row = conn.execute(
            "SELECT content FROM memories WHERE user_id=? AND owner='elder' AND kind='mood' "
            "ORDER BY created_ts DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    return row["content"] if row else None


def counts(user_id: str, owner: str = "elder") -> dict[str, int]:
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT kind, COUNT(*) AS n FROM memories WHERE user_id=? AND owner=? "
            "GROUP BY kind",
            (user_id, owner),
        ).fetchall()
    return {r["kind"]: r["n"] for r in rows}


def forget_companion(user_id: str) -> None:
    """A new friend means a new life — for THIS person and nobody else.

    Erases the previous companion's self-memories, the conversation log, and
    his diary. Keeps what was learned about the USER — family, birthdays,
    routine stay true regardless of who they are talking to.

    The `WHERE user_id=?` on all three statements is the whole point. Without
    it (and it was missing until multi-user landed) one person tapping «начать
    заново» wipes the conversation of every other person on the server.
    """
    with db.connect() as conn:
        conn.execute("DELETE FROM memories WHERE user_id=? AND owner='bob'", (user_id,))
        conn.execute("DELETE FROM turns WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM diary WHERE user_id=?", (user_id,))


# --------------------------------------------------------------------------- #
# Assemble the memory block for the system prompt
# --------------------------------------------------------------------------- #
async def build_memory_context(user_id: str, query_text: str) -> str:
    """Recalled stories + (sometimes) a resurfaced memory + a due follow-up + mood.

    Facts are fetched separately (facts_context). He always speaks first; this is
    what the companion should have in mind when he answers.
    """
    used: set[int] = set()
    sections: list[str] = []

    relevant = await recall_relevant(user_id, query_text, exclude=used)
    used.update(r["id"] for r in relevant)
    if relevant:
        lines = "\n".join(f"- {_fmt(r)}" for r in relevant)
        sections.append(
            "Из ваших прошлых бесед (можешь мягко вспомнить, если к слову):\n" + lines
        )

    # A gentle, spaced "а помнишь…" — sometimes, out of nowhere.
    if random.random() < RESURFACE_CHANCE:
        r = resurface(user_id, exclude=used)
        if r:
            used.add(r["id"])
            sections.append(
                "Тёплый момент, о котором можешь вспомнить сам, даже без повода:\n"
                f"- {_fmt(r)}"
            )

    # A caring follow-up that's due — check back on what he mentioned before.
    for fup in due_follow_ups(user_id, limit=1):
        sections.append(
            "По-доброму поинтересуйся, как дела с тем, о чём он говорил раньше:\n"
            f"- {fup['content']}"
        )
        surface_follow_up(user_id, fup["id"])

    mood = latest_mood(user_id)
    if mood:
        sections.append(f"Его настроение в последнее время: {mood}.")

    return "\n\n".join(sections)


def _fmt(row: dict) -> str:
    title = row.get("title")
    content = row.get("content", "")
    return f"«{title}» — {content}" if title else content
