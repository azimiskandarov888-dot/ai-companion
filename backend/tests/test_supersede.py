"""When something stops being true.

The scenario this whole file exists for: a man tells his friend about his wife
Valya. Months later Valya dies, and he says so. Before this existed, the fact
«жена Валя» stayed in memory exactly as it was — because add_memory only ever
skipped exact duplicates and nothing in the codebase could make a fact false.
The companion would have gone on asking how she was. Forever.

Two things are being protected at once here, and they pull in opposite
directions. The present tense must stop reaching him. The woman must not be
erased — the diary is meant to outlive the subscription, and a book that
quietly dropped his wife the week she died would be worse than no book.
"""

from __future__ import annotations

import time

import pytest

from app import db, diary, learn, memory

U = "u"


def _fact(content: str, **kw) -> int:
    fid = memory.add_memory(U, "fact", content, owner="elder", **kw)
    assert fid is not None
    return fid


def _row(memory_id: int):
    with db.connect() as conn:
        return conn.execute(
            "SELECT * FROM memories WHERE id=?", (memory_id,)
        ).fetchone()


# ── the present tense stops ─────────────────────────────────────────────────

def test_a_retired_fact_stops_being_told_to_him():
    fid = _fact("семья: жена Валя")
    assert "Валя" in memory.facts_context(U)

    assert memory.supersede(U, fid, "Валя умерла весной") is True
    assert "Валя" not in memory.facts_context(U)


def test_the_rest_of_his_life_is_untouched():
    keep = _fact("семья: внучка Оля в Москве")
    drop = _fact("семья: жена Валя")
    memory.supersede(U, drop, "умерла")
    context = memory.facts_context(U)
    assert "Оля" in context
    assert "Валя" not in context


def test_a_retired_health_note_stops_coming_back():
    hid = memory.add_memory(U, "health", "болит колено", owner="elder")
    memory.supersede(U, hid, "колено прошло")
    assert memory._rows(U, ("story", "health")) == []


def test_a_retired_story_stops_resurfacing():
    sid = memory.add_memory(U, "story", "как они с Валей ездили на Байкал", owner="elder")
    memory.supersede(U, sid, "")
    assert memory.resurface(U) is None


# ── nothing is ever erased ──────────────────────────────────────────────────

def test_she_is_not_deleted():
    """The bold half of the design. «Жена Валя» does not become FALSE when Valya
    dies — it becomes PAST. She was real and she mattered."""
    fid = _fact("семья: жена Валя")
    memory.supersede(U, fid, "Валя умерла весной")

    row = _row(fid)
    assert row is not None
    assert row["content"] == "семья: жена Валя"
    assert row["superseded_ts"] is not None
    assert row["superseded_why"] == "Валя умерла весной"


def test_what_ended_can_be_read_back():
    a = _fact("семья: жена Валя")
    memory.supersede(U, a, "умерла весной")
    past = memory.past_facts(U)
    assert len(past) == 1
    assert past[0]["content"] == "семья: жена Валя"
    assert "умерла" in past[0]["superseded_why"]


def test_a_live_life_has_no_past():
    _fact("семья: внучка Оля")
    assert memory.past_facts(U) == []


def test_the_diary_still_has_her_but_in_the_past_tense():
    """The book is the one place his life is allowed a past tense. It keeps the
    row and is told to write it as over — the alternative is a diary that
    silently loses people."""
    _fact("семья: внучка Оля")
    fid = _fact("семья: жена Валя")
    memory.supersede(U, fid, "умерла весной")

    notes = diary._notes_text(diary._memory_rows(U))
    assert "Валя" in notes
    assert "прошедшем времени" in notes
    # and the living are not marked
    oli = [ln for ln in notes.splitlines() if "Оля" in ln]
    assert oli and "прошедшем времени" not in oli[0]


# ── the follow-up, which is the trap ────────────────────────────────────────

def test_the_question_about_her_dies_with_her():
    """«Жена Валя» and «спросить, как Валя» are two different rows. Retiring
    only the fact leaves the follow-up open, and due_follow_ups then has the
    companion ask after a dead woman — for up to three weeks, which is how long
    one takes to expire by itself."""
    fid = memory.add_memory(
        U, "follow_up", "спросить, как Валя", owner="elder", status="open"
    )
    with db.connect() as conn:                       # old enough to be due
        conn.execute(
            "UPDATE memories SET created_ts=? WHERE id=?",
            (time.time() - 4 * 3600, fid),
        )
    assert memory.due_follow_ups(U), "precondition: it was about to be asked"

    memory.supersede(U, fid, "Валя умерла")
    assert memory.due_follow_ups(U) == []


def test_the_extractor_is_shown_the_questions_too():
    """It cannot retire what it cannot point at."""
    _fact("семья: жена Валя")
    memory.add_memory(U, "follow_up", "спросить, как Валя", owner="elder", status="open")
    shown = memory.believes(U)
    assert "жена Валя" in shown
    assert "спросить, как Валя" in shown
    assert "собирается спросить" in shown


def test_the_extractor_is_not_shown_what_is_already_over():
    fid = _fact("семья: жена Валя")
    memory.supersede(U, fid, "умерла")
    assert "Валя" not in memory.believes(U)


def test_every_line_the_extractor_sees_carries_a_number():
    _fact("семья: внучка Оля")
    _fact("здоровье: болит колено")
    for line in memory.believes(U).splitlines():
        assert line.startswith("["), line


# ── a fact can come back ────────────────────────────────────────────────────

def test_something_retired_by_mistake_can_return():
    """The duplicate check looks only at LIVE rows on purpose. A daughter who
    comes back, a pain that returns, a retirement that was simply wrong — the
    fact has to be able to be said again, and matching a retired row would
    swallow it silently and forever."""
    fid = _fact("семья: дочь Нина рядом")
    memory.supersede(U, fid, "уехала")
    assert "Нина" not in memory.facts_context(U)

    again = memory.add_memory(U, "fact", "семья: дочь Нина рядом", owner="elder")
    assert again is not None and again != fid
    assert "Нина" in memory.facts_context(U)


def test_a_live_duplicate_is_still_skipped():
    fid = _fact("семья: внучка Оля")
    assert memory.add_memory(U, "fact", "семья: внучка Оля", owner="elder") is None
    assert _row(fid) is not None


# ── it cannot reach past this person ────────────────────────────────────────

def test_one_persons_memory_cannot_be_retired_by_another():
    mine = memory.add_memory("анна", "fact", "семья: муж Пётр", owner="elder")
    assert memory.supersede("борис", mine, "выдумка") is False
    assert "Пётр" in memory.facts_context("анна")


def test_an_id_that_does_not_exist_just_fails():
    assert memory.supersede(U, 999_999, "ничего") is False


def test_retiring_the_same_thing_twice_is_not_a_second_ending():
    fid = _fact("семья: жена Валя")
    assert memory.supersede(U, fid, "умерла весной") is True
    assert memory.supersede(U, fid, "что-то другое") is False
    assert _row(fid)["superseded_why"] == "умерла весной"


def test_a_very_long_reason_is_trimmed():
    fid = _fact("семья: жена Валя")
    memory.supersede(U, fid, "я" * 5000)
    assert len(_row(fid)["superseded_why"]) <= 300


# ── the extractor's side ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_the_extractor_can_end_a_fact():
    fid = _fact("семья: жена Валя")
    await learn._store(
        U, {"no_longer_true": [{"id": fid, "because": "Валя умерла весной"}]}
    )
    assert "Валя" not in memory.facts_context(U)
    assert memory.past_facts(U)[0]["superseded_why"] == "Валя умерла весной"


@pytest.mark.asyncio
async def test_the_whole_thing_end_to_end():
    """What actually happens on the evening he tells his friend."""
    wife = _fact("семья: жена Валя, вместе 51 год")
    ask = memory.add_memory(
        U, "follow_up", "спросить, как Валя себя чувствует", owner="elder", status="open"
    )
    _fact("семья: внучка Оля в Москве")

    await learn._store(
        U,
        {
            "facts": [{"category": "семья", "value": "жена Валя умерла весной"}],
            "no_longer_true": [
                {"id": wife, "because": "Вали не стало весной"},
                {"id": ask, "because": "Вали не стало весной"},
            ],
        },
    )

    now = memory.facts_context(U)
    assert "умерла" in now              # he knows
    assert "вместе 51 год" not in now   # and not the present tense of her
    assert "Оля" in now                 # the rest of his life is intact
    assert memory.due_follow_ups(U) == []
    assert len(memory.past_facts(U)) == 2


@pytest.mark.asyncio
async def test_a_runaway_retires_nothing_at_all():
    """Over the cap NOTHING goes, not the first five. A partial apply would mean
    acting on a batch already known to be wrong; the safe failure is the old
    behaviour — he keeps believing what he believed."""
    ids = [_fact(f"прочее: факт {i}") for i in range(9)]
    await learn._store(
        U, {"no_longer_true": [{"id": i, "because": "всё не так"} for i in ids]}
    )
    assert memory.past_facts(U) == []
    assert len(memory.facts_context(U).splitlines()) == 9


@pytest.mark.asyncio
async def test_a_legitimate_bereavement_is_not_clipped():
    """The cap has to clear the case the mechanism exists for: one death can
    honestly end the person, the question about them, and their health."""
    ids = [
        _fact("семья: жена Валя"),
        _fact("здоровье: у Вали больное сердце"),
        _fact("распорядок: они с Валей гуляют по вечерам"),
    ]
    ids.append(
        memory.add_memory(U, "follow_up", "спросить про Валю", owner="elder", status="open")
    )
    await learn._store(
        U, {"no_longer_true": [{"id": i, "because": "Вали не стало"} for i in ids]}
    )
    assert len(memory.past_facts(U)) == 4


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "claims",
    [
        None,
        [],
        "всё неправда",
        [None],
        ["12"],
        [{}],
        [{"id": None}],
        [{"id": "жена"}],
        [{"because": "нет номера"}],
    ],
)
async def test_nonsense_retires_nothing(claims):
    _fact("семья: внучка Оля")
    await learn._store(U, {"no_longer_true": claims})
    assert "Оля" in memory.facts_context(U)
    assert memory.past_facts(U) == []


@pytest.mark.asyncio
async def test_an_ordinary_exchange_ends_nothing():
    _fact("семья: жена Валя")
    await learn._store(U, {"facts": [{"category": "прочее", "value": "пил чай"}]})
    assert "Валя" in memory.facts_context(U)


# ── the line the prompt has to hold ─────────────────────────────────────────

def test_the_extractor_is_told_not_to_retire_his_biography():
    """The sharpest risk in the whole mechanism. «Работал сварщиком тридцать
    лет» is true forever — the past does not stop being true by being past —
    and a model that retires biography empties a man of his own life."""
    s = learn._EXTRACTION_SYSTEM
    assert "БИОГРАФИЯ" in s
    assert "Прошлое не перестаёт быть правдой оттого, что оно прошло" in s
    assert "Сомневаешься — не ставь" in s
    assert "ПОЧТИ ВСЕГДА ЗДЕСЬ ПУСТОЙ СПИСОК" in s


def test_the_extractor_is_told_the_question_is_a_separate_row():
    assert "это два разных номера" in learn._EXTRACTION_SYSTEM


# ── the upgrade, for people who were already using it ───────────────────────

def test_a_database_from_before_this_existed_upgrades_and_loses_nothing():
    """Somebody has been talking to their friend for months. The columns this
    feature needs did not exist when their memories were written, and an upgrade
    that dropped a row — or worse, quietly marked one as over — would take part
    of their life with it."""
    with db.connect() as conn:
        conn.execute("DROP TABLE memories")
        conn.execute(
            """
            CREATE TABLE memories (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id           TEXT NOT NULL DEFAULT 'default',
                owner             TEXT NOT NULL DEFAULT 'elder',
                kind              TEXT NOT NULL,
                title             TEXT,
                content           TEXT NOT NULL,
                importance        INTEGER DEFAULT 1,
                status            TEXT DEFAULT 'open',
                embedding         TEXT,
                meta              TEXT,
                created_ts        REAL NOT NULL,
                last_recalled_ts  REAL,
                recall_count      INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            "INSERT INTO memories(user_id, owner, kind, content, created_ts)"
            " VALUES (?,?,?,?,?)",
            (U, "elder", "fact", "семья: жена Валя", time.time()),
        )

    db.init_db()                                  # the upgrade

    # everything he had is still his, and still true
    assert "Валя" in memory.facts_context(U)
    assert memory.past_facts(U) == []
    row = _row(1)
    assert row["superseded_ts"] is None

    # and the new machinery works on his old rows
    assert memory.supersede(U, 1, "умерла весной") is True
    assert "Валя" not in memory.facts_context(U)
    assert len(memory.past_facts(U)) == 1


def test_the_upgrade_runs_twice_without_doing_anything_the_second_time():
    _fact("семья: внучка Оля")
    db.init_db()
    db.init_db()
    assert "Оля" in memory.facts_context(U)
