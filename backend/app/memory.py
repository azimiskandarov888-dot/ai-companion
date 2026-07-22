"""The companion's memory — what makes it feel like a real friend.

What it holds (in SQLite, via db.py):
  - facts      : durable truths about him (family, birthdays, his accident,
                 routine, likes, doctor/contacts).
  - stories    : anecdotes and topics he shared, embedded for semantic recall
                 days or months later ("а помните, вы рассказывали про…").
  - health     : health things he mentioned (never advice — just remembered).
  - mood       : a gentle read of his mood each conversation, tracked over time.
  - follow_up  : things a caring friend checks back on ("как ваше колено сегодня?").

How it's used:
  - Before each reply → build_reply_context() loads relevant facts + semantically
    recalled stories + open follow-ups + (sometimes) a spontaneously resurfaced
    warm memory + recent mood, and hands them to the brain.
  - After each reply → learn.py extracts new facts/stories/etc. in the background.

This module is a small, storage-agnostic interface. Phase 2 can replace the
SQLite/cosine internals with Postgres + pgvector without changing its callers.
"""

from __future__ import annotations

import json
import random
import time

from . import db, embeddings

# How many recent turns to feed the brain as live conversation.
RECENT_TURNS = 20
# How many semantically-recalled stories to surface per reply.
RECALL_K = 4
# Chance of spontaneously resurfacing an old warm memory in a normal reply.
RESURFACE_CHANCE = 0.35
# A follow-up stops being raised after it's been surfaced this many times.
FOLLOW_UP_MAX_SURFACES = 2
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
            "SELECT id FROM memories WHERE kind=? AND content=? LIMIT 1",
            (kind, content),
        ).fetchone()
        if dup:
            return None
        cur = conn.execute(
            "INSERT INTO memories(kind, title, content, importance, status, "
            "embedding, meta, created_ts, recall_count) VALUES (?,?,?,?,?,?,?,?,0)",
            (
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
# Recall
# --------------------------------------------------------------------------- #
def facts_context() -> str:
    """All known facts about him — always worth having in context (small)."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT content FROM memories WHERE kind='fact' "
            "ORDER BY importance DESC, created_ts ASC"
        ).fetchall()
    return "\n".join(f"- {r['content']}" for r in rows)


def seed_facts_from_file(path=None) -> int:
    """Import hand-written facts from data/facts.json into memory (once).

    Lets family pre-load what they know about him — family, birthdays, routine,
    his doctor/contact. Safe to run every startup: duplicates are skipped.
    """
    from . import config

    path = path or (config.DATA_DIR / "facts.json")
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0
    added = 0
    for key, value in data.items():
        if isinstance(value, (list, tuple)):
            value = ", ".join(str(v) for v in value)
        if add_memory("fact", f"{key}: {value}", title=str(key), importance=3):
            added += 1
    return added


def _rows(kinds: tuple[str, ...]) -> list:
    marks = ",".join("?" for _ in kinds)
    with db.connect() as conn:
        return conn.execute(
            f"SELECT * FROM memories WHERE kind IN ({marks})", kinds
        ).fetchall()


async def recall_relevant(
    query_text: str, k: int = RECALL_K, exclude: set[int] | None = None
) -> list[dict]:
    """Semantically recall the stories/health notes most relevant to `query_text`."""
    exclude = exclude or set()
    rows = [r for r in _rows(("story", "health")) if r["id"] not in exclude]
    if not rows:
        return []

    if embeddings.available() and query_text.strip():
        try:
            q = await embeddings.embed(query_text)
        except Exception:
            q = None
    else:
        q = None

    if q is not None:
        scored = []
        for r in rows:
            emb = json.loads(r["embedding"]) if r["embedding"] else None
            scored.append((embeddings.cosine(q, emb), r))
        scored.sort(key=lambda t: t[0], reverse=True)
        # Only keep genuinely related memories.
        picked = [r for score, r in scored[:k] if score > 0.2]
    else:
        # No embeddings → fall back to the most recent stories.
        picked = sorted(rows, key=lambda r: r["created_ts"], reverse=True)[:k]

    _mark_recalled([r["id"] for r in picked])
    return [dict(r) for r in picked]


def resurface(exclude: set[int] | None = None) -> dict | None:
    """Pick a warm story he hasn't been reminded of in a while (spaced recall).

    This is the "out of nowhere, remember when…" magic — gentle and not repetitive.
    """
    exclude = exclude or set()
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM memories WHERE kind='story' "
            "ORDER BY (last_recalled_ts IS NULL) DESC, last_recalled_ts ASC, "
            "created_ts ASC LIMIT 5"
        ).fetchall()
    candidates = [r for r in rows if r["id"] not in exclude]
    if not candidates:
        return None
    chosen = candidates[0]
    _mark_recalled([chosen["id"]])
    return dict(chosen)


def open_follow_ups(limit: int = 3) -> list[dict]:
    """Caring things to check back on — not too old, not already over-raised."""
    cutoff = time.time() - FOLLOW_UP_MAX_AGE
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM memories WHERE kind='follow_up' AND status='open' "
            "AND created_ts > ? AND recall_count < ? "
            "ORDER BY created_ts ASC LIMIT ?",
            (cutoff, FOLLOW_UP_MAX_SURFACES, limit),
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
            "SELECT content FROM memories WHERE kind='mood' "
            "ORDER BY created_ts DESC LIMIT 1"
        ).fetchone()
    return row["content"] if row else None


def counts() -> dict[str, int]:
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT kind, COUNT(*) AS n FROM memories GROUP BY kind"
        ).fetchall()
    return {r["kind"]: r["n"] for r in rows}


# --------------------------------------------------------------------------- #
# Assemble everything the brain should know before it replies / greets
# --------------------------------------------------------------------------- #
async def build_reply_context(
    session_id: str,
    query_text: str,
    *,
    for_greeting: bool = False,
) -> tuple[str, str]:
    """Return (facts_context, memory_context) strings for the system prompt."""
    facts = facts_context()

    used: set[int] = set()
    sections: list[str] = []

    relevant = await recall_relevant(query_text, exclude=used)
    used.update(r["id"] for r in relevant)
    if relevant:
        lines = [f"- {_fmt(r)}" for r in relevant]
        sections.append(
            "Из ваших прошлых бесед (можешь мягко вспомнить, если к слову):\n"
            + "\n".join(lines)
        )

    # A gentle, spaced "remember when…" — always in greetings, sometimes in chat.
    if for_greeting or random.random() < RESURFACE_CHANCE:
        r = resurface(exclude=used)
        if r:
            used.add(r["id"])
            sections.append(
                "Тёплый момент, о котором можешь вспомнить сам, даже без повода:\n"
                f"- {_fmt(r)}"
            )

    # Caring follow-ups — check back on what he mentioned before.
    fups = open_follow_ups(limit=1 if not for_greeting else 2)
    if fups:
        lines = [f"- {r['content']}" for r in fups]
        sections.append(
            "По-доброму поинтересуйся, как дела с тем, о чём он говорил раньше:\n"
            + "\n".join(lines)
        )
        if for_greeting:
            for r in fups:
                surface_follow_up(r["id"])

    mood = latest_mood()
    if mood:
        sections.append(f"Его настроение в последнее время: {mood}.")

    return facts, "\n\n".join(sections)


def _fmt(row: dict) -> str:
    title = row.get("title")
    content = row.get("content", "")
    return f"«{title}» — {content}" if title else content
