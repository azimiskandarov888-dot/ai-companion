"""The live ears (hearing.py): Deepgram Flux, one line per conversation.

What is pinned here is what Deepgram is TOLD — above all that audio is never
kept (children talk to him) — and what is done with what it says back.
"""

from __future__ import annotations

import asyncio
import json
from urllib.parse import parse_qs, urlparse

import pytest
from websockets.exceptions import ConnectionClosed
from websockets.frames import Close

from app import config, hearing


def _query(keyterms=()) -> dict:
    parsed = urlparse(hearing.url(keyterms))
    return parse_qs(parsed.query)


def test_deepgram_never_keeps_the_audio():
    """Without mip_opt_out Deepgram may keep audio to improve its models — and
    some of the people talking to him are children, about whom nothing is kept."""
    assert _query()["mip_opt_out"] == ["true"]


def test_it_is_told_the_language_and_the_format_it_is_sent(monkeypatch):
    monkeypatch.setattr(config, "LANGUAGE", "ru")
    q = _query()
    assert q["model"] == [config.FLUX_MODEL]
    assert q["language_hint"] == ["ru"]
    assert q["encoding"] == ["linear16"] and q["sample_rate"] == [str(hearing.RATE)]
    assert q["eot_threshold"] == [str(config.FLUX_EOT_THRESHOLD)]
    assert q["eager_eot_threshold"] == [str(config.FLUX_EAGER_EOT_THRESHOLD)]
    assert q["eot_timeout_ms"] == [str(config.FLUX_EOT_TIMEOUT_MS)]


def test_it_goes_to_europe_by_default():
    """80 ms there and back from Tashkent, against 240 ms for the US address."""
    assert config.DEEPGRAM_URL.startswith("wss://api.eu.deepgram.com/v2/listen")


def test_his_name_is_a_word_to_expect():
    assert _query(("Андрей",))["keyterm"] == ["Андрей"]
    assert "keyterm" not in _query(("", "  "))


def test_an_80_ms_chunk_is_what_deepgram_asks_for():
    assert hearing.CHUNK == 2560


def test_no_key_is_said_plainly():
    with pytest.raises(RuntimeError, match="DEEPGRAM_API_KEY"):
        asyncio.run(hearing.Ears.open())


class _Line:
    """A WebSocket that says what it is given and records what it is sent."""

    def __init__(self, incoming, closing=None) -> None:
        self.incoming = list(incoming)
        self.closing = closing
        self.sent: list = []
        self.closed = False

    async def send(self, data) -> None:
        self.sent.append(data)

    async def close(self) -> None:
        self.closed = True

    def __aiter__(self):
        return self._each()

    async def _each(self):
        for item in self.incoming:
            yield item
        if self.closing is not None:
            raise self.closing


def _heard(line) -> list:
    async def collect():
        return [m async for m in hearing.Ears(line).events()]
    return asyncio.run(collect())


def test_what_flux_says_comes_through_in_order():
    turn = {"type": "TurnInfo", "event": "EndOfTurn", "transcript": "привет"}
    got = _heard(_Line([json.dumps({"type": "Connected"}), b"\x00", "not json", json.dumps(turn)]))
    assert got == [{"type": "Connected"}, turn]


def test_a_fatal_error_ends_the_conversation_out_loud():
    fatal = json.dumps({"type": "FatalError", "code": "NET-0001", "description": "no audio"})
    with pytest.raises(RuntimeError, match="NET-0001"):
        _heard(_Line([fatal]))


def test_a_normal_hang_up_is_just_the_end():
    assert _heard(_Line([], closing=ConnectionClosed(Close(1000, ""), None))) == []


def test_a_line_that_drops_is_said():
    with pytest.raises(RuntimeError, match="1011"):
        _heard(_Line([], closing=ConnectionClosed(Close(1011, "internal"), None)))


def test_hanging_up_asks_flux_to_close_and_never_raises():
    line = _Line([])
    ears = hearing.Ears(line)
    asyncio.run(ears.hear(b"\x00\x00"))
    asyncio.run(ears.finished())
    asyncio.run(ears.close())
    assert line.sent[0] == b"\x00\x00"
    assert json.loads(line.sent[1]) == {"type": "ForceEndTurn"}
    assert json.loads(line.sent[2]) == {"type": "CloseStream"}
    assert line.closed
