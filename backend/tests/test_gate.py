"""Only their voice goes on to the ears (gate.py).

Deepgram bills the audio it is sent; most of a talk is not the person's voice.
Pinned here is everything that would otherwise cost a word: the first
consonant, the pause Flux needs to hear to end a turn, a turn Flux started
late, somebody talking over him — and which way the gate errs: open.
"""

from __future__ import annotations

import math
from array import array

import pytest

from app import gate

FRAME = 0.08


def tone(db: float, length: float = FRAME) -> bytes:
    amp = 32767 * 10 ** (db / 20) * math.sqrt(2)
    n = int(16000 * length)
    return array("h", [int(amp * math.sin(2 * math.pi * 220 * i / 16000)) for i in range(n)]).tobytes()


SILENCE = bytes(int(16000 * FRAME) * 2)
ROOM = tone(-65)          # a quiet room
SOFT = tone(-42)          # a soft voice — or a consonant
VOICE = tone(-22)         # speech as it arrives (live_check: -13 to -25 dBFS)


def run(g: gate.Gate, frames, start: float = 0.0, *, over_him: bool = False):
    """Feed frames in real time; return what went to Flux, with arrival times."""
    out, now = [], start
    for frame in frames:
        out += g.feed(frame, now, over_him=over_him)
        now += FRAME
    return out, now


def test_levels_are_measured_in_db_below_full_scale():
    assert gate.level(SILENCE) == -120.0
    assert abs(gate.level(tone(-22)) - -22) < 0.5
    assert abs(gate.level(tone(-65)) - -65) < 1.5


def test_a_quiet_room_is_never_sent():
    g = gate.Gate(0.0)
    out, _ = run(g, [ROOM] * 50 + [SILENCE] * 50)
    assert out == [] and not g.open
    assert g.heard_s == pytest.approx(8.0) and g.sent_s == 0


def test_a_voice_goes_with_the_second_before_it_and_its_own_times():
    """A soft first consonant is quieter than any threshold; Flux's word times
    must still turn into the moment that audio really arrived."""
    g = gate.Gate(0.0)
    out, _ = run(g, [ROOM] * 10 + [SOFT, SOFT])
    assert g.open
    sent = [frame for frame, _ in out]
    assert sent[-2:] == [SOFT, SOFT] and set(sent[:-2]) == {ROOM}
    assert 0.4 <= sum(gate.seconds(f) for f in sent[:-2]) <= gate.PREROLL
    times = [t for _, t in out]
    assert times == sorted(times) and times[-1] == pytest.approx(11 * FRAME)


def test_a_click_does_not_open_it_and_a_clear_voice_opens_at_once():
    g = gate.Gate(0.0)
    out, _ = run(g, [SOFT] + [ROOM] * 5)
    assert out == [] and not g.open
    out, _ = run(gate.Gate(0.0), [VOICE])
    assert out == [(VOICE, 0.0)]


def test_the_pause_inside_a_turn_reaches_flux_until_flux_ends_it():
    """Flux ends a turn by hearing the pause: cut it, and he answers late."""
    g = gate.Gate(0.0)
    out, now = run(g, [VOICE] * 5)
    g.on_turn("StartOfTurn", now)
    out, now = run(g, [ROOM] * 30, now)             # 2.4 s of pause, mid-turn
    assert len(out) == 30 and g.open
    g.on_turn("EndOfTurn", now)
    out, now = run(g, [ROOM] * 30, now)
    # Closed AFTER_END later: those frames went, the rest did not.
    assert 0 < len(out) <= math.ceil(gate.AFTER_END / FRAME) + 1 and not g.open


def test_a_sound_that_never_became_a_turn_closes_it():
    g = gate.Gate(0.0)
    run(g, [VOICE])                                  # a door
    out, _ = run(g, [ROOM] * 40, FRAME)
    assert not g.open
    assert len(out) <= math.ceil(gate.NO_TURN_QUIET / FRAME) + 1


def test_a_turn_flux_started_late_is_followed_to_its_end():
    g = gate.Gate(0.0)
    run(g, [VOICE])
    out, now = run(g, [ROOM] * 30, FRAME)            # closed: nothing became a turn…
    assert not g.open
    g.on_turn("StartOfTurn", now)                    # …until Flux says it did
    out, now = run(g, [ROOM] * 3, now)
    assert g.open and out


def test_over_him_his_echo_stays_out_and_somebody_talking_gets_in():
    g = gate.Gate(0.0)
    out, now = run(g, [tone(-45)] * 20, over_him=True)   # his voice, through the echo cancellation
    assert out == []
    out, _ = run(g, [VOICE] * 2, now, over_him=True)     # «подожди»
    assert g.open and out


def test_a_noisy_room_keeps_it_open_never_deaf():
    """Which way it errs is chosen: the saving shrinks, the hearing never does."""
    g = gate.Gate(0.0)
    out, _ = run(g, [tone(-45)] * 100)
    assert len(out) >= 95


def test_a_closed_line_is_kept_alive_on_a_beat():
    g = gate.Gate(0.0)
    assert g.keepalive(gate.KEEPALIVE_EVERY - 0.1) is None
    beat = g.keepalive(gate.KEEPALIVE_EVERY)
    assert beat == bytes(len(beat)) and gate.seconds(beat) == gate.KEEPALIVE
    assert g.keepalive(gate.KEEPALIVE_EVERY + 0.1) is None     # not again so soon
    run(g, [VOICE])
    assert g.keepalive(100.0) is None or not g.open             # an open line needs none


def test_switched_off_it_sends_everything_as_before():
    g = gate.Gate(0.0, enabled=False)
    out, _ = run(g, [SILENCE] * 10)
    assert len(out) == 10 and g.keepalive(100.0) is None


def test_it_says_what_the_talk_cost():
    g = gate.Gate(0.0)
    run(g, [ROOM] * 40 + [VOICE] * 10)
    assert "sent to the ears" in g.report() and g.sent_s < g.heard_s


def test_as_he_stops_it_opens_and_waits_for_their_answer():
    """That is when people answer: an answer on a line already listening has
    nothing for Flux to catch up on. His own voice before it is not sent — he
    would be answered for it."""
    g = gate.Gate(0.0)
    echo, now = run(g, [tone(-45)] * 10, over_him=True)
    for frame in [tone(-45)] * 10:                   # what feed saw: he speaks
        g.feed(frame, now, over_him=True, he_speaks=True)
        now += FRAME
    out = g.feed(ROOM, now)                          # he has stopped
    assert g.open and out == [(ROOM, now)]           # from now, not before
    out, now = run(g, [ROOM] * int(gate.EXPECT_FOR / FRAME), now + FRAME)
    assert len(out) == int(gate.EXPECT_FOR / FRAME)   # waiting, listening
    run(g, [ROOM] * 3, now)
    assert not g.open                                 # nobody answered


def test_an_answer_inside_the_wait_is_heard_to_its_end():
    g = gate.Gate(0.0)
    g.feed(ROOM, 0.0, he_speaks=True)
    g.feed(ROOM, FRAME)                               # he stopped
    out, now = run(g, [ROOM] * 5 + [VOICE] * 10, 2 * FRAME)
    g.on_turn("StartOfTurn", now)
    out, now = run(g, [ROOM] * 40, now)               # past the wait: the turn holds it
    assert g.open and len(out) == 40
