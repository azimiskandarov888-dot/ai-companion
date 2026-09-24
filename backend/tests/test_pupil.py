"""The friend as a pupil — owner's decision, 2026-09-24.

In the person's own strength the friend starts with little or nothing and
badly wants to become a master, and the person teaches him. «Видеть, как к
тебе пришли не зная ничего, а затем стали профессионалом из-за тебя самого —
лучшее чувство.»

Why it is built as a mechanism and not as a sentence. The effect it rests on
is real and large — people work harder for someone they teach than for
themselves (the protégé effect, Chase et al. 2009); older adults who stop
feeling useful to others die sooner (Gruenewald et al., MacArthur Study); a
partner who helps you become who you want to be is the one you keep (the
Michelangelo phenomenon, Drigotas & Rusbult 1999). But it has one boundary
condition that decides everything: labour turns into love only when it ends
in success (the IKEA effect, Norton, Mochon & Ariely 2012). A pupil who is a
beginner forever is labour that went nowhere. And a model cannot remember
last Tuesday's lesson — so the lessons are written down by the scribe and
handed back to him, and his progress is made of what he was actually taught.
"""

from __future__ import annotations

import asyncio
import inspect

import pytest

from app import companion, config, db, embeddings, erase, learn, main, memory, persona, young

U = "pupil-user"


@pytest.fixture(autouse=True)
def _fresh(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(embeddings, "available", lambda: False)
    db.init_db()
    yield


def _taught(*lessons: str) -> None:
    asyncio.run(learn._store(U, {"taught_bob": list(lessons)}))


def test_he_arrives_as_a_pupil_on_the_persons_ground():
    block = persona.build_persona_block(
        {"name": "Айлен", "wants_to_learn": "писать код — пока ноль, но очень хочет"})
    assert "писать код — пока ноль" in block
    assert "учит тебя ОН" in block
    assert "дорасти до мастера" in block


def test_the_scribe_writes_down_what_he_was_taught():
    assert '"taught_bob"' in learn._EXTRACTION_SYSTEM
    _taught("цикл for повторяет действие для каждого элемента")
    assert "цикл for" in memory.lessons_block(U)


def test_nothing_taught_is_nothing_in_the_prompt():
    assert memory.lessons_block(U) == ""


def test_he_grows_and_the_prompt_says_how_far():
    """The count is what lets the oldest lessons fall out of the prompt without
    him seeming to have forgotten everything: «уроков от него: 40» says a
    great deal more than the last dozen lines do on their own."""
    _taught(*(f"урок номер {i}, про очередную штуку в программировании" for i in range(40)))
    block = memory.lessons_block(U)
    assert "уроков от него: 40" in block
    assert "урок номер 39" in block                 # the newest is always there
    assert "урок номер 0," not in block             # the oldest fell out of the budget
    assert len(block) < memory.LESSONS_BUDGET + 600
    # Newest last, so they read in the order he learned them.
    assert block.index("урок номер 38") < block.index("урок номер 39")
    # Success, not only effort — the IKEA boundary — and gratitude, not a hook.
    assert "У тебя правда получается" in block
    assert "помни, от кого это у тебя" in block


def test_it_rides_with_the_rest_of_him_in_the_uncached_half():
    """The scribe adds to it mid-conversation, so the stable half — which must
    be byte-identical turn to turn — cannot carry it."""
    _taught("как устроен git commit")
    stable, variable = companion.build_system_parts(lessons_block=memory.lessons_block(U))
    assert "git commit" in variable and "git commit" not in stable
    assert stable == companion.build_system_parts()[0]
    assert "lessons_block=memory.lessons_block(user_id)" in inspect.getsource(main)


def test_a_new_friend_does_not_arrive_knowing_the_last_ones_lessons():
    _taught("как устроен git commit")
    erase.the_companion(U)
    assert memory.lessons_block(U) == ""


def test_a_childs_lessons_are_kept_no_more_than_anything_else_of_theirs():
    """His row, but the child's words — and nothing a child says is kept."""
    _taught("как строить редстоун-схемы")
    young.forget(U)
    assert memory.lessons_block(U) == ""


def test_he_notices_the_person_growing_too():
    """The same effect facing the other way, and the one the owner called the
    most important: change for the better, thanks to somebody. The Michelangelo
    phenomenon (Drigotas & Rusbult 1999) — a close other who sees and affirms
    your movement toward who you want to be is how that movement happens. The
    constitution told him to notice change only when it was for the worse."""
    rules = companion.BEHAVIOR_RULES
    assert "И перемену к лучшему тоже: решился, смог, вырос в чём-то" in rules
    # It is where praise is actually earned — not a licence to praise.
    assert "это правда стоит похвалы" in rules
