"""Memory — Phase 1 (simple, file-based).

The plan's full memory is Postgres + pgvector (facts table + story vectors).
That is Phase 2. For Phase 1 we keep a lightweight, dependency-free memory so
the talking loop already feels continuous:

  - Conversation history per session (JSON on disk, so it survives restarts).
  - Optional facts about the person (data/facts.json), hand-editable by family.

This module is written as a small interface so Phase 2 can swap the storage for
Postgres + pgvector without touching the rest of the app.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import config

# Keep the last N turns in the prompt (bounds cost + latency).
_MAX_TURNS_IN_CONTEXT = 20
# Keep more on disk than we send, so nothing is lost.
_MAX_TURNS_ON_DISK = 500


def _session_file(session_id: str) -> Path:
    safe = "".join(c for c in session_id if c.isalnum() or c in ("-", "_")) or "default"
    return config.DATA_DIR / f"session_{safe}.json"


def _load(session_id: str) -> list[dict[str, str]]:
    path = _session_file(session_id)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def history_for_brain(session_id: str) -> list[dict[str, str]]:
    """The recent conversation, formatted for Claude's messages array."""
    turns = _load(session_id)[-_MAX_TURNS_IN_CONTEXT:]
    return [{"role": t["role"], "content": t["content"]} for t in turns]


def save_turn(session_id: str, user_text: str, assistant_text: str) -> None:
    """Append one exchange (his message + the companion's reply) to disk."""
    turns = _load(session_id)
    turns.append({"role": "user", "content": user_text})
    turns.append({"role": "assistant", "content": assistant_text})
    turns = turns[-_MAX_TURNS_ON_DISK:]
    _session_file(session_id).write_text(
        json.dumps(turns, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def facts_context() -> str:
    """Known facts about the person, injected into the brain's system prompt.

    Reads data/facts.json if present. Family can edit it by hand for now; in
    Phase 2 the companion will learn and update facts automatically.
    """
    path = config.DATA_DIR / "facts.json"
    if not path.exists():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ""

    lines: list[str] = []
    for key, value in data.items():
        if isinstance(value, (list, tuple)):
            value = ", ".join(str(v) for v in value)
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)
