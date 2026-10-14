"""The live ears (hearing.py): Soniox, one line per conversation.

What is pinned here is what Soniox is TOLD — the key in a header, never in
the request; patient endpoints; his name as a word to expect — and what is
made of what it says back: the turns the live channel follows, and a thought
broken off held until it is plainly all they are going to say.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from websockets.exceptions import ConnectionClosed
from websockets.frames import Close

from app import config, hearing


def tok(text: str, final: bool = True, start: int = 0, end: int = 0) -> dict:
    return {"text": text, "is_final": final, "start_ms": start, "end_ms": end}


END = tok("<end>")


# ── what it is told ─────────────────────────────────────────────────────────

def test_it_is_told_the_format_the_languages_and_to_be_patient():
    request = hearing.start_request()
    assert request["model"] == config.SONIOX_MODEL
    assert request["audio_format"] == "pcm_s16le"
    assert request["sample_rate"] == hearing.RATE == 16000 and request["num_channels"] == 1
    assert request["language_hints"] == ["ru", "en"]
    assert request["enable_endpoint_detection"] is True
    assert request["endpoint_sensitivity"] == config.SONIOX_ENDPOINT_SENSITIVITY < 0
    assert request["max_endpoint_delay_ms"] == config.SONIOX_MAX_ENDPOINT_DELAY_MS


def test_the_key_never_goes_in_the_request():
    """In a header: a start request carrying the key is refused from 2027-01-15,
    and a request is a thing that gets logged."""
    assert not any("key" in field for field in hearing.start_request(("Андрей",)))


def test_his_name_is_a_word_to_expect():
    assert hearing.start_request(("Андрей",))["context"] == {"terms": ["Андрей"]}
    assert "context" not in hearing.start_request(("", "  "))


def test_an_80_ms_chunk_is_what_the_phone_sends():
    assert hearing.CHUNK == 2560


def test_no_key_is_said_plainly():
    with pytest.raises(RuntimeError, match="SONIOX_API_KEY"):
        asyncio.run(hearing.Ears.open())


def test_the_key_goes_in_a_header_and_the_request_first(monkeypatch):
    line = _Line([])
    seen = {}

    async def connect(url, **kwargs):
        seen.update(url=url, **kwargs)
        return line

    monkeypatch.setattr(config, "SONIOX_API_KEY", "test-key")
    monkeypatch.setattr(hearing, "connect", connect)
    ears = asyncio.run(hearing.Ears.open(("Андрей",)))
    assert seen["url"] == config.SONIOX_URL
    assert seen["additional_headers"] == {"Authorization": "Bearer test-key"}
    assert json.loads(line.sent[0]) == hearing.start_request(("Андрей",))
    assert "test-key" not in line.sent[0]
    assert ears._turns.hold == config.HOLD_UNFINISHED


# ── what is made of what it says ────────────────────────────────────────────

def test_a_turn_begins_grows_and_ends_with_when_each_word_was_said():
    turns = hearing.Turns(hold=1.5)
    assert [t["event"] for t in turns.feed({"tokens": [tok("При", final=False)]}, 0.0)] == [
        "StartOfTurn"]
    grown = turns.feed({"tokens": [tok("Привет", start=100, end=520), tok("."),
                                   tok(" как", final=False)]}, 0.3)
    assert [(t["event"], t["transcript"]) for t in grown] == [("Update", "Привет. как")]
    ended = turns.feed({"tokens": [tok(" как", start=700, end=900), tok(" дела", start=950,
                                   end=1400), tok("?"), END]}, 1.9)
    assert ended[-1]["event"] == "EndOfTurn"
    assert ended[-1]["transcript"] == "Привет. как дела?"
    # The punctuation is not a word, and has no moment of its own.
    assert [w["word"] for w in ended[-1]["words"]] == ["Привет", "как", "дела"]
    assert ended[-1]["words"][-1]["end"] == pytest.approx(1.4)
    assert turns.held_until is None


@pytest.mark.parametrize("broken", ["I've really been thinking about—", "…последнее время, нет,",
                                    "Я вот думаю:", "Ну, не знаю…", "Ну, не знаю...", "и потом -"])
def test_a_thought_broken_off_is_not_an_end(broken):
    turns = hearing.Turns(hold=1.5)
    got = turns.feed({"tokens": [tok(broken), END]}, 10.0)
    assert [t["event"] for t in got] == ["StartOfTurn"]
    assert turns.held_until == pytest.approx(11.5)


def test_a_finished_one_is():
    turns = hearing.Turns(hold=1.5)
    got = turns.feed({"tokens": [tok("Ну вот и всё."), END]}, 0.0)
    assert [t["event"] for t in got] == ["StartOfTurn", "EndOfTurn"]


def test_if_they_go_on_it_is_all_one_turn():
    turns = hearing.Turns(hold=1.5)
    turns.feed({"tokens": [tok("I've really been thinking about—"), END]}, 0.0)
    # Something that is not a word is not their going on.
    assert turns.feed({"tokens": [tok(" ", final=False)]}, 0.5) == []
    assert turns.held_until is not None
    went_on = turns.feed({"tokens": [tok(" the sea", final=False)]}, 1.0)
    assert [(t["event"], t["transcript"]) for t in went_on] == [
        ("Update", "I've really been thinking about— the sea")]
    assert turns.held_until is None
    ended = turns.feed({"tokens": [tok(" the sea"), tok("."), END]}, 2.0)
    assert [(t["event"], t["transcript"]) for t in ended] == [
        ("Update", "I've really been thinking about— the sea."),
        ("EndOfTurn", "I've really been thinking about— the sea.")]


def test_if_they_say_nothing_more_it_is_their_turn_after_the_hold():
    turns = hearing.Turns(hold=1.5)
    turns.feed({"tokens": [tok("Я вчера ходил в—", end=900), END]}, 4.0)
    assert turns.due(5.49) == []
    ended = turns.due(5.5)
    assert [(t["event"], t["transcript"]) for t in ended] == [("EndOfTurn", "Я вчера ходил в—")]
    assert ended[0]["words"][-1]["end"] == pytest.approx(0.9)
    assert turns.held_until is None and turns.due(100.0) == []


def test_the_button_ends_a_broken_off_turn_at_once():
    turns = hearing.Turns(hold=1.5)
    turns.feed({"tokens": [tok("Я думаю,"), END]}, 0.0)
    ended = turns.feed({"tokens": [tok("<fin>")]}, 0.2)
    assert [(t["event"], t["transcript"]) for t in ended] == [("EndOfTurn", "Я думаю,")]


def test_without_a_hold_a_broken_off_thought_ends_as_soniox_says():
    turns = hearing.Turns(hold=0)
    got = turns.feed({"tokens": [tok("Я думаю,"), END]}, 0.0)
    assert [t["event"] for t in got] == ["StartOfTurn", "EndOfTurn"]


def test_words_after_an_end_in_the_same_message_begin_the_next_turn():
    turns = hearing.Turns(hold=1.5)
    got = turns.feed({"tokens": [tok("Да."), END, tok(" А"), tok(" ты", final=False),
                                 tok("?", final=False)]}, 0.0)
    assert [(t["event"], t["transcript"]) for t in got] == [
        ("StartOfTurn", "Да."), ("EndOfTurn", "Да."), ("StartOfTurn", "А ты?")]


def test_a_sound_that_never_became_a_word_is_no_turn():
    turns = hearing.Turns(hold=1.5)
    assert turns.feed({"tokens": [tok("."), END]}, 0.0) == []
    # A word that vanished closes the turn it opened, with nothing in it.
    assert [t["event"] for t in turns.feed({"tokens": [tok("э", final=False)]}, 1.0)] == [
        "StartOfTurn"]
    assert [(t["event"], t["transcript"]) for t in turns.feed({"tokens": [END]}, 1.5)] == [
        ("EndOfTurn", "")]


def test_a_message_with_no_tokens_is_only_the_time_passing():
    """Soniox sends those in silence (5 of 52 on a whispered talk, 2026-10-14);
    the words still changing are not taken for gone."""
    turns = hearing.Turns(hold=1.5)
    turns.feed({"tokens": [tok("Я", final=False)]}, 0.0)
    assert turns.feed({"tokens": [], "total_audio_proc_ms": 900}, 0.2) == []
    assert [t["transcript"] for t in turns.feed({"tokens": [tok("Я"), END]}, 0.5)] == ["Я"]


def test_words_that_were_never_said_after_all_close_the_turn():
    """Otherwise the turn would stay open — and somebody talking over him next
    would come as more of it, never as a turn of their own (live._listen)."""
    turns = hearing.Turns(hold=1.5)
    turns.feed({"tokens": [tok("а", final=False)]}, 0.0)
    assert [(t["event"], t["transcript"]) for t in turns.feed(
        {"tokens": [tok(" ", final=False)]}, 0.3)] == [("EndOfTurn", "")]
    assert turns.deadline is None


def test_a_turn_that_goes_quiet_without_an_end_ends_by_itself():
    """Soniox should always say «<end>» within its delay; if it ever does not,
    the turn is theirs a little after — with the words still changing too."""
    turns = hearing.Turns(hold=1.5)
    assert turns.quiet == pytest.approx(
        config.SONIOX_MAX_ENDPOINT_DELAY_MS / 1000 + 1.5 + hearing.QUIET_MARGIN)
    turns.feed({"tokens": [tok("Ну"), tok(" вот", final=False)]}, 10.0)
    assert turns.deadline == pytest.approx(10.0 + turns.quiet)
    assert turns.due(10.0 + turns.quiet - 0.01) == []
    assert [(t["event"], t["transcript"]) for t in turns.due(10.0 + turns.quiet)] == [
        ("EndOfTurn", "Ну вот")]
    assert turns.deadline is None


def test_a_held_thought_is_due_at_its_hold_not_at_the_quiet_limit():
    turns = hearing.Turns(hold=1.5)
    turns.feed({"tokens": [tok("Я думаю,"), END]}, 3.0)
    assert turns.deadline == pytest.approx(4.5)


# ── the line ────────────────────────────────────────────────────────────────

class _Line:
    """A WebSocket that says what it is given and records what it is sent."""

    def __init__(self, incoming, closing=None, *, then_wait: bool = False) -> None:
        self.incoming = list(incoming)
        self.closing = closing
        self.then_wait = then_wait
        self.sent: list = []
        self.closed = False

    async def send(self, data) -> None:
        self.sent.append(data)

    async def close(self) -> None:
        self.closed = True

    async def recv(self):
        if self.incoming:
            return self.incoming.pop(0)
        if self.then_wait:
            await asyncio.Event().wait()
        raise self.closing or ConnectionClosed(Close(1000, ""), None)


def _heard(line, hold: float = 1.5, *, take: int | None = None) -> list:
    async def collect():
        got = []
        async for turn in hearing.Ears(line, hold).events():
            got.append(turn)
            if take is not None and len(got) >= take:
                break
        return got
    return asyncio.run(asyncio.wait_for(collect(), 5))


def test_what_soniox_says_comes_through_as_turns_in_order():
    said = [json.dumps({"tokens": [tok("Привет", final=False)]}), b"\x00", "not json", "[]",
            json.dumps({"tokens": [tok("Привет"), tok("!"), END]}),
            json.dumps({"tokens": [], "finished": True}),
            json.dumps({"tokens": [tok("never read")]})]
    got = _heard(_Line(said))
    assert [(t["event"], t["transcript"]) for t in got] == [
        ("StartOfTurn", "Привет"), ("Update", "Привет!"), ("EndOfTurn", "Привет!")]


def test_a_held_thought_becomes_their_turn_with_nothing_more_coming():
    line = _Line([json.dumps({"tokens": [tok("Я вчера ходил в—"), END]})], then_wait=True)
    got = _heard(line, hold=0.05, take=2)
    assert [(t["event"], t["transcript"]) for t in got] == [
        ("StartOfTurn", "Я вчера ходил в—"), ("EndOfTurn", "Я вчера ходил в—")]


def test_an_error_from_soniox_ends_the_conversation_out_loud():
    spent = json.dumps({"error_code": 402, "error_type": "organization_balance_exhausted",
                        "error_message": "Organization balance exhausted."})
    with pytest.raises(RuntimeError, match="402 organization_balance_exhausted"):
        _heard(_Line([spent]))


def test_a_normal_hang_up_is_just_the_end():
    assert _heard(_Line([], closing=ConnectionClosed(Close(1000, ""), None))) == []


def test_a_line_that_drops_is_said():
    with pytest.raises(RuntimeError, match="1011"):
        _heard(_Line([], closing=ConnectionClosed(Close(1011, "internal"), None)))


def test_hanging_up_says_no_more_audio_and_never_raises():
    line = _Line([])
    ears = hearing.Ears(line)
    asyncio.run(ears.hear(b"\x00\x00"))
    asyncio.run(ears.finished())
    asyncio.run(ears.close())
    assert line.sent[0] == b"\x00\x00"
    assert json.loads(line.sent[1]) == {"type": "finalize"}
    assert line.sent[2] == ""          # an empty TEXT frame: no more audio
    assert line.closed

    class Gone(_Line):
        async def send(self, data):
            raise ConnectionError("gone")

    asyncio.run(hearing.Ears(Gone([])).close())   # no exception
