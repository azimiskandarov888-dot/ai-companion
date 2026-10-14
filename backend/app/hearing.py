"""Hearing, live — Soniox, one line for the whole conversation.

Since 2026-10-14 (the owner: «лучше уже полностью перевести нашу программу на
Soniox»). Before it, Deepgram Flux — in git history, should it ever be wanted
back. Measured side by side on the same audio, streamed in real time
(docs/HANDOVER.md §0, «Cheaper ears»): the same words, and more of them —
«ну», «эм», «Боб» with a capital, the English in an English talk — whispered,
with a phone playing behind; the end of a turn 0.4–0.9 s after the last
sound, where Flux took 1.0–2.3 s; at half the price or less ($0.12 an hour
of the whole talk).

── WHAT IT IS SENT AND TOLD ────────────────────────────────────────────────

All of the person's audio, as it comes: Soniox bills the whole stream, not the
audio in it, so holding back the silence saves nothing (gate.py is off). The
key goes in a header, never in the start request (refused from 2027-01-15).
Patient endpoints (SONIOX_ENDPOINT_SENSITIVITY, SONIOX_MAX_ENDPOINT_DELAY_MS):
at the defaults it called «finished» on four thoughts the owner had only
broken off; patient, on two — both ending «—», which the rule below catches.

── WHAT COMES BACK, AND WHAT IS MADE OF IT ──────────────────────────────────

Tokens — pieces of words, each with its time; final, or still changing — and
«<end>» when Soniox thinks they have finished. Turns turns them into the same
TurnInfo the live channel has always followed:

    StartOfTurn   they began — with the first words
    Update        the words so far, as they change
    EndOfTurn     finished — its transcript, and when each piece was said

There is no «похоже, договорил»: Soniox's «договорил» comes as early as Flux's
«похоже» did. The live channel's drafting on a guess stays for ears that give one.

── A THOUGHT BROKEN OFF IS NOT AN END ───────────────────────────────────────

The owner, on «I've really been thinking about—» and a long pause: there is
nothing in it to answer yet — he should get «Ну?» or «О чём?», and only after
a while, longer for an older person. Soniox writes a broken-off thought as it
sounds — «about—», «последнее время... нет,» — so an «<end>» on words ending
like that (UNFINISHED) is held: if they go on, it is all one turn; if they say
nothing for `hold` seconds, it is their turn after all, and the brain, told by
companion.BY_EAR what such an ending means, nudges them on. The button «I've
finished» (finished()) ends a turn at once, broken off or not.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from collections.abc import AsyncIterator

from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed

from . import config

#: What the live channel sends: 16-bit little-endian mono, 16 kHz…
RATE = 16000
#: …in 80 ms frames — 2,560 bytes.
CHUNK = RATE * 2 * 80 // 1000

#: A turn quiet this much longer than Soniox should ever take to end it ends
#: by itself (Turns.quiet).
QUIET_MARGIN = 1.0
#: Words ending like this are a thought broken off, not a turn finished.
UNFINISHED = ("—", "–", "-", ",", ":", "…", "...")
_WORD = re.compile(r"\w")


def unfinished(text: str) -> bool:
    return text.rstrip().endswith(UNFINISHED)


def start_request(keyterms: tuple[str, ...] = ()) -> dict:
    """What Soniox is told as the line opens — everything but the key."""
    request: dict = {
        "model": config.SONIOX_MODEL,
        "audio_format": "pcm_s16le",
        "sample_rate": RATE,
        "num_channels": 1,
        "language_hints": list(config.SONIOX_LANGUAGES),
        "enable_endpoint_detection": True,
        "endpoint_sensitivity": config.SONIOX_ENDPOINT_SENSITIVITY,
        "max_endpoint_delay_ms": config.SONIOX_MAX_ENDPOINT_DELAY_MS,
    }
    # Words it should expect — his name above all, which is a word the person
    # says to him and one no general model has reason to favour.
    terms = [term.strip() for term in keyterms if term and term.strip()]
    if terms:
        request["context"] = {"terms": terms}
    return request


def _turn(event: str, transcript: str, words: list[dict] | None = None) -> dict:
    return {"type": "TurnInfo", "event": event, "transcript": transcript, "words": words or []}


def _text(tokens: list[dict]) -> str:
    return "".join(str(t.get("text") or "") for t in tokens).strip()


class Turns:
    """Soniox's tokens, as the turns the live channel follows. No I/O: what
    Ears reads goes in (feed), and the time, when nothing has come (due)."""

    def __init__(self, hold: float, quiet: float | None = None) -> None:
        #: How long a broken-off thought waits for more before it is their turn.
        self.hold = hold
        #: A turn in which nothing has changed for this long is over, whatever
        #: Soniox says — as Flux's eot_timeout was: it should always have said
        #: «<end>» well before (SONIOX_MAX_ENDPOINT_DELAY_MS), and a turn left
        #: open would let somebody talk over him unheard (live.Session._listen).
        self.quiet = (config.SONIOX_MAX_ENDPOINT_DELAY_MS / 1000 + hold + QUIET_MARGIN
                      if quiet is None else quiet)
        self._final: list[dict] = []
        self._pending: list[dict] = []
        self._in_turn = False
        self._shown = ""
        self._changed_at = 0.0
        self._held_since: float | None = None
        #: How many final tokens there were when it was held.
        self._held_at = 0

    @property
    def held_until(self) -> float | None:
        """When a held thought becomes their turn, if one is held."""
        return None if self._held_since is None else self._held_since + self.hold

    @property
    def deadline(self) -> float | None:
        """When, with nothing more from Soniox, a turn ends by itself."""
        if self.held_until is not None:
            return self.held_until
        return self._changed_at + self.quiet if self._in_turn else None

    def feed(self, message: dict, now: float) -> list[dict]:
        """One message from Soniox: the turns it makes, in order. Final tokens
        come once; the ones still changing come whole in every message that
        has tokens at all (one without is only the time passing)."""
        tokens = message.get("tokens") or []
        if not tokens:
            return []
        out: list[dict] = []
        self._pending = []
        for token in tokens:
            text = str(token.get("text") or "")
            if not token.get("is_final"):
                self._pending.append(token)
            elif text in ("<end>", "<fin>"):
                out += self._sync(now)
                out += self._end(now, forced=text == "<fin>")
            else:
                self._final.append(token)
        return out + self._sync(now)

    def due(self, now: float) -> list[dict]:
        """Nothing has come: a thought held long enough — or a turn gone quiet
        for far too long — is their turn now."""
        until = self.held_until
        if until is not None:
            return self._end(now, forced=True) if now >= until else []
        if self._in_turn and now >= self._changed_at + self.quiet:
            return self._end(now, forced=True, unsure=True)
        return []

    def _sync(self, now: float) -> list[dict]:
        if self._held_since is not None:
            fresh = self._final[self._held_at:] + self._pending
            if not any(_WORD.search(str(t.get("text") or "")) for t in fresh):
                return []
            self._held_since = None   # they went on: the same turn
        text = _text(self._final + self._pending)
        if not _WORD.search(text):
            if self._in_turn and not self._final:
                # The words it thought it heard are gone: no turn after all.
                self._in_turn, self._shown = False, ""
                return [_turn("EndOfTurn", "")]
            return []
        if not self._in_turn:
            self._in_turn, self._shown, self._changed_at = True, text, now
            return [_turn("StartOfTurn", text)]
        if text != self._shown:
            self._shown, self._changed_at = text, now
            return [_turn("Update", text)]
        return []

    def _end(self, now: float, *, forced: bool, unsure: bool = False) -> list[dict]:
        """`unsure`: Soniox never said — its words still changing count too."""
        text = _text(self._final + self._pending if unsure else self._final)
        said = bool(_WORD.search(text))
        if said and not forced and self.hold > 0 and unfinished(text):
            if self._held_since is None:
                self._held_since, self._held_at = now, len(self._final)
            return []
        tokens = self._final + self._pending if unsure else self._final
        out = [_turn("EndOfTurn", text if said else "", self._words(tokens))] if self._in_turn else []
        self._final, self._pending = [], []
        self._in_turn, self._shown, self._held_since = False, "", None
        return out

    @staticmethod
    def _words(tokens: list[dict]) -> list[dict]:
        """Each piece of the turn and when it was said, in seconds of the audio
        sent — what turns «the last word ended at 5.06 s» into a moment
        (live.Session._speech_end)."""
        return [{"word": str(t["text"]).strip(), "start": float(t.get("start_ms") or 0) / 1000,
                 "end": float(t["end_ms"]) / 1000}
                for t in tokens
                if _WORD.search(str(t.get("text") or "")) and t.get("end_ms") is not None]


class Ears:
    """One conversation's line to Soniox."""

    def __init__(self, ws: ClientConnection, hold: float = 0.0) -> None:
        self._ws = ws
        # The phone's audio and the silence the live channel fills gaps with
        # come from two tasks; one send at a time keeps them whole.
        self._sending = asyncio.Lock()
        self._turns = Turns(hold)

    @classmethod
    async def open(cls, keyterms: tuple[str, ...] = (), hold: float | None = None) -> Ears:
        """`hold`: how long a broken-off thought waits for more — the
        caller's, when it knows better (config.HOLD_UNFINISHED_OLDER)."""
        if not config.SONIOX_API_KEY:
            raise RuntimeError(
                "SONIOX_API_KEY is not set — the live ears (Soniox) are not configured."
            )
        ws = await connect(
            config.SONIOX_URL,
            additional_headers={"Authorization": f"Bearer {config.SONIOX_API_KEY}"},
            open_timeout=10,
            max_size=2**22,
        )
        try:
            await ws.send(json.dumps(start_request(keyterms)))
        except Exception:
            await ws.close()
            raise
        return cls(ws, config.HOLD_UNFINISHED if hold is None else hold)

    async def hear(self, pcm: bytes) -> None:
        """Audio from the person, as it comes."""
        async with self._sending:
            await self._ws.send(pcm)

    async def finished(self) -> None:
        """The person says they are done — end the turn now, held or not."""
        async with self._sending:
            await self._ws.send(json.dumps({"type": "finalize"}))

    async def end_of_audio(self) -> None:
        """No more audio: Soniox finishes what it has heard, says so, and hangs
        up — events() then ends (an empty text frame; an empty binary one is
        only an empty piece of audio)."""
        async with self._sending:
            await self._ws.send("")

    async def close(self) -> None:
        """Hang up. Never raises: a line that is already gone is hung up."""
        try:
            await self.end_of_audio()
        except Exception:  # noqa: BLE001
            pass
        try:
            await self._ws.close()
        except Exception:  # noqa: BLE001
            pass

    async def events(self) -> AsyncIterator[dict]:
        """Every turn, in order. Ends when the line closes normally; an error
        from Soniox or an abnormal close is raised, because the conversation
        cannot go on without ears and must be told so."""
        try:
            while True:
                until = self._turns.deadline
                try:
                    if until is None:
                        raw = await self._ws.recv()
                    else:
                        raw = await asyncio.wait_for(self._ws.recv(),
                                                     max(0.0, until - time.monotonic()))
                except TimeoutError:
                    for turn in self._turns.due(time.monotonic()):
                        yield turn
                    continue
                if isinstance(raw, bytes):
                    continue
                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if not isinstance(message, dict):
                    continue
                if message.get("error_code") or message.get("error_type"):
                    raise RuntimeError("Soniox: " + " ".join(
                        str(message.get(k)) for k in ("error_code", "error_type", "error_message")
                        if message.get(k)).strip())
                for turn in self._turns.feed(message, time.monotonic()):
                    yield turn
                if message.get("finished"):
                    return
        except ConnectionClosed as closed:
            received = closed.rcvd
            if received is not None and received.code != 1000:
                raise RuntimeError(
                    f"Soniox closed the line ({received.code} {received.reason})".strip()
                ) from None
