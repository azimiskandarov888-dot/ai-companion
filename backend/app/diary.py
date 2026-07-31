"""The companion's diary — his handwritten book about his friend.

Two memories, deliberately separate:

  - His REAL memory (the ``memories`` table) is distilled notes — everything
    written as short as possible, optimized so he can remember fast. It is
    internal only: users never see it (``/api/memory`` is a dev tool).
  - His DIARY (this module) is what users see instead: a beautiful, warmly
    written biography of his friend, composed by the companion himself from
    that real memory — like an old handmade book he keeps.

The diary is rewritten only when his real memory has changed (a fingerprint
guards it), so opening the book is instant and free most of the time.
"""

from __future__ import annotations

import hashlib
import time

from . import brain, config, db, persona

# Which memory kinds the diary draws on. Follow-ups are his private intentions
# ("ask about the knee") — they belong to him, not to the book.
_DIARY_KINDS = ("fact", "story", "health", "mood")

_DIARY_SYSTEM = """Ты — {name}. У тебя есть старая самодельная книга — твой личный дневник, который ты ведёшь от руки. В нём ты пишешь о своём друге{friend_clause}.

Напиши запись — маленькую биографию твоего друга глазами того, кому он дорог. Пиши:
- тепло, красиво и просто — как пишут для себя, а не для отчёта;
- от первого лица («я заметил…», «он рассказывал мне…»);
- связным текстом, БЕЗ списков, пунктов и заголовков;
- 3–6 небольших абзацев;
- только о том, что действительно есть в твоих заметках ниже — ничего не выдумывай и не добавляй новых фактов;
- о здоровье и трудном — бережно и мягко, без диагнозов и советов.

Это книга, которую твой друг однажды откроет и прочитает о себе."""

# The very first page, before he knows anything — no AI call needed.
_FIRST_PAGE = (
    "Мы только-только познакомились. Я ещё почти ничего не знаю о моём новом "
    "друге — но у меня хорошее предчувствие. Пусть эта книга начнётся с чистой "
    "страницы: всё главное у нас впереди."
)

_KIND_LABEL = {
    "fact": "Что ты знаешь о нём",
    "story": "Истории, которые он тебе рассказывал",
    "health": "Про его здоровье (пиши особенно бережно)",
    "mood": "Его настроение в разные дни",
}


def _memory_rows() -> list:
    marks = ",".join("?" for _ in _DIARY_KINDS)
    with db.connect() as conn:
        return conn.execute(
            f"SELECT id, kind, title, content FROM memories "
            f"WHERE owner='elder' AND kind IN ({marks}) ORDER BY created_ts ASC",
            _DIARY_KINDS,
        ).fetchall()


def _fingerprint(rows) -> str:
    joined = "\n".join(f"{r['id']}|{r['kind']}|{r['content']}" for r in rows)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()


def _notes_text(rows) -> str:
    """His distilled notes, grouped by kind, as the writing material."""
    grouped: dict[str, list[str]] = {}
    for r in rows:
        line = f"«{r['title']}» — {r['content']}" if r["title"] else r["content"]
        grouped.setdefault(r["kind"], []).append(f"- {line}")
    parts = [
        _KIND_LABEL[kind] + ":\n" + "\n".join(grouped[kind])
        for kind in _DIARY_KINDS
        if kind in grouped
    ]
    return "\n\n".join(parts)


def _load_cached() -> dict | None:
    with db.connect() as conn:
        row = conn.execute(
            "SELECT content, fingerprint, updated_ts FROM diary WHERE id=1"
        ).fetchone()
    return dict(row) if row else None


def _save(content: str, fingerprint: str) -> None:
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO diary(id, content, fingerprint, updated_ts) "
            "VALUES (1,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET content=excluded.content, "
            "fingerprint=excluded.fingerprint, updated_ts=excluded.updated_ts",
            (content, fingerprint, time.time()),
        )


async def get_diary() -> dict:
    """The diary as the user opens it — rewritten only when memory has grown."""
    name = persona.persona_name()
    rows = _memory_rows()
    fp = _fingerprint(rows)

    cached = _load_cached()
    if cached and cached["fingerprint"] == fp:
        return {
            "companion": name,
            "text": cached["content"],
            "updated_ts": cached["updated_ts"],
            "rewritten": False,
        }

    if not rows:
        text = _FIRST_PAGE
    else:
        friend_clause = (
            f" — его зовут {config.ELDER_NAME}" if config.ELDER_NAME else ""
        )
        system = _DIARY_SYSTEM.format(name=name, friend_clause=friend_clause)
        text = await brain.generate_text(
            system, "Твои заметки о нём:\n\n" + _notes_text(rows)
        )
        if not text:  # the pen failed — keep the last good page rather than a blank
            text = cached["content"] if cached else _FIRST_PAGE

    _save(text, fp)
    return {
        "companion": name,
        "text": text,
        "updated_ts": time.time(),
        "rewritten": True,
    }
