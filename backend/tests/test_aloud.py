"""How a sentence sounds said, not written (aloud.py) — in Russian and English.

The owner, 2026-09-30: too perfect is fake — «это не эссе… это живой разговор,
где должны быть ошибки, запинания, слова-паразиты»; and 2026-10-02: a real
person stalls, repeats words, and has a lot of fillers — «добавь их в
достаточном количестве». What is pinned here: WHERE they go, HOW MANY, where
they never go — and (in test_live, test_streaming) that only the voice gets
them, while what is remembered stays as he meant it.
"""

from __future__ import annotations

import random
import re

import pytest

from app import aloud, config


@pytest.fixture(autouse=True)
def on(monkeypatch):
    """conftest turns the layer off for every other test; here it is on, as shipped."""
    monkeypatch.setattr(aloud, "CHANCE", 1.0)


def _every(piece: str, before: str | None = None, tries: int = 400, young: bool = False) -> set[str]:
    """Everything the layer ever makes of `piece` — as a reply's first piece,
    or after `before`."""
    seen = set()
    for seed in range(tries):
        speaker = aloud.Speaker(random.Random(seed), young=young)
        if before is not None:
            speaker.say(before)
        seen.add(speaker.say(piece))
    return seen


# ── where they go ──────────────────────────────────────────────────────────

def test_a_hedge_or_a_pause_goes_before_the_vague_word_he_reaches_for():
    """Hesitations gather before what is hard to plan (Maclay & Osgood 1959;
    Clark & Fox Tree 2002) — the vague word said when the exact one is not
    there yet."""
    seen = _every("Мне это всегда казалось каким-то фокусом, если честно.")
    for hedge in ("казалось, ну, каким-то", "казалось как бы каким-то",
                  "казалось, я не знаю, каким-то", "казалось… каким-то"):
        assert any(hedge in s for s in seen), hedge


def test_a_filled_pause_goes_before_the_word_he_reaches_for_after_a_little_word():
    seen = _every("Я с тренировки только пришёл, палец ещё болит немного.")
    assert any(re.search(r"\bс (?:э-э|м-м|э)… тренировки", s) for s in seen)


def test_a_clause_opens_twice_on_its_little_word():
    """Repeats sit on the function word that opens a constituent (Clark & Wasow 1998)."""
    seen = _every("Ого. Я тоже так думал, когда только начинал играть.", tries=600)
    assert any("Я… я тоже" in s for s in seen)


def test_an_either_or_question_gets_its_vague_there_and_nothing_after_the_or():
    seen = _every("А ты сам учишься или кто-то помогает тебе с этим?")
    assert any("или там кто-то" in s for s in seen)
    assert not any("или там там" in s for s in seen)


def test_he_holds_the_floor_as_he_begins_on_himself():
    assert any("Я вот там никогда не был" in s for s in _every(
        "О, Ташкент. Я там никогда не был, но город представляю тёплым."))
    # «Я вот бы» is not Russian.
    assert not any("Я вот бы" in s for s in _every("О, плов. Я бы с рисом всё испортил сразу же."))


def test_a_long_sentence_holds_the_floor_where_its_next_clause_is_planned():
    piece = "Я на пианино вообще не умею, даже простую мелодию не сыграл бы."
    assert any(re.search(r"не умею, (?:ну|вот|как бы), даже", s) for s in _every(piece, before="Ого."))


def test_the_young_say_типа_and_короче_and_the_rest_do_not():
    piece = "Играю в баскетбол за районную команду, недавно палец выбил на тренировке."
    young, grown = _every(piece, young=True), _every(piece)
    assert any(re.search(r"\b(?:типа|короче)\b", s) for s in young)
    assert not any(re.search(r"\b(?:типа|короче)\b", s) for s in grown)


# ── where they never go ────────────────────────────────────────────────────

def test_the_reply_opens_whole():
    """His first word is never a stumble: the reaction comes first, and his
    first sound has already been made (first_sound.py)."""
    piece = "Я тоже так думаю, если честно, хотя и не уверен до конца."
    assert not any(s.startswith(("Я… я", "Я вот", "Э", "М-м")) for s in _every(piece))


def test_never_inside_a_list_after_an_aside_or_before_a_word_that_joins():
    lists = _every("Город я представляю шумный, тёплый, с базарами и садами вокруг.")
    assert not any(re.search(r"шумный, (?:ну|вот|как бы|типа), тёплый", s) for s in lists)
    aside = _every("Ничего себе, сам? Я бы, наверное, рис сварил, а с пловом побоялся.")
    assert not any(re.search(r"наверное, (?:ну|вот|как бы),", s) for s in aside)
    assert not any(re.search(r"Я бы, (?:ну|вот|как бы|типа|короче), наверное", s) for s in aside)
    joined = _every("Наверное, там совсем другой ритм, чем у нас у моря летом.")
    assert not any(re.search(r"ритм, (?:ну|вот|как бы), чем", s) for s in joined)


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
    assert _every("А там что?") == {"А там что?"}


def test_his_markers_are_never_broken_into():
    piece = "Кхм //КАШЕЛЬ// мне это казалось каким-то фокусом всегда, если честно."
    assert all("//КАШЕЛЬ//" in s for s in _every(piece))
    assert all(s.count("//") == 2 for s in _every("//СМЕХ// Я с тренировки только пришёл, палец ещё болит."))


def test_a_name_keeps_its_capital_after_a_word_put_before_it():
    seen = _every("Ого, сам? Азим, ты меня удивил, честно говоря, вообще.", tries=600)
    assert not any("азим" in s for s in seen)


# ── how many ───────────────────────────────────────────────────────────────

REPLIES = [
    "О, программирование — это мне всегда казалось каким-то фокусом. Сам учишься или кто-то помогает?",
    "Ничего себе, сам? Я бы, наверное, рис сварил, а с пловом побоялся бы возиться.",
    "О, пианино. Я бы, наверное, долго искал нужную клавишу. Ты давно учишься?",
    "Ох, тогда тебе бы сейчас просто сесть и выдохнуть. После таких дней даже разговаривать лень.",
    "О, Ташкент… Я там никогда не был, но город почему-то представляется очень солнечным.",
    "О, значит, день не зря прошёл. Я в футболе так себе, обычно мяч теряю быстрее всех.",
    "Ага, спокойный день. Я после магазина обычно сразу ставлю чайник, а потом смотрю что-нибудь.",
    "Да тоже ничего. Я с тренировки только пришёл, палец ещё болит.",
]
_WORD = re.compile(r"[А-Яа-яЁёA-Za-z]+")


def _rate(young: bool) -> tuple[float, list[int]]:
    rng = random.Random(5)
    words = events = 0
    per = []
    for _ in range(60):
        for reply in REPLIES:
            speaker = aloud.Speaker(rng, young=young)
            for piece in re.findall(r"[^.!?…]+[.!?…]*\s*", reply):
                speaker.say(piece.rstrip())
            made = aloud.MAX_PER_REPLY - speaker._left
            words += len(_WORD.findall(reply))
            events += made
            per.append(made)
    return 100.0 * events / words, per


def test_about_as_often_as_people_do_and_the_young_more():
    """Six to ten in a hundred words (Fox Tree 1995; Shriberg 2001; Bortfeld et
    al. 2001), and teenagers' «like» on top (Tagliamonte 2005). The layer's
    own share, with the voice's own «…» and «ну» added to it (~3.8)."""
    grown, per = _rate(young=False)
    teen, _ = _rate(young=True)
    assert 4.0 <= grown <= 8.5, grown
    assert grown + 1.0 <= teen <= 11.0, teen
    assert max(per) <= aloud.MAX_PER_REPLY
    assert sum(1 for n in per if n == 0) >= len(per) // 5      # and often none at all


def test_never_the_same_word_twice_in_a_reply_and_two_at_most_in_a_sentence():
    rng = random.Random(9)
    for _ in range(80):
        for reply in REPLIES:
            out = aloud.said(reply, rng, young=True)
            for word in ("типа", "короче", "как бы", "э-э", "м-м"):
                assert out.count(word) <= reply.count(word) + 1, (word, out)


def test_a_whole_reply_said_at_once_keeps_its_shape(monkeypatch):
    """The path that voices a reply whole (not streamed) says it sentence by
    sentence, like the pieces of a streamed one — every space kept."""
    text = "Ого.  Сам учишься или кто-то помогает?\nДавно?"
    monkeypatch.setattr(aloud, "CHANCE", 0.0)
    assert aloud.said(text, random.Random(2)) == text
    monkeypatch.setattr(aloud, "CHANCE", 1.0)
    out = aloud.said(text, random.Random(2))
    assert out.startswith("Ого.  ") and out.endswith("?\nДавно?")


# ── age ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("age, young", [
    ("16", True), ("шестнадцать лет", True), ("twenty-two", True), ("двадцать пять", True),
    ("68", False), ("восемьдесят семь", False), ("сорок один год", False), ("", False),
])
def test_who_counts_as_young(age, young):
    assert aloud.young({"age": age}) is young


# ── English ────────────────────────────────────────────────────────────────

def test_a_russian_conversation_leaves_english_as_written():
    line = "Honestly, I tried drawing pixel art once, and it was way harder than I thought, like every square matters."
    assert _every(line, tries=40) == {line}


@pytest.fixture
def english(monkeypatch):
    monkeypatch.setattr(config, "LANGUAGE", "en")


def test_an_english_conversation_stumbles_in_english(english):
    seen = _every("I tried drawing pixel art once, and it was way harder than I thought, honestly.",
                  young=True)
    assert len(seen) > 1
    assert not any(re.search(r"[А-Яа-яЁё]", s) for s in seen)
    assert any(re.search(r"\b(?:uh|um|like|you know|I mean|honestly)\b", s.replace("honestly.", ""))
               for s in seen)


def test_english_pauses_and_repeats_go_where_speakers_put_them(english):
    seen = _every("It's a platformer, and I do the art myself on weekends.", tries=600)
    assert any(re.search(r"\ba, (?:uh|um), platformer", s) for s in seen)
    assert any("and… and" in s for s in seen) or any("I… I" in s for s in seen)


def test_english_like_is_for_the_young(english):
    piece = "Oh wait, you're making a game? That was really hard for me when I tried it."
    assert not any(re.search(r"\blike\b", s, re.I) for s in _every(piece))
    young = _every(piece, young=True)
    assert any(re.search(r"\blike\b", s, re.I) for s in young)
    assert any("was like really hard" in s for s in young)


def test_an_english_conversation_leaves_russian_as_written(english):
    piece = "Я на пианино вообще не умею, даже простую мелодию не сыграл бы."
    assert _every(piece, tries=40) == {piece}


def test_english_exactness(english):
    warning = "Hang up right now, and don't give them the code from the text, okay?"
    assert _every(warning) == {warning}
