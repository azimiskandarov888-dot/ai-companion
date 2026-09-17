"""Learning: the extraction captures everything important, distilled short."""

from __future__ import annotations

from app import learn


def test_extraction_covers_key_memory_categories():
    p = learn._EXTRACTION_SYSTEM
    # Everything the family asked Bob to remember about the elder.
    for word in ("семью", "здоровье", "планы", "даты", "истории", "переживает"):
        assert word in p


def test_extraction_distills_not_verbatim():
    p = learn._EXTRACTION_SYSTEM
    # It must store the MEANING short, in its own words — never word-for-word.
    assert "своими словами" in p
    assert "НЕ слово в слово" in p


# --------------------------------------------------------------------------- #
# The module actually running
# --------------------------------------------------------------------------- #
#
# Everything above this line asserts that Russian words appear in a prompt
# string. Mutation-tested, that left the whole module undefended: making
# `learn_from_exchange` a no-op, and `_parse_json` return `{}` always, both
# left the suite green — the only entry point could be deleted and nothing
# noticed. These tests drive the real function with the model stubbed.

import asyncio
import json

import pytest

from app import config, db, embeddings, feeling, memory, mood


@pytest.fixture(autouse=True)
def _fresh(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(embeddings, "available", lambda: False)
    db.init_db()
    yield


def _answers(monkeypatch, payload) -> dict:
    """Make the extractor's one model call return exactly this."""
    seen: dict = {}

    class _Block:
        type = "text"
        def __init__(self, text): self.text = text

    class _Message:
        def __init__(self, text): self.content = [_Block(text)]

    class _Messages:
        async def create(self, **kw):
            seen.update(kw)
            return _Message(payload if isinstance(payload, str)
                            else json.dumps(payload, ensure_ascii=False))

    class _Client:
        messages = _Messages()

    monkeypatch.setattr(learn, "_get_client", lambda: _Client())
    return seen


def _learn(user, said="я вчера ходил к врачу", replied="и как, что сказал?"):
    """One exchange, read now. A goodbye closes the batch whatever its size,
    which is what lets every test below stay about extraction rather than
    about when the batch happens to fill."""
    memory.log_turn(user, "user", said)
    memory.log_turn(user, "assistant", replied)
    asyncio.run(learn.learn_from_conversation(user, farewell=True))


def test_a_whole_exchange_lands_in_memory(monkeypatch):
    _answers(monkeypatch, {
        "facts": [{"category": "семья", "value": "дочь Валя, живёт в Твери"}],
        "stories": [{"title": "Рыбалка", "summary": "Ходил с отцом на Волгу."}],
        "health": ["ноет колено"],
        "mood": {"word": "устал", "energy": -1, "warmth": 0, "lightness": -1,
                 "clarity": 0, "engagement": 0, "note": "говорит тише обычного",
                 "because": "«да ничего»"},
        "observed": [{"tag": "ушёл_от_вопроса", "subject": "здоровье"}],
        "bob": {"valence": 1, "arousal": 0, "note": "посмеялись про рыбалку"},
        "follow_ups": ["спросить, что сказал врач"],
        "bob_facts": ["у Боба есть кот Мурзик"],
    })
    _learn("u")

    assert "дочь Валя" in memory.facts_context("u")
    assert "Мурзик" in memory.bob_self_context("u")
    assert memory.due_follow_ups("u", limit=5) is not None
    assert mood.recent("u") and mood.recent("u")[0]["word"] == "устал"
    assert feeling.now("u")["note"] == "посмеялись про рыбалку"
    with db.connect() as conn:
        tags = [r["tag"] for r in conn.execute(
            "SELECT tag FROM observations WHERE user_id='u'")]
    assert tags == ["ушёл_от_вопроса"]


def test_what_the_extractor_is_shown(monkeypatch):
    """It must be given what is already known, or it re-writes the same facts
    every turn — and the topics already named, or «война» and «про войну» are
    two truths that each wait forever to reach two."""
    memory.add_memory("u", "fact", "семья: дочь Валя")
    mood.observe("u", "закрылся_на_теме", "война")
    seen = _answers(monkeypatch, {})
    _learn("u")

    prompt = seen["messages"][0]["content"]
    assert "дочь Валя" in prompt
    assert "«война»" in prompt
    assert "буква в букву" in prompt
    assert "я вчера ходил к врачу" in prompt


def test_a_broken_model_never_breaks_the_turn(monkeypatch):
    class _Boom:
        class messages:
            @staticmethod
            async def create(**kw):
                raise RuntimeError("провайдер прилёг")

    monkeypatch.setattr(learn, "_get_client", lambda: _Boom())
    _learn("u")                                   # must not raise
    assert memory.facts_context("u") == ""


@pytest.mark.parametrize("raw", [
    "", "не знаю", "{", '{"facts":', "[]", '["facts"]', "null",
])
def test_garbage_is_read_as_nothing_learned(monkeypatch, raw):
    _answers(monkeypatch, raw)
    _learn("u")
    assert memory.facts_context("u") == ""


def test_a_fenced_answer_is_still_read(monkeypatch):
    """The tolerance in _parse_json had no coverage at all, and a model that
    starts fencing its JSON would have silently stopped the app learning."""
    _answers(monkeypatch, '```json\n{"facts":[{"category":"семья","value":"сын Пётр"}]}\n```')
    _learn("u")
    assert "сын Пётр" in memory.facts_context("u")


def test_prose_around_the_json_is_tolerated(monkeypatch):
    _answers(monkeypatch, 'Вот что я вынес: {"facts":[{"category":"быт","value":"живёт один"}]} — всё.')
    _learn("u")
    assert "живёт один" in memory.facts_context("u")


def test_nothing_is_learned_without_a_key(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")

    def boom():
        raise AssertionError("the extractor must not be called without a key")

    monkeypatch.setattr(learn, "_get_client", boom)
    _learn("u")


def test_an_invented_tag_is_dropped_but_the_rest_of_the_answer_survives(monkeypatch):
    _answers(monkeypatch, {
        "observed": [{"tag": "он_грустный_потому_что_осень"},
                     {"tag": "поднял_юмор"}],
        "facts": [{"category": "быт", "value": "держит кур"}],
    })
    _learn("u")
    with db.connect() as conn:
        tags = [r["tag"] for r in conn.execute(
            "SELECT tag FROM observations WHERE user_id='u'")]
    assert tags == ["поднял_юмор"]
    assert "держит кур" in memory.facts_context("u")


def test_what_stopped_being_true_is_retired(monkeypatch):
    """The worst thing this app can do is ask how a dead wife is doing."""
    memory.add_memory("u", "fact", "семья: жена Валя")
    numbered = memory.believes("u")
    fact_id = int(numbered.split("]")[0].lstrip("["))

    _answers(monkeypatch, {"no_longer_true": [{"id": fact_id, "because": "«Валя умерла весной»"}]})
    _learn("u")
    assert "жена Валя" not in memory.facts_context("u")


def test_two_people_never_share_what_was_learned(monkeypatch):
    _answers(monkeypatch, {"facts": [{"category": "семья", "value": "внук Саша"}]})
    _learn("анна")
    assert "внук Саша" in memory.facts_context("анна")
    assert memory.facts_context("борис") == ""


# ── when the batch closes ──────────────────────────────────────────────────

def _say(user, n: int) -> None:
    for i in range(n):
        memory.log_turn(user, "user", f"реплика {i}")
        memory.log_turn(user, "assistant", f"ответ {i}")


def test_a_batch_does_not_close_before_it_is_full(monkeypatch):
    """The whole point: the extractor stops running on every single exchange.
    At about a third of what a conversation costs it was the most expensive
    thing in one, and it was also the worst extraction available — one
    exchange is almost nothing to judge what is worth remembering from."""
    _answers(monkeypatch, {})
    user = "batch-a"
    _say(user, learn.BATCH_EXCHANGES - 1)
    assert learn.unread(user) == []


def test_a_full_batch_closes(monkeypatch):
    _answers(monkeypatch, {})
    user = "batch-b"
    _say(user, learn.BATCH_EXCHANGES)
    rows = learn.unread(user)
    assert len(rows) == learn.BATCH_EXCHANGES * 2
    assert rows[0]["content"] == "реплика 0", "старейшее первым — это порядок чтения"


def test_a_goodbye_closes_a_batch_of_any_size(monkeypatch):
    """There may be no next turn to close it on. Everything said in a short
    visit would otherwise be learned only if he happened to come back."""
    _answers(monkeypatch, {})
    user = "batch-c"
    _say(user, 1)
    assert learn.unread(user) == []
    assert len(learn.unread(user, farewell=True)) == 2


def test_a_slow_talker_does_not_have_his_visit_cut_in_half(monkeypatch):
    """The batch cannot be a count alone. Each run writes ONE mood reading,
    and mood._visits cuts readings into visits wherever two fall more than
    CONVERSATION_GAP apart — so five exchanges spanning eleven minutes would
    have one visit counted as two, and the visit is the unit the whole
    baseline rests on. Time closes the batch before that can happen."""
    _answers(monkeypatch, {})
    user = "batch-d"
    _say(user, 2)
    assert learn.unread(user) == [], "рано"

    with db.connect() as conn:                      # два обмена, но давно
        conn.execute(
            "UPDATE turns SET ts = ts - ? WHERE user_id=?",
            (learn.BATCH_SECONDS + 1, user),
        )
    assert len(learn.unread(user)) == 4
    assert learn.BATCH_SECONDS < mood.CONVERSATION_GAP, "иначе визит всё равно порвётся"


def test_a_batch_is_read_once_and_never_again(monkeypatch):
    _answers(monkeypatch, {"facts": [{"category": "семья", "value": "дочь Валя"}]})
    user = "batch-e"
    _say(user, learn.BATCH_EXCHANGES)
    asyncio.run(learn.learn_from_conversation(user))
    assert learn.unread(user, farewell=True) == [], "пачка прочитана дважды"

    # …and the next exchange starts a fresh one rather than re-reading.
    _say(user, 1)
    assert len(learn.unread(user, farewell=True)) == 2


def test_a_failed_extraction_keeps_the_batch_for_the_next_turn(monkeypatch):
    """A provider having a bad minute must cost a delay, never a memory."""
    user = "batch-f"
    _say(user, learn.BATCH_EXCHANGES)

    class _Boom:
        class messages:
            @staticmethod
            async def create(**kw):
                raise RuntimeError("провайдер лёг")

    monkeypatch.setattr(learn, "_get_client", lambda: _Boom())
    asyncio.run(learn.learn_from_conversation(user))
    assert len(learn.unread(user)) == learn.BATCH_EXCHANGES * 2, "пачка потеряна"
