"""Memory: owner isolation, facts, semantic recall, resurfacing, follow-ups."""

from __future__ import annotations

import asyncio
import json
import time

from app import config, db, embeddings, memory

#: The person these tests are about. Every memory call names whose it is.
U = "u1"


def test_owner_isolation():
    memory.add_memory(U, "fact", "семья: внук Алёша", owner="elder")
    memory.add_memory(U, "fact", "живёт у моря", owner="bob")

    elder = memory.facts_context(U, "elder")
    bob = memory.bob_self_context(U)

    assert "внук Алёша" in elder and "у моря" not in elder
    assert "у моря" in bob and "внук Алёша" not in bob


def test_add_memory_dedup():
    first = memory.add_memory(U, "fact", "любит уху", owner="elder")
    dup = memory.add_memory(U, "fact", "любит уху", owner="elder")
    # Same content for a DIFFERENT owner is allowed.
    other = memory.add_memory(U, "fact", "любит уху", owner="bob")
    assert first is not None and dup is None and other is not None


def test_seed_facts_from_file():
    (config.DATA_DIR / "facts.json").write_text(
        json.dumps({"Имя": "Иван", "Любит": ["чай", "песни"]}, ensure_ascii=False),
        encoding="utf-8",
    )
    added = memory.seed_facts_from_file(U)
    assert added == 2
    facts = memory.facts_context(U, "elder")
    assert "Иван" in facts and "чай, песни" in facts
    # Idempotent — re-seeding adds nothing.
    assert memory.seed_facts_from_file(U) == 0


def test_semantic_recall_orders_by_relevance(monkeypatch):
    memory.add_memory(U, "story", "Ловил рыбу на реке", owner="elder",
                      title="Рыбалка", embedding=[1.0, 0.0, 0.0])
    memory.add_memory(U, "story", "Танцевал на свадьбе", owner="elder",
                      title="Свадьба", embedding=[0.0, 1.0, 0.0])

    async def fake_embed(text):
        return [0.95, 0.05, 0.0]  # close to the fishing story

    monkeypatch.setattr(embeddings, "available", lambda: True)
    monkeypatch.setattr(embeddings, "embed", fake_embed)

    picked = asyncio.run(memory.recall_relevant(U, "расскажи про рыбалку", k=2))
    assert picked and picked[0]["title"] == "Рыбалка"


def test_recall_falls_back_to_recency_without_embeddings(monkeypatch):
    memory.add_memory(U, "story", "старая история", owner="elder", title="A")
    memory.add_memory(U, "story", "новая история", owner="elder", title="B")
    monkeypatch.setattr(embeddings, "available", lambda: False)
    picked = asyncio.run(memory.recall_relevant(U, "что угодно", k=1))
    assert picked and picked[0]["title"] == "B"  # most recent


def test_resurface_returns_a_story():
    memory.add_memory(U, "story", "тёплый момент", owner="elder", title="Момент")
    r = memory.resurface(U)
    assert r is not None and r["title"] == "Момент"


def _backdate(memory_id: int, created_ago: float, recalled_ago: float | None = None):
    now = time.time()
    with db.connect() as conn:
        conn.execute(
            "UPDATE memories SET created_ts=?, last_recalled_ts=? WHERE id=?",
            (now - created_ago, None if recalled_ago is None else now - recalled_ago, memory_id),
        )


def test_follow_up_not_due_same_conversation():
    memory.add_memory(U, "follow_up", "спросить про колено", owner="elder", status="open")
    assert memory.due_follow_ups(U) == []  # created just now → not due yet


def test_follow_up_due_later_then_auto_closes():
    fid = memory.add_memory(U, "follow_up", "спросить про письмо", owner="elder", status="open")
    _backdate(fid, created_ago=4 * 3600)  # 4h ago → due
    due = memory.due_follow_ups(U)
    assert due and due[0]["content"] == "спросить про письмо"

    memory.surface_follow_up(U, fid)              # 1st raise
    _backdate(fid, created_ago=4 * 3600, recalled_ago=13 * 3600)  # clear cooldown
    memory.surface_follow_up(U, fid)              # 2nd raise → auto-close
    with db.connect() as conn:
        row = conn.execute("SELECT status, recall_count FROM memories WHERE id=?", (fid,)).fetchone()
    assert row["status"] == "done" and row["recall_count"] >= 2


def test_latest_mood():
    memory.add_memory(U, "mood", "спокойное", owner="elder")
    time.sleep(0.01)
    memory.add_memory(U, "mood", "бодрое", owner="elder")
    assert memory.latest_mood(U) == "бодрое"


def test_build_memory_context_assembles(monkeypatch):
    memory.add_memory(U, "story", "Рассказал про войну", owner="elder", title="Война")
    memory.add_memory(U, "mood", "задумчивое", owner="elder")
    monkeypatch.setattr(embeddings, "available", lambda: False)
    ctx = asyncio.run(memory.build_memory_context(U, ""))
    assert "Война" in ctx and "задумчивое" in ctx


# --------------------------------------------------------------------------- #
# Two people on one server
# --------------------------------------------------------------------------- #
V = "u2"


def test_nothing_leaks_between_two_people(monkeypatch):
    """The bug this whole layer exists to make impossible.

    Every read path is checked in one test on purpose: a leak is not a feature
    that degrades, it is a stranger reading somebody's life, and it only takes
    ONE unscoped query to happen. If a future edit drops a `WHERE user_id=?`
    anywhere, this fails.
    """
    monkeypatch.setattr(embeddings, "available", lambda: False)

    memory.add_memory(U, "fact", "внучка Настя", owner="elder")
    memory.add_memory(U, "story", "как он строил дом", owner="elder", title="Дом")
    memory.add_memory(U, "mood", "тихое", owner="elder")
    memory.add_memory(U, "fact", "он плотник", owner="bob")
    memory.log_turn(U, "user", "здравствуй")

    memory.add_memory(V, "fact", "сын Марат", owner="elder")
    memory.add_memory(V, "story", "как он водил трамвай", owner="elder", title="Трамвай")
    memory.add_memory(V, "mood", "бодрое", owner="elder")
    memory.add_memory(V, "fact", "он вагоновожатый", owner="bob")
    memory.log_turn(V, "user", "привет")

    assert "Настя" in memory.facts_context(U, "elder")
    assert "Марат" not in memory.facts_context(U, "elder")
    assert "плотник" in memory.bob_self_context(U)
    assert "вагоновожатый" not in memory.bob_self_context(U)

    assert memory.latest_mood(U) == "тихое"
    assert memory.latest_mood(V) == "бодрое"

    assert memory.resurface(U)["title"] == "Дом"
    assert memory.resurface(V)["title"] == "Трамвай"

    recalled = asyncio.run(memory.recall_relevant(U, "дом"))
    assert [r["title"] for r in recalled] == ["Дом"]

    assert [t["content"] for t in memory.recent_turns(U)] == ["здравствуй"]
    assert [t["content"] for t in memory.recent_turns(V)] == ["привет"]

    assert memory.counts(U, "elder") == {"fact": 1, "story": 1, "mood": 1}
    assert memory.counts(U, "bob") == {"fact": 1}


def test_same_words_from_two_people_are_two_memories():
    """Dedup is per person. Two lonely people both saying they miss their wife
    is two memories, not one — the second must not be swallowed as a duplicate
    of the first."""
    a = memory.add_memory(U, "fact", "скучает по жене", owner="elder")
    b = memory.add_memory(V, "fact", "скучает по жене", owner="elder")
    assert a is not None and b is not None and a != b


def test_starting_over_touches_only_that_person():
    """«Начать заново» used to be three DELETEs with no WHERE — one person
    meeting a new friend wiped every conversation on the server."""
    memory.add_memory(U, "fact", "внучка Настя", owner="elder")
    memory.add_memory(U, "fact", "он плотник", owner="bob")
    memory.log_turn(U, "user", "здравствуй")
    memory.add_memory(V, "fact", "сын Марат", owner="elder")
    memory.add_memory(V, "fact", "он вагоновожатый", owner="bob")
    memory.log_turn(V, "user", "привет")

    memory.forget_companion(U)

    # U's friend is gone, and their own history with him.
    assert memory.bob_self_context(U) == ""
    assert memory.recent_turns(U) == []
    # …but what U said about THEMSELVES survives — still true of them.
    assert "Настя" in memory.facts_context(U, "elder")
    # …and V never noticed a thing.
    assert "вагоновожатый" in memory.bob_self_context(V)
    assert [t["content"] for t in memory.recent_turns(V)] == ["привет"]
