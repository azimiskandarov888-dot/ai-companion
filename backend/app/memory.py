"""The companion's memory — what makes it feel like a real friend.

Two owners share the store (see db.py):
  - owner='elder' : memory ABOUT the great-grandad — facts, stories, health,
                    mood, and caring follow-ups. This is what gets recalled to
                    make him feel known.
  - owner='bob'   : durable details Bob has revealed about his OWN life, so he
                    stays consistent about himself (Ben stays 73, etc.).

Kinds: fact | story | health | mood | follow_up.

How it's used:
  - Before each reply → facts_context('elder') + bob_self_context() +
    build_memory_context() load what Bob should have in mind.
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
def log_turn(session_id: str, role: str, content: str) -> None:
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO turns(session_id, role, content, ts) VALUES (?,?,?,?)",
            (session_id, role, content, time.time()),
        )


def recent_turns(session_id: str, limit: int = RECENT_TURNS) -> list[dict[str, str]]:
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM turns WHERE session_id=? "
            "ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


# --------------------------------------------------------------------------- #
# Storing what the companion learns
# --------------------------------------------------------------------------- #
def add_memory(
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
            "SELECT id FROM memories WHERE owner=? AND kind=? AND content=? LIMIT 1",
            (owner, kind, content),
        ).fetchone()
        if dup:
            return None
        cur = conn.execute(
            "INSERT INTO memories(owner, kind, title, content, importance, status, "
            "embedding, meta, created_ts, recall_count) VALUES (?,?,?,?,?,?,?,?,?,0)",
            (
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
def facts_context(owner: str = "elder") -> str:
    """The known facts for an owner, formatted for the prompt."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT content FROM memories WHERE kind='fact' AND owner=? "
            "ORDER BY importance DESC, created_ts ASC",
            (owner,),
        ).fetchall()
    return "\n".join(f"- {r['content']}" for r in rows)


def bob_self_context() -> str:
    """Durable details Bob has said about his own life (to stay consistent)."""
    return facts_context(owner="bob")


def seed_facts_from_file(path=None) -> int:
    """Import hand-written facts about the elder from data/facts.json (once).

    Lets family pre-load what they know — family, birthdays, routine, his
    doctor/contact. Safe to run every startup: duplicates are skipped.
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
        if add_memory("fact", f"{key}: {value}", title=str(key), importance=3):
            added += 1
    return added


# --------------------------------------------------------------------------- #
# Recall (the elder's memory)
# --------------------------------------------------------------------------- #
def _rows(kinds: tuple[str, ...], owner: str = "elder") -> list:
    marks = ",".join("?" for _ in kinds)
    with db.connect() as conn:
        return conn.execute(
            f"SELECT * FROM memories WHERE owner=? AND kind IN ({marks})",
            (owner, *kinds),
        ).fetchall()


async def recall_relevant(
    query_text: str, k: int = RECALL_K, exclude: set[int] | None = None
) -> list[dict]:
    """Semantically recall the elder's stories/health notes most relevant now."""
    exclude = exclude or set()
    rows = [r for r in _rows(("story", "health")) if r["id"] not in exclude]
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


def resurface(exclude: set[int] | None = None) -> dict | None:
    """Pick a warm story he hasn't been reminded of in a while (spaced recall)."""
    exclude = exclude or set()
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM memories WHERE owner='elder' AND kind='story' "
            "ORDER BY (last_recalled_ts IS NULL) DESC, last_recalled_ts ASC, "
            "created_ts ASC LIMIT 5"
        ).fetchall()
    candidates = [r for r in rows if r["id"] not in exclude]
    if not candidates:
        return None
    chosen = candidates[0]
    _mark_recalled([chosen["id"]])
    return dict(chosen)


def due_follow_ups(limit: int = 1) -> list[dict]:
    """Caring things that are *due* to be checked back on now (never nagging)."""
    now = time.time()
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM memories WHERE owner='elder' AND kind='follow_up' "
            "AND status='open' AND created_ts < ? AND created_ts > ? "
            "AND recall_count < ? AND (last_recalled_ts IS NULL OR last_recalled_ts < ?) "
            "ORDER BY created_ts ASC LIMIT ?",
            (
                now - FOLLOW_UP_MIN_AGE,
                now - FOLLOW_UP_MAX_AGE,
                FOLLOW_UP_MAX_SURFACES,
                now - FOLLOW_UP_COOLDOWN,
                limit,
            ),
        ).fetchall()
    return [dict(r) for r in rows]


def surface_follow_up(follow_up_id: int) -> None:
    """Mark a follow-up as raised; auto-close it once it's been raised enough."""
    _mark_recalled([follow_up_id])
    with db.connect() as conn:
        conn.execute(
            "UPDATE memories SET status='done' "
            "WHERE id=? AND kind='follow_up' AND recall_count >= ?",
            (follow_up_id, FOLLOW_UP_MAX_SURFACES),
        )


def latest_mood() -> str | None:
    with db.connect() as conn:
        row = conn.execute(
            "SELECT content FROM memories WHERE owner='elder' AND kind='mood' "
            "ORDER BY created_ts DESC LIMIT 1"
        ).fetchone()
    return row["content"] if row else None


def counts(owner: str = "elder") -> dict[str, int]:
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT kind, COUNT(*) AS n FROM memories WHERE owner=? GROUP BY kind",
            (owner,),
        ).fetchall()
    return {r["kind"]: r["n"] for r in rows}


# --------------------------------------------------------------------------- #
# Assemble the elder-memory block for the system prompt
# --------------------------------------------------------------------------- #
async def build_memory_context(session_id: str, query_text: str) -> str:
    """Recalled stories + (sometimes) a resurfaced memory + a due follow-up + mood.

    Facts are fetched separately (facts_context). He always speaks first; this is
    what Bob should have in mind when he answers.
    """
    used: set[int] = set()
    sections: list[str] = []

    relevant = await recall_relevant(query_text, exclude=used)
    used.update(r["id"] for r in relevant)
    if relevant:
        lines = "\n".join(f"- {_fmt(r)}" for r in relevant)
        sections.append(
            "Из ваших прошлых бесед (можешь мягко вспомнить, если к слову):\n" + lines
        )

    # A gentle, spaced "а помнишь…" — sometimes, out of nowhere.
    if random.random() < RESURFACE_CHANCE:
        r = resurface(exclude=used)
        if r:
            used.add(r["id"])
            sections.append(
                "Тёплый момент, о котором можешь вспомнить сам, даже без повода:\n"
                f"- {_fmt(r)}"
            )

    # A caring follow-up that's due — check back on what he mentioned before.
    for fup in due_follow_ups(limit=1):
        sections.append(
            "По-доброму поинтересуйся, как дела с тем, о чём он говорил раньше:\n"
            f"- {fup['content']}"
        )
        surface_follow_up(fup["id"])

    mood = latest_mood()
    if mood:
        sections.append(f"Его настроение в последнее время: {mood}.")

    return "\n\n".join(sections)


def _fmt(row: dict) -> str:
    title = row.get("title")
    content = row.get("content", "")
    return f"«{title}» — {content}" if title else content
