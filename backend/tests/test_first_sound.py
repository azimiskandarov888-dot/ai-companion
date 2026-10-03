"""His first sound (first_sound.py): at once, the right one, never twice in a
row of his words, never remembered. The live channel's side of it is pinned in
test_live.py."""

from __future__ import annotations

import array
import asyncio
import random

import pytest

from app import first_sound, tts


@pytest.mark.parametrize("said", ["Я сегодня в школе был.", "Да нормально всё.", "А ты откуда?",
                                  "Короче, я прихожу в школу, а там,"])
def test_a_finished_turn_gets_a_listeners_sound(said):
    assert first_sound.at_end(said) == "listening"


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

    async def voice(text, voice=None):
        asked.append((text, voice))
        yield 1000, _pcm([0] * 50 + [9000] * 100 + [0] * 50)

    monkeypatch.setattr(tts, "stream", voice)

    async def run():
        first = first_sound.prepare("her-voice")
        assert first_sound.prepare("her-voice") is first     # one making per voice
        await first

    asyncio.run(run())
    texts = dict.fromkeys(first_sound.LISTENING + first_sound.THINKING + first_sound.REACTIONS)
    assert {t for t, _ in asked} == set(texts)
    assert [t for t, _ in asked][:len(first_sound.LISTENING) * first_sound.TAKES] == [
        t for t in first_sound.LISTENING for _ in range(first_sound.TAKES)]   # sounds first
    assert all(v == "her-voice" for _, v in asked)
    assert len(asked) == len(texts) * first_sound.TAKES
    assert first_sound.ready("her-voice") and not first_sound.ready(None)


def test_what_is_made_is_kept_and_never_made_again(monkeypatch):
    """A companion's sounds are made the first time he speaks — not again in
    the next conversation, nor after a restart (DATA_DIR/sounds)."""
    asked: list[str] = []

    async def voice(text, voice=None):
        asked.append(text)
        yield 1000, _pcm([0] * 50 + [9000] * 100 + [0] * 50)

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
    async def broken(text, voice=None):
        raise RuntimeError("no voice")
        yield  # pragma: no cover

    monkeypatch.setattr(tts, "stream", broken)
    asyncio.run(first_sound._make_all(None))
    assert not first_sound.ready(None)
