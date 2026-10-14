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
    edge, tail = int(rate * first_sound._EDGE), int(rate * first_sound._TAIL)
    assert len(cut) == 300 + edge + tail       # the sound, a little before it, a slow end after
    assert cut[0] == 0 and cut[-1] == 0          # no click, and no dead stop
    assert cut[-tail // 2] < 10000 // 2          # half-way through its end it has mostly died away
    assert max(cut) == 10000
    assert first_sound.trimmed(_pcm([0] * 100), rate) == b""


def _noise(seconds: float, level: int, rate: int = 8000, seed: int = 1) -> list[int]:
    rng = random.Random(seed)
    return [0] * 80 + [int(rng.uniform(-level, level)) for _ in range(int(rate * seconds))] + [0] * 1200


def _tone(seconds: float, level: int, hz: float = 150, rate: int = 8000) -> list[int]:
    import math
    return [0] * 80 + [int(level * math.sin(2 * math.pi * hz * i / rate))
                       for i in range(int(rate * seconds))] + [0] * 1200


#: A companion's voice as tts.voice_for gives it: a Gemini voice, whom it plays.
GEMINI = "gemini:Charon|a man of 68 (calm), warm, relaxed and natural"


def test_a_breath_with_a_voice_in_it_is_made_again_and_air_is_kept(monkeypatch):
    """The owner, 2026-10-08: «everytime he says "ehh" thats not real». Half
    the breaths kept then had a pitch — an «э». A take with one is made again,
    and so is one at full volume; air is kept, as loud as a breath is."""
    takes = iter([_tone(0.5, 9000),            # a voice: «э»
                  _noise(0.5, 32000),          # full volume: not a breath
                  _noise(0.5, 4000)])          # air
    asked: list[tuple[str, str]] = []

    async def voice(text, voice=None, **_):
        asked.append((text, voice))
        yield 8000, _pcm(next(takes) if text == first_sound.BREATH else _noise(0.9, 4000, seed=2))

    monkeypatch.setattr(tts, "stream", voice)
    monkeypatch.setattr(first_sound, "BREATHS", (
        (first_sound.BREATH, "a quiet in-breath", 1, (0.3, 1.1)),
        (first_sound.DEEP_BREATH, "a deep in-breath", 1, (0.6, 1.6))))
    asyncio.run(first_sound._make_breaths(GEMINI))
    assert [t for t, _ in asked] == [first_sound.BREATH] * 3 + [first_sound.DEEP_BREATH]
    assert all("just air, no voice at all" in v and v.startswith("gemini:Charon|a man of 68") for _, v in asked)
    (_rate, ordinary), = first_sound._made[(GEMINI, first_sound.BREATH)]
    (_rate, deep), = first_sound._made[(GEMINI, first_sound.DEEP_BREATH)]
    peak = lambda pcm: max(map(abs, array.array("h", pcm)))
    assert peak(deep) == first_sound.PEAKS[first_sound.DEEP_BREATH] > peak(ordinary)   # and stronger


def test_a_voice_that_cannot_be_told_whom_it_plays_has_no_breaths(monkeypatch):
    asked: list[str] = []

    async def voice(text, voice=None, **_):
        asked.append(text)
        yield 8000, _pcm(_noise(0.5, 4000))

    monkeypatch.setattr(tts, "stream", voice)
    asyncio.run(first_sound._make_breaths("c962ed46edfd419abc530d1e33a7435f"))   # a Fish voice id
    assert asked == [] and not first_sound.breaths("c962ed46edfd419abc530d1e33a7435f")


def test_a_pitch_is_heard_in_a_voice_and_not_in_air():
    assert first_sound._voiced(array.array("h", _tone(0.6, 9000)), 8000) > 0.8
    assert first_sound._voiced(array.array("h", _noise(0.6, 9000)), 8000) < 0.1


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


#: What a stand-in voice makes: a short quiet sound for anything — an
#: ordinary breath, a word — and for <heavy breath> a long, strong one.
SHORT = [0] * 50 + [9000] * 320 + [0] * 100
DEEP = [0] * 50 + [12000] * 700 + [0] * 100


def _sound_of(text: str) -> bytes:
    """At 1000 Hz: a word is SHORT; a breath is air — noise — as long as its
    kind (the deep one longest)."""
    if text == first_sound.DEEP_BREATH:
        return _pcm(_noise(0.9, 9000, rate=1000))
    if text in (first_sound.BREATH, first_sound.EXHALE):
        return _pcm(_noise(0.5, 9000, rate=1000))
    return _pcm(SHORT)


def test_they_are_made_once_in_his_voice_and_kept(monkeypatch):
    asked: list[tuple[str, str | None]] = []

    async def voice(text, voice=None, **_):
        asked.append((text, voice))
        yield 1000, _sound_of(text)

    monkeypatch.setattr(tts, "stream", voice)

    async def run():
        first = first_sound.prepare(GEMINI)
        assert first_sound.prepare(GEMINI) is first          # one making per voice
        await first

    asyncio.run(run())
    breaths = [kind for kind, _how, count, _lengths in first_sound.BREATHS for _ in range(count)]
    sounds = list(dict.fromkeys(first_sound.STATEMENT + first_sound.QUESTION + first_sound.THINKING
                                + first_sound.LISTENING))
    # A listener's sounds (listening.py), each in its colour — his own voice
    # told how (first_sound.TONES) — and his usual first words.
    along = [(first_sound._toned(GEMINI, tone), s) for tone in first_sound.TONES
             for s in first_sound.LISTENER[tone]]
    along = [(v, s) for v, s in dict.fromkeys(along) if not (v == GEMINI and s in sounds)]
    once = along + [(GEMINI, r) for r in first_sound.REACTIONS
                    if r not in sounds and (GEMINI, r) not in along]
    said = [t for t, _ in asked]
    assert said[:len(breaths)] == breaths                                    # his breaths first of all
    rest = asked[len(breaths):]
    assert [t for t, _ in rest[:len(sounds) * first_sound.TAKES]] == [
        t for t in sounds for _ in range(first_sound.TAKES)]                 # then his sounds
    start = len(sounds) * first_sound.TAKES
    assert [(v, t) for t, v in rest[start:start + len(once)]] == once       # then one of each
    assert len(rest) == (len(sounds) + len(once)) * first_sound.TAKES
    colours = {v for v, _ in along}
    assert GEMINI in colours and len(colours) == len(first_sound.TONES)     # four colours, one voice
    assert all(v.startswith("gemini:Charon|a man of 68: ") for v in colours - {GEMINI})
    assert first_sound.ready(GEMINI) and not first_sound.ready(None)
    ordinary = first_sound._made[(GEMINI, first_sound.BREATH)][0]
    deep = first_sound._made[(GEMINI, first_sound.DEEP_BREATH)][0]
    assert len(deep[1]) > len(ordinary[1])                                   # the deep one is longer
    assert len(first_sound.breaths(GEMINI)) == 6 + 3                         # in and out, many
    assert len(first_sound.breaths(GEMINI, older=True)) == 6 + 3 + 4


def test_what_is_made_is_kept_and_never_made_again(monkeypatch):
    """A companion's sounds are made the first time he speaks — not again in
    the next conversation, nor after a restart (DATA_DIR/sounds)."""
    asked: list[str] = []

    async def voice(text, voice=None, **_):
        asked.append(text)
        yield 1000, _sound_of(text)

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
