"""Learning — turn each conversation into lasting memory.

After the companion replies, this runs in the background (so it never slows the
spoken response). It asks the brain to read the exchange and pull out what a
caring friend would remember about *him*:

  - facts       (family, birthdays, his accident, routine, likes, contacts)
  - stories     (anecdotes / topics he shared — embedded for later recall)
  - health      (things he mentioned about his health — remembered, not advised)
  - mood        (a gentle read of how he seemed)
  - follow_ups  (things to check back on next time)

Robust by design: if extraction or parsing fails, we simply skip learning for
that turn — the conversation itself is never affected.
"""

from __future__ import annotations

import json
import sys

from anthropic import AsyncAnthropic

from . import config, embeddings, memory

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


_EXTRACTION_SYSTEM = """Ты ведёшь память о пожилом человеке для его тёплого друга-companion.
Прочитай последний обмен репликами и выпиши только то, что стоит ЗАПОМНИТЬ О ЧЕЛОВЕКЕ (не о companion, не общие факты о мире).

Отвечай ТОЛЬКО в формате JSON, без пояснений и без текста вокруг. Все значения — по-русски. Если чего-то нет — пустой список или пустая строка.

Формат:
{
  "facts": [{"category": "семья|здоровье|распорядок|интересы|контакты|прочее", "value": "короткий факт"}],
  "stories": [{"title": "короткое название", "summary": "1-2 предложения: что он рассказал"}],
  "health": ["что он упомянул о самочувствии (без диагнозов и советов)"],
  "mood": "одно-два слова о его настроении, или пусто",
  "follow_ups": ["о чём по-доброму спросить в следующий раз"]
}

Записывай только заметное и настоящее. Не выдумывай. Мелкую болтовню пропускай."""


async def learn_from_exchange(
    session_id: str, user_text: str, assistant_text: str
) -> None:
    if not config.ANTHROPIC_API_KEY:
        return
    try:
        data = await _extract(user_text, assistant_text)
    except Exception as e:  # never let learning crash the request lifecycle
        print(f"[learn] extraction failed: {e}", file=sys.stderr)
        return

    try:
        await _store(data)
    except Exception as e:
        print(f"[learn] storing failed: {e}", file=sys.stderr)


async def _extract(user_text: str, assistant_text: str) -> dict:
    client = _get_client()
    existing = memory.facts_context() or "(пока ничего)"
    prompt = (
        f"Что уже известно о человеке (не повторяй это):\n{existing}\n\n"
        f"Последний обмен репликами:\n"
        f"ЧЕЛОВЕК: {user_text}\n"
        f"COMPANION: {assistant_text}\n\n"
        "Выпиши новое, что стоит запомнить, в требуемом JSON."
    )
    message = await client.messages.create(
        model=config.BRAIN_MODEL,
        max_tokens=700,
        system=_EXTRACTION_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in message.content if b.type == "text").strip()
    return _parse_json(text)


def _parse_json(text: str) -> dict:
    # Tolerate accidental code fences or surrounding prose.
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return {}
    return json.loads(text[start : end + 1])


async def _store(data: dict) -> None:
    for fact in data.get("facts", []) or []:
        cat = (fact.get("category") or "прочее").strip()
        val = (fact.get("value") or "").strip()
        if val:
            memory.add_memory("fact", f"{cat}: {val}", title=cat, importance=2)

    for story in data.get("stories", []) or []:
        title = (story.get("title") or "").strip() or None
        summary = (story.get("summary") or "").strip()
        if summary:
            emb = await _safe_embed(f"{title or ''} {summary}")
            memory.add_memory("story", summary, title=title, embedding=emb)

    for note in data.get("health", []) or []:
        note = (note or "").strip()
        if note:
            emb = await _safe_embed(note)
            memory.add_memory("health", note, embedding=emb, importance=2)

    mood = (data.get("mood") or "").strip()
    if mood:
        memory.add_memory("mood", mood)

    for fup in data.get("follow_ups", []) or []:
        fup = (fup or "").strip()
        if fup:
            memory.add_memory("follow_up", fup, status="open", importance=2)


async def _safe_embed(text: str) -> list[float] | None:
    if not embeddings.available() or not text.strip():
        return None
    try:
        return await embeddings.embed(text)
    except Exception:
        return None
