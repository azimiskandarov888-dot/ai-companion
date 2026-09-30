"""Hearing, live — Deepgram Flux, one line for the whole conversation.

Whisper (stt.py) hears a FINISHED recording: the phone waited 1.2 s of silence
to be sure, sent the file, and only then did 0.75–1.5 s of recognising begin.
Flux hears while the person is still talking and says itself when they have
finished — by what was said and how it was said, not by a timer. Measured on
Russian through the European address (2026-09-29): «похоже, договорил» 0.34 s
after the last word, «договорил» 0.63 s after it, and a pause in the middle of
a sentence correctly not taken for the end. That «договорил» was at Deepgram's
default threshold, 0.7, which cut the owner off mid-thought; at the 0.85 used
now it comes 0.8–1.6 s after the last word (config.FLUX_EOT_THRESHOLD).
See docs/LATENCY.md.

── WHAT COMES BACK ─────────────────────────────────────────────────────────

TurnInfo messages, one conversation turn at a time (Deepgram's state machine):

    StartOfTurn     they began — always with the first words
    Update          about every 0.25 s of audio: the transcript so far
    EagerEndOfTurn  «похоже, договорил». The live channel starts writing a
                    DRAFT reply here, before it is sure.
    TurnResumed     they carried on after all — the draft is thrown away
    EndOfTurn       finished. Its transcript is always exactly the one in the
                    EagerEndOfTurn before it, which is what lets a draft be
                    kept rather than written again (Deepgram guarantees it).

Besides those: Connected, Warning, ConfigureSuccess/Failure — and FatalError,
which ends the line and is raised here rather than passed on.

── TWO THINGS THAT BITE ────────────────────────────────────────────────────

1. Flux has NO KeepAlive. About ten seconds without audio and it hangs up, so
   the line is never left without it: while he is speaking, or while the phone
   has gone quiet, the live channel sends silence (live.py).
2. `mip_opt_out=true` on every connection. Without it Deepgram may keep the
   audio to improve its models — and some of the people talking to him are
   children, about whom this app keeps nothing (young.py). Opting out forgoes
   a discount; it is not a question.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from urllib.parse import urlencode

from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed

from . import config

#: What the live channel sends Flux: 16-bit little-endian mono, 16 kHz.
RATE = 16000
#: Deepgram: «80 ms audio chunks strongly recommended» — 2,560 bytes.
CHUNK = RATE * 2 * 80 // 1000


def url(keyterms: tuple[str, ...] = ()) -> str:
    """The address of one conversation's line, with everything it is told."""
    params = [
        ("model", config.FLUX_MODEL),
        ("encoding", "linear16"),
        ("sample_rate", str(RATE)),
        ("eot_threshold", str(config.FLUX_EOT_THRESHOLD)),
        ("eot_timeout_ms", str(config.FLUX_EOT_TIMEOUT_MS)),
        ("mip_opt_out", "true"),
    ]
    if config.FLUX_EAGER_EOT_THRESHOLD:
        params.append(("eager_eot_threshold", str(config.FLUX_EAGER_EOT_THRESHOLD)))
    if "multi" in config.FLUX_MODEL and config.LANGUAGE:
        params.append(("language_hint", config.LANGUAGE.split("-")[0]))
    # Words it should expect — his name above all, which is a word the person
    # says to him and one no general model has reason to favour.
    params += [("keyterm", term) for term in keyterms if term and term.strip()]
    return f"{config.DEEPGRAM_URL}?{urlencode(params)}"


class Ears:
    """One conversation's line to Flux."""

    def __init__(self, ws: ClientConnection) -> None:
        self._ws = ws
        # The phone's audio and the silence the live channel fills gaps with
        # come from two tasks; one send at a time keeps them whole.
        self._sending = asyncio.Lock()

    @classmethod
    async def open(cls, keyterms: tuple[str, ...] = ()) -> Ears:
        if not config.DEEPGRAM_API_KEY:
            raise RuntimeError(
                "DEEPGRAM_API_KEY is not set — the live ears (Deepgram) are not configured."
            )
        ws = await connect(
            url(keyterms),
            additional_headers={"Authorization": f"Token {config.DEEPGRAM_API_KEY}"},
            open_timeout=10,
            max_size=2**22,
        )
        return cls(ws)

    async def hear(self, pcm: bytes) -> None:
        """Audio from the person, as it comes."""
        async with self._sending:
            await self._ws.send(pcm)

    async def finished(self) -> None:
        """The person says they are done — end the turn now, not in 0.6 s."""
        async with self._sending:
            await self._ws.send(json.dumps({"type": "ForceEndTurn"}))

    async def close(self) -> None:
        """Hang up. Never raises: a line that is already gone is hung up."""
        try:
            async with self._sending:
                await self._ws.send(json.dumps({"type": "CloseStream"}))
        except Exception:  # noqa: BLE001
            pass
        try:
            await self._ws.close()
        except Exception:  # noqa: BLE001
            pass

    async def events(self) -> AsyncIterator[dict]:
        """Every message from Flux, parsed, in order. Ends when the line closes
        normally; a FatalError or an abnormal close is raised, because the
        conversation cannot go on without ears and must be told so."""
        try:
            async for raw in self._ws:
                if isinstance(raw, bytes):
                    continue
                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if message.get("type") in ("FatalError", "Error"):
                    raise RuntimeError(
                        "Deepgram: " + " ".join(
                            str(message.get(k)) for k in ("code", "description") if message.get(k)
                        ).strip()
                    )
                yield message
        except ConnectionClosed as closed:
            received = closed.rcvd
            if received is not None and received.code != 1000:
                raise RuntimeError(
                    f"Deepgram closed the line ({received.code} {received.reason})".strip()
                ) from None
