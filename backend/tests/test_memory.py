"""Memory: owner isolation, facts, semantic recall, resurfacing, follow-ups."""

from __future__ import annotations

import asyncio
import json
import time

from app import config, db, embeddings, memory


def test_owner_isolation():
    memory.add_memory("fact", "семья: внук Алёша", owner="elder")
    memory.add_memory("fact", "живёт у моря", owner="bob")

    elder = memory.facts_context("elder")
    bob = memory.bob_self_context()

    assert "внук Алёша" in elder and "у моря" not in elder
    assert "у моря" in bob and "внук Алёша" not in bob


def test_add_memory_dedup():
    first = memory.add_memory("fact", "любит уху", owner="elder")
    dup = memory.add_memory("fact", "любит уху", owner="elder")
    # Same content for a DIFFERENT owner is allowed.
    other = memory.add_memory("fact", "любит уху", owner="bob")
    assert first is not None and dup is None and other is not None


def test_seed_facts_from_file():
    (config.DATA_DIR / "facts.json").write_text(
        json.dumps({"Имя": "Иван", "Любит": ["чай", "песни"]}, ensure_ascii=False),
        encoding="utf-8",
    )
    added = memory.seed_facts_from_file()
    assert added == 2
    facts = memory.facts_context("elder")
    assert "Иван" in facts and "чай, песни" in facts
    # Idempotent — re-seeding adds nothing.
    assert memory.seed_facts_from_file() == 0


def test_semantic_recall_orders_by_relevance(monkeypatch):
    memory.add_memory("story", "Ловил рыбу на реке", owner="elder",
                      title="Рыбалка", embedding=[1.0, 0.0, 0.0])
    memory.add_memory("story", "Танцевал на свадьбе", owner="elder",
                      title="Свадьба", embedding=[0.0, 1.0, 0.0])

    async def fake_embed(text):
        return [0.95, 0.05, 0.0]  # close to the fishing story

    monkeypatch.setattr(embeddings, "available", lambda: True)
    monkeypatch.setattr(embeddings, "embed", fake_embed)

    picked = asyncio.run(memory.recall_relevant("расскажи про рыбалку", k=2))
    assert picked and picked[0]["title"] == "Рыбалка"


def test_recall_falls_back_to_recency_without_embeddings(monkeypatch):
    memory.add_memory("story", "старая история", owner="elder", title="A")
    memory.add_memory("story", "новая история", owner="elder", title="B")
    monkeypatch.setattr(embeddings, "available", lambda: False)
    picked = asyncio.run(memory.recall_relevant("что угодно", k=1))
    assert picked and picked[0]["title"] == "B"  # most recent


def test_resurface_returns_a_story():
    memory.add_memory("story", "тёплый момент", owner="elder", title="Момент")
    r = memory.resurface()
    assert r is not None and r["title"] == "Момент"


def _backdate(memory_id: int, created_ago: float, recalled_ago: float | None = None):
    now = time.time()
    with db.connect() as conn:
        conn.execute(
            "UPDATE memories SET created_ts=?, last_recalled_ts=? WHERE id=?",
            (now - created_ago, None if recalled_ago is None else now - recalled_ago, memory_id),
        )


def test_follow_up_not_due_same_conversation():
    memory.add_memory("follow_up", "спросить про колено", owner="elder", status="open")
    assert memory.due_follow_ups() == []  # created just now → not due yet


def test_follow_up_due_later_then_auto_closes():
    fid = memory.add_memory("follow_up", "спросить про письмо", owner="elder", status="open")
    _backdate(fid, created_ago=4 * 3600)  # 4h ago → due
    due = memory.due_follow_ups()
    assert due and due[0]["content"] == "спросить про письмо"

    memory.surface_follow_up(fid)              # 1st raise
    _backdate(fid, created_ago=4 * 3600, recalled_ago=13 * 3600)  # clear cooldown
    memory.surface_follow_up(fid)              # 2nd raise → auto-close
    with db.connect() as conn:
        row = conn.execute("SELECT status, recall_count FROM memories WHERE id=?", (fid,)).fetchone()
    assert row["status"] == "done" and row["recall_count"] >= 2


def test_latest_mood():
    memory.add_memory("mood", "спокойное", owner="elder")
    time.sleep(0.01)
    memory.add_memory("mood", "бодрое", owner="elder")
    assert memory.latest_mood() == "бодрое"


def test_build_memory_context_assembles(monkeypatch):
    memory.add_memory("story", "Рассказал про войну", owner="elder", title="Война")
    memory.add_memory("mood", "задумчивое", owner="elder")
    monkeypatch.setattr(embeddings, "available", lambda: False)
    ctx = asyncio.run(memory.build_memory_context("s1", ""))
    assert "Война" in ctx and "задумчивое" in ctx
