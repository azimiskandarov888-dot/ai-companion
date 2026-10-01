"""How a sentence sounds said, not written (aloud.py).

The owner, 2026-09-30: too perfect is fake — «это не эссе… это живой разговор,
где должны быть ошибки, запинания, слова-паразиты». Asked in every way we
tried, the voice still wrote clean prose; so the small imperfections of speech
are put in where a speaker makes them. What is pinned here: WHERE they go, HOW
MANY, where they never go — and (in test_live, test_streaming) that only the
voice gets them, while what is remembered stays as he meant it.
"""

from __future__ import annotations

import random
import re
from pathlib import Path

import pytest

from app import aloud


@pytest.fixture(autouse=True)
def on(monkeypatch):
    """conftest turns the chance off for every other test; here it is certain."""
    monkeypatch.setattr(aloud, "CHANCE", 1.0)


def _every(piece: str, before: str | None = None, tries: int = 300) -> set[str]:
    """Everything the layer ever makes of `piece` — as a reply's first piece,
    or after `before`."""
    seen = set()
    for seed in range(tries):
        speaker = aloud.Speaker(random.Random(seed))
        if before is not None:
            speaker.say(before)
        seen.add(speaker.say(piece))
    return seen


# ── where they go ──────────────────────────────────────────────────────────

def test_a_hedge_or_a_pause_goes_before_the_vague_word_he_reaches_for():
    """Hesitations gather before what is hard to plan (Maclay & Osgood 1959;
    Clark & Fox Tree 2002) — the vague word said when the exact one is not
    there yet."""
    piece = "Мне это всегда казалось каким-то фокусом, если честно."
    assert _every(piece) == {
        "Мне это всегда казалось, ну, каким-то фокусом, если честно.",
        "Мне это всегда казалось как бы каким-то фокусом, если честно.",
        "Мне это всегда казалось, я не знаю, каким-то фокусом, если честно.",
        "Мне это всегда казалось… каким-то фокусом, если честно.",
    }


def test_an_either_or_question_gets_its_vague_there_and_nothing_after_the_or():
    piece = "А ты сам учишься или кто-то помогает тебе с этим?"
    assert _every(piece) == {"А ты сам учишься или там кто-то помогает тебе с этим?"}


def test_he_restarts_or_holds_the_floor_as_he_begins_on_himself():
    assert "О, плов. Я… я бы, наверное, с рисом всё испортил в первый же раз." in _every(
        "О, плов. Я бы, наверное, с рисом всё испортил в первый же раз.")
    assert "О, Ташкент. Я вот там никогда не был, но город представляю тёплым." in _every(
        "О, Ташкент. Я там никогда не был, но город представляю тёплым.")
    # «Я вот бы» is not Russian.
    assert not any("Я вот бы" in s for s in _every("О, плов. Я бы с рисом всё испортил сразу же."))


def test_a_long_sentence_pauses_where_its_next_clause_is_planned():
    piece = "Я на пианино вообще не умею, даже простую мелодию не сыграл бы."
    assert "Я на пианино вообще не умею, ну, даже простую мелодию не сыграл бы." in _every(
        piece, before="Ого.")


# ── where they never go ────────────────────────────────────────────────────

def test_the_reply_opens_whole():
    """His first word is never a stumble: the reaction comes first."""
    piece = "Я тоже так думаю, если честно, хотя и не уверен до конца."
    assert not any(s.startswith(("Я… я", "Я вот")) for s in _every(piece))


def test_never_inside_a_list_after_an_aside_or_before_a_word_that_joins():
    lists = _every("Город я представляю шумный, тёплый, с базарами и садами вокруг.")
    assert not any("шумный, ну, тёплый" in s for s in lists)
    aside = _every("Ничего себе, сам? Я бы, наверное, рис сварил, а с пловом побоялся.")
    assert not any("наверное, ну," in s for s in aside)
    joined = _every("Наверное, там совсем другой ритм, чем у нас у моря летом.")
    assert not any("ритм, ну, чем" in s for s in joined)


def test_where_exactness_matters_he_speaks_plainly_from_there_on():
    warning = "Если звонят из банка и просят код, положи трубку, это обман, слышишь?"
    assert _every(warning) == {warning}
    speaker = aloud.Speaker(random.Random(1))
    speaker.say("Позвони в скорую, номер сто три, прямо сейчас.")
    after = "Я бы на твоём месте сразу позвонил, не откладывая это надолго."
    assert speaker.say(after) == after
    assert _every("Мой номер 8 900 123 45 67, запиши его куда-то себе.") == {
        "Мой номер 8 900 123 45 67, запиши его куда-то себе."}


def test_a_short_piece_is_left_as_it_is():
    assert _every("Ой. Сильно ударился?") == {"Ой. Сильно ударился?"}


def test_his_markers_are_never_broken_into():
    piece = "Кхм //КАШЕЛЬ// мне это казалось каким-то фокусом всегда."
    assert all("//КАШЕЛЬ//" in s for s in _every(piece))


# ── how many ───────────────────────────────────────────────────────────────

REPLIES = [
    "О, программирование — это мне всегда казалось каким-то фокусом. Сам учишься или кто-то помогает?",
    "Ничего себе, сам? Я бы, наверное, рис сварил, а с пловом побоялся бы возиться.",
    "О, пианино. Я бы, наверное, долго искал нужную клавишу. Ты давно учишься?",
    "Ох, тогда тебе бы сейчас просто сесть и выдохнуть. После таких дней даже разговаривать лень.",
    "Ой, бедная кошка… Хорошо, что ты отвёз её к ветеринару. Что он сказал?",
    "О, Ташкент… Я там никогда не был, но город почему-то представляется очень солнечным.",
    "О, значит, день не зря прошёл. Я в футболе так себе, обычно мяч теряю быстрее всех.",
    "Ага, спокойный день. Я после магазина обычно сразу ставлю чайник, а потом смотрю что-нибудь.",
]
_MARKS = ("ну, ", "как бы ", "я не знаю, ", "… ", "или там ", "Я… я", "Я вот", "Ну, ")


def _added(before: str, after: str) -> list[str]:
    return [m for m in _MARKS for _ in range(after.count(m) - before.count(m))]


def test_about_one_a_reply_never_more_than_two_never_the_same_twice(monkeypatch):
    """People make about six in a hundred words (Bortfeld et al. 2001); a
    machine that stumbles in every sentence is caught «trying too hard»
    (Jones & Bergen 2023). At the chance shipped — measured on 650 of the
    voice's own replies at about seven in ten a reply."""
    shipped = float(re.search(r"^CHANCE = ([0-9.]+)", Path(aloud.__file__).read_text(), re.M).group(1))
    monkeypatch.setattr(aloud, "CHANCE", shipped)
    rng = random.Random(5)
    added = [_added(r, aloud.said(r, rng)) for _ in range(40) for r in REPLIES]
    assert all(len(a) <= aloud.MAX_PER_REPLY for a in added)
    assert all(len(set(a)) == len(a) for a in added)
    average = sum(map(len, added)) / len(added)
    assert 0.5 <= average <= 1.2, average
    assert sum(1 for a in added if not a) >= len(added) // 5       # and often none at all


def test_a_whole_reply_said_at_once_keeps_its_shape(monkeypatch):
    """The path that voices a reply whole (not streamed) says it sentence by
    sentence, like the pieces of a streamed one — every space kept."""
    text = "Ого.  Сам учишься или кто-то помогает?\nДавно?"
    assert aloud.said(text, random.Random(2)) == "Ого.  Сам учишься или там кто-то помогает?\nДавно?"
    monkeypatch.setattr(aloud, "CHANCE", 0.0)
    assert aloud.said(text, random.Random(2)) == text
