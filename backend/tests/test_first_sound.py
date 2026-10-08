"""His first sound (first_sound.py): at once, the right one, never twice in a
row of his words, never remembered. The live channel's side of it is pinned in
test_live.py."""

from __future__ import annotations

import array
import asyncio
import random

import pytest

from app import first_sound, tts


@pytest.mark.parametrize("said, kind", [("Я сегодня в школе был.", "statement"),
                                        ("Да нормально всё.", "statement"),
                                        ("Короче, я прихожу в школу, а там,", "statement"),
                                        ("А ты откуда?", "question")])
def test_a_finished_turn_is_told_by_what_was_said(said, kind):
    assert first_sound.at_end(said) == kind


@pytest.mark.parametrize("said", ["А ты как думаешь, стоит идти?", "Почему так вышло, как считаешь?",
                                  "Что лучше взять, как по-твоему?"])
def test_something_to_weigh_gets_a_thinking_sound(said):
    """«Хм…» before «Из Алматы» would be a man pondering where he is from: only
    a question that asks him to weigh something gets one."""
    assert first_sound.at_end(said) == "thinking"


@pytest.mark.parametrize("said", ["Ладно, пока!", "Ну давай, до завтра.", "Мне пора.", "", "   "])
def test_a_goodbye_or_nothing_gets_no_sound(said):
    assert first_sound.at_end(said) is None


def test_a_pause_is_filled_only_once_they_have_begun():
    assert not first_sound.in_pause("я сегодня")
    assert first_sound.in_pause("я сегодня в школу пришёл")
    assert not first_sound.in_pause("ну ладно давай пока")


@pytest.mark.parametrize("piece, sound, said", [
    ("Хм, ну я не знаю.", "Хм…", "Ну я не знаю."),
    ("Так, слушай…", "Так…", "Слушай…"),
    ("М-м, понятно.", "М-м…", "Понятно."),
    ("Мм.", "М-м…", ""),
    ("Хорошо.", "Хм…", "Хорошо."),
    ("Ого, сам?", "М-м…", "Ого, сам?"),
    ("Ого, сам?", "", "Ого, сам?"),
])
def test_his_words_do_not_say_the_sound_again(piece, sound, said):
    assert first_sound.without_repeat(piece, sound) == said


def _pcm(samples: list[int]) -> bytes:
    return array.array("h", samples).tobytes()


def test_the_silence_around_a_sound_is_cut_and_the_ends_fade():
    rate = 1000
    sound = _pcm([0] * 500 + [10000] * 300 + [0] * 500)
    cut = array.array("h")
    cut.frombytes(first_sound.trimmed(sound, rate))
    edge = int(rate * first_sound._EDGE)
    assert len(cut) == 300 + 2 * edge          # the sound, and a breath of margin
    assert cut[0] == 0 and cut[-1] == 0          # no click
    assert max(cut) == 10000
    assert first_sound.trimmed(_pcm([0] * 100), rate) == b""


def test_a_breath_is_kept_only_short_and_quiet_and_made_again_when_not(monkeypatch):
    """Measured 2026-10-08: most takes of <breath> a quiet half-second, but one
    23 s long and at full volume. Such a take is made again."""
    takes = iter([[0] * 10 + [32000] * 600 + [0] * 10,      # loud: not a breath
                  [0] * 10 + [3000] * 5000 + [0] * 10,      # five seconds: not a breath
                  [0] * 10 + [3000] * 500 + [0] * 10])      # a quiet half-second
    asked: list[str] = []

    async def voice(text, voice=None, **_):
        asked.append(text)
        yield 1000, _pcm(next(takes) if text == first_sound.BREATH else [0] * 10 + [9000] * 300 + [0] * 10)

    monkeypatch.setattr(tts, "stream", voice)
    monkeypatch.setattr(first_sound, "TAKES", 1)
    asyncio.run(first_sound._make_all("v"))
    assert asked.count(first_sound.BREATH) == 3
    (rate, pcm), = first_sound._made[("v", first_sound.BREATH)]
    assert 0.4 < len(pcm) / 2 / rate < 0.6


def test_the_end_of_a_turn_gets_a_breath_a_word_or_nothing(monkeypatch):
    first_sound._made[("v", first_sound.BREATH)] = [(1000, b"BR")]
    first_sound._made[("v", "Да…")] = [(1000, b"DA")]
    rolls = iter([0.1, 0.7, 0.95])                          # breath 0.6, word 0.2, nothing
    rng = random.Random()
    monkeypatch.setattr(rng, "random", lambda: next(rolls))
    monkeypatch.setattr(rng, "choice", lambda seq: seq[0])
    assert first_sound.choose("v", "statement", rng)[0] == "(вдох)"
    assert first_sound.choose("v", "statement", rng)[0] == "Да…"
    assert first_sound.choose("v", "statement", rng) is None


def test_while_his_breath_is_not_made_a_word_stands_in(monkeypatch):
    first_sound._made[("v", "Да…")] = [(1000, b"DA")]
    rng = random.Random()
    monkeypatch.setattr(rng, "random", lambda: 0.1)
    assert first_sound.choose("v", "statement", rng)[0] == "Да…"


def test_an_older_friend_breathes_more():
    young, old = first_sound.SHARES["statement"], first_sound.SHARES_OLDER["statement"]
    assert old[0] > young[0] and old[1] < young[1]


def test_he_does_not_make_the_same_sound_twice_running_when_there_is_another():
    first_sound._made[(None, "Хм…")] = [(16000, b"HM")]
    first_sound._made[(None, "Так…")] = [(16000, b"TA")]
    rng = random.Random(1)
    for _ in range(20):
        text, _rate, _pcm = first_sound.pick(None, "thinking", rng, avoid="Хм…")
        assert text == "Так…"
    # Only one made: that one, rather than none.
    assert first_sound.pick(None, "listening", rng) is None
    first_sound._made[(None, "М-м…")] = [(16000, b"MM")]
    assert first_sound.pick(None, "listening", rng, avoid="М-м…")[0] == "М-м…"


def test_they_are_made_once_in_his_voice_and_kept(monkeypatch):
    asked: list[tuple[str, str | None]] = []

    async def voice(text, voice=None, **_):
        asked.append((text, voice))
        yield 1000, _pcm([0] * 50 + [9000] * 300 + [0] * 50)

    monkeypatch.setattr(tts, "stream", voice)

    async def run():
        first = first_sound.prepare("her-voice")
        assert first_sound.prepare("her-voice") is first     # one making per voice
        await first

    asyncio.run(run())
    sounds = list(dict.fromkeys((first_sound.BREATH,) + first_sound.STATEMENT + first_sound.QUESTION
                                + first_sound.THINKING + first_sound.LISTENING))
    reactions = [t for t in first_sound.REACTIONS if t not in sounds]
    texts = sounds + reactions
    assert {t for t, _ in asked} == set(texts)
    assert [t for t, _ in asked][:len(sounds) * first_sound.TAKES] == [
        t for t in sounds for _ in range(first_sound.TAKES)]                 # his sounds first, his breath first of all
    start = len(sounds) * first_sound.TAKES
    assert [t for t, _ in asked][start:start + len(reactions)] == reactions  # then one of each first word
    assert all(v == "her-voice" for _, v in asked)
    assert len(asked) == len(texts) * first_sound.TAKES
    assert first_sound.ready("her-voice") and not first_sound.ready(None)


def test_what_is_made_is_kept_and_never_made_again(monkeypatch):
    """A companion's sounds are made the first time he speaks — not again in
    the next conversation, nor after a restart (DATA_DIR/sounds)."""
    asked: list[str] = []

    async def voice(text, voice=None, **_):
        asked.append(text)
        yield 1000, _pcm([0] * 50 + [9000] * 300 + [0] * 50)

    monkeypatch.setattr(tts, "stream", voice)
    asyncio.run(first_sound._make_all("his-voice"))
    made_first = len(asked)
    kept = first_sound._made[("his-voice", "Понимаю.")]
    first_sound._made.clear()                              # a restart
    asyncio.run(first_sound._make_all("his-voice"))
    assert len(asked) == made_first                        # nothing made again
    assert first_sound._made[("his-voice", "Понимаю.")] == kept


def test_his_usual_first_word_is_ready_made_and_nothing_else_is():
    first_sound._made[("v", "Ого…")] = [(1000, b"OGO")]
    first_sound._made[("v", "Понимаю.")] = [(1000, b"PON")]
    assert first_sound.reaction("v", "Ого...") == (1000, b"OGO")       # «...» is «…»
    assert first_sound.reaction("v", " Понимаю. ") == (1000, b"PON")
    assert first_sound.reaction("v", "Ого!") is None                   # said differently
    assert first_sound.reaction("v", "Ого… а ты как?") is None          # not only that
    assert first_sound.reaction("other", "Ого…") is None               # not in this voice


def test_a_voice_that_cannot_make_them_leaves_him_without_and_says_nothing_else(monkeypatch):
    async def broken(text, voice=None, **_):
        raise RuntimeError("no voice")
        yield  # pragma: no cover

    monkeypatch.setattr(tts, "stream", broken)
    asyncio.run(first_sound._make_all(None))
    assert not first_sound.ready(None)
