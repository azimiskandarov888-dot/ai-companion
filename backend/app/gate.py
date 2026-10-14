"""What the live ears are sent: the person's voice, not the room.

OFF since 2026-10-14 (config.LIVE_GATE): the ears are Soniox now, which
bills the whole stream, not the audio in it — holding the room back saves
nothing there. Kept, measured and tested, for ears that bill what they are
sent, as Deepgram did:

Deepgram bills a stream for the audio it is sent, silence included — «you will
still be billed for an active connection if you're sending data»
(developers.deepgram.com, Live Streaming Audio Transcription) — and the live
channel used to send it everything: the person, their pauses, the room, and
his own voice coming back while he spoke. About $4.7 a person a month at
twenty minutes a day, for words that were perhaps a third of it. The owner,
2026-10-11: «чтобы слушали только наш голос».

So the phone still streams everything to this server — that costs nothing —
and only the person's speech goes on to Flux:

  · OPENED by a voice: frames loud enough to be somebody, for long enough to
    be more than a click (OPEN_AFTER) — or at once, if clearly loud. The
    second before it goes too (PREROLL), with the moments it really arrived:
    a soft first consonant is quieter than any threshold and must not be lost;
    Flux's «the last word ended at 5.06 s» must still turn into the right
    moment in time (live.Session._speech_end); and Flux hears the end of a
    turn as fast as before only with the room in its ears before the words —
    measured on the real ears, below.
  · HELD until Flux itself says the turn is over (EndOfTurn). It decides the
    end by hearing the pause, so the pause must reach it: cut short, he would
    answer late or never. Only after that, and a moment of quiet, does it close.
  · A sound that never became a turn — a cough, a door — closes it after
    NO_TURN_QUIET. A turn Flux did start is followed to its end, even one it
    started late: StartOfTurn reopens it.
  · AS HE STOPS, it opens by itself and waits EXPECT_FOR: that is when people
    answer, and an answer that starts on a line already listening has nothing
    for Flux to catch up on — a second of held audio sent at once made a short
    answer's end 0.08 s later to hear (measured below). What came before is not
    sent then: it is his own voice, and he would be answered for it.
  · WHILE HE SPEAKS the bar is higher (OPEN_DB_OVER_HIM): what the phone's echo
    cancellation lets through of his own voice is quieter than somebody talking
    over him. Interrupting him still works.
  · Between turns the line is kept alive with 80 ms of silence every
    KEEPALIVE_EVERY seconds: Flux has no KeepAlive and hangs up after about ten
    seconds without audio (eight held, measured 2026-10-11).

Which way it errs is chosen, not left to chance: a word never missed is worth
more than a second saved. A noisy room keeps it open longer — the saving
shrinks, the hearing never does. The thresholds sit far below speech as it
arrives (live_check u1–u3: words at -13 to -25 dBFS, soft endings to -40).

── MEASURED ON THE REAL EARS, 2026-10-11 ───────────────────────────────────

One talk (live_check u1–u3 with a room before and his voice after each), sent
whole and gated, alternating, through real Flux. The words: the same, every
time. The end of a turn, from the last word: whole 0.95 s (median of 9–18);
gated with half a second before the voice 1.03 s — Flux was slower to be
sure without the room before the words, a quarter second or half the same;
with 0.75 s or 1.0 s before it, 0.94–0.95 s, the same as whole. Hence a
second. But the short answer then came 0.08 s later (0.79–0.83 s against
0.71–0.74 s whole): a second of held audio arriving at once is a second for
Flux to catch up on. Hence EXPECT_FOR — answers mostly start on a line already
listening. With it, and the person's pause before answering him (0.6 s), three
trials: the end of a turn 0.88 s on average gated against 0.89 s whole; the
short answer 0.70–0.72 s against 0.78–0.81 s; the words the same; sent 68% of
that talk, whose turns were long. A talk of short answers and longer replies
of his sends about half (an estimate — every talk prints its own,
live.Session.run).
"""

from __future__ import annotations

import math
import sys
from array import array
from collections import deque

#: 16-bit little-endian mono at 16 kHz — what the phone sends (hearing.RATE).
RATE = 16000

#: How much of what came before a voice goes to Flux with it (see MEASURED).
PREROLL = 1.0
#: Loud enough to be somebody — when he is not speaking…
OPEN_DB = -50.0
#: …and while he is, above what the echo cancellation lets through of him.
OPEN_DB_OVER_HIM = -40.0
#: Loud enough to open at once, without waiting OPEN_AFTER (never over him).
STRONG_DB = -30.0
#: A voice for this long in a row opens it; a click does not.
OPEN_AFTER = 0.12
#: After Flux's EndOfTurn, this much quiet before it closes. Short: the turn is
#: already heard, and a voice that carries on opens it again, the second
#: before it included.
AFTER_END = 0.2
#: A sound that never became a turn: closed after this much quiet.
NO_TURN_QUIET = 1.5
#: A turn Flux has open is followed to its end — but no longer than this
#: without a voice: the ears end a turn by themselves after a few seconds.
TURN_QUIET_CAP = 7.0
#: As he stops speaking, open and wait this long for their answer.
EXPECT_FOR = 2.0
#: Silence to keep a closed line alive: this often, this long.
KEEPALIVE_EVERY = 4.0
KEEPALIVE = 0.08


def level(pcm: bytes) -> float:
    """Loudness of a piece of audio, in dB below full scale (-120: none)."""
    samples = array("h")
    samples.frombytes(pcm[: len(pcm) - len(pcm) % 2])
    if sys.byteorder != "little":
        samples.byteswap()
    if not samples:
        return -120.0
    power = sum(s * s for s in samples) / len(samples)
    return 10 * math.log10(power / 32768**2) if power else -120.0


def seconds(pcm: bytes) -> float:
    return len(pcm) / (2 * RATE)


class Gate:
    """One conversation's gate between the phone and Flux. `enabled=False`
    sends everything, as before it existed (config.LIVE_GATE)."""

    def __init__(self, now: float, *, enabled: bool = True) -> None:
        self.enabled = enabled
        self.open = not enabled
        self._preroll: deque[tuple[bytes, float]] = deque()
        self._preroll_s = 0.0
        self._voiced_for = 0.0
        self._last_voiced = now
        self._turn = False
        self._ended: float | None = None
        self._he_spoke = False
        self._expect_until = 0.0
        self.last_sent = now
        #: Seconds of audio the phone sent, and seconds that went on to Flux.
        self.heard_s = 0.0
        self.sent_s = 0.0

    def feed(self, pcm: bytes, now: float, *, over_him: bool = False,
             he_speaks: bool = False) -> list[tuple[bytes, float]]:
        """A frame from the phone. Returns what goes to Flux now, in order, each
        with the moment it arrived — nothing, the frame, or the frames held
        before it as well. `over_him`: he can be heard and may be talked over
        (the higher bar); `he_speaks`: he can be heard at all."""
        length = seconds(pcm)
        self.heard_s += length
        if not self.enabled:
            return self._sent([(pcm, now)], now)
        stopped = self._he_spoke and not he_speaks
        self._he_spoke = he_speaks
        if stopped and not self.open:
            # He has just stopped: this is when they answer. Listen from now —
            # not before: what is held is his own voice coming back.
            self.open, self._ended = True, None
            self._expect_until = now + EXPECT_FOR
            self._preroll.clear()
            self._preroll_s = 0.0
        loud = level(pcm)
        voiced = loud >= (OPEN_DB_OVER_HIM if over_him else OPEN_DB)
        if voiced:
            self._voiced_for += length
            self._last_voiced = now
        else:
            self._voiced_for = 0.0

        if self.open:
            if self._done(now):
                self.open = False   # this frame still goes: the last of the quiet
            return self._sent([(pcm, now)], now)

        self._preroll.append((pcm, now))
        self._preroll_s += length
        while self._preroll and self._preroll_s - seconds(self._preroll[0][0]) >= PREROLL:
            self._preroll_s -= seconds(self._preroll.popleft()[0])
        strong = voiced and not over_him and loud >= STRONG_DB
        if self._turn or strong or self._voiced_for >= OPEN_AFTER:
            self.open, self._ended = True, None
            if self._turn:
                # Reopened by Flux's own turn (it started late): what is held
                # is all quiet, whatever it is — nothing to time from it.
                self._last_voiced = max(self._last_voiced, now)
            out = list(self._preroll)
            self._preroll.clear()
            self._preroll_s = 0.0
            return self._sent(out, now)
        return []

    def on_turn(self, event: str, now: float) -> None:
        """What Flux says about the turn (TurnInfo events)."""
        if event in ("StartOfTurn", "TurnResumed"):
            self._turn, self._ended = True, None
        elif event == "EndOfTurn":
            self._turn, self._ended = False, now

    def keepalive(self, now: float) -> bytes | None:
        """Silence to keep a closed line from hanging up, when it is due."""
        if not self.enabled or self.open or now - self.last_sent < KEEPALIVE_EVERY:
            return None
        beat = bytes(int(RATE * KEEPALIVE) * 2)
        self._sent([(beat, now)], now)
        return beat

    def sent(self, pcm: bytes, now: float) -> None:
        """Audio the live channel sent Flux itself (silence into a quiet turn)."""
        self._sent([(pcm, now)], now)

    def _done(self, now: float) -> bool:
        quiet = now - self._last_voiced
        if self._turn:
            return quiet >= TURN_QUIET_CAP
        if now < self._expect_until:
            return False
        if self._ended is not None:
            return quiet >= AFTER_END and now - self._ended >= AFTER_END
        return quiet >= NO_TURN_QUIET

    def _sent(self, out: list[tuple[bytes, float]], now: float) -> list[tuple[bytes, float]]:
        if out:
            self.last_sent = now
            self.sent_s += sum(seconds(pcm) for pcm, _ in out)
        return out

    def report(self) -> str:
        share = round(100 * self.sent_s / self.heard_s) if self.heard_s else 0
        return f"heard {self.heard_s:.0f} s, sent to the ears {self.sent_s:.0f} s ({share}%)"
