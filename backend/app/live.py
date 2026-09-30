"""The live channel — he hears you while you speak, and starts on his answer
before he is sure you have finished.

The old way was a relay race: the phone waited 1.2 s of silence, sent the whole
recording, Whisper transcribed it, the brain wrote a sentence, the voice made
all of it — and only then did anything play. About 6.5 s, every turn
(docs/LATENCY.md). Here every runner starts early:

    the phone streams the microphone          → Flux hears it as it is said
    Flux: «похоже, договорил» (~0.34 s)       → a DRAFT reply is already written
    Flux: «договорил» (~0.63 s)               → the draft becomes the answer
    first comma or full stop of the answer    → the voice starts on it
    first bytes of his voice                  → straight to the phone, played

── THE WIRE ────────────────────────────────────────────────────────────────

One WebSocket per conversation, /api/live. Identity is the `Authorization`
header, as everywhere — or, from a browser, which cannot set one, the `token` in
the first message. Never in the URL: a URL is printed in every server log.

  phone → server
    {"type": "start", "token"?: "...", "hello"?: bool, "duplex"?: bool}
                                   first, once. `hello`: he greets them if they
                                   have never talked. `duplex` (true unless
                                   said otherwise): he may be interrupted —
                                   see below.
    binary                         the microphone: 16-bit mono PCM, 16 kHz
                                   (hearing.RATE), 80 ms a frame is ideal
    {"type": "played"}             everything he sent has finished playing
    {"type": "done_talking"}       the person says they have finished — end the
                                   turn now (a button, like Verity's)
    {"type": "stop"}               end of conversation

  server → phone
    {"kind": "ready", ...}         the ears are open; audio formats
    {"kind": "hearing", "text"}    what he has heard so far — captions
    {"kind": "heard", "transcript", "timing"}   their turn is over
    {"kind": "say", "text", "rate"}             a piece of his answer; the
    binary                                      raw audio for it follows:
                                                16-bit mono PCM at `rate`
    {"kind": "alarm", "alarm"}     danger — put the number under a button NOW
    {"kind": "interrupted"}        they talked over him: drop what is queued
    {"kind": "done", "reply", "farewell", "seconds_left", "timing"}
    {"kind": "asleep" | "daily_limit" | "idle" | "replaced" | "trouble", ...}

── WHAT IS WRITTEN, AND WHEN ───────────────────────────────────────────────

A draft writes NOTHING: not their line, not what memory recalled, no watcher
(main._assemble(pending=True)). A draft that is thrown away because they carried
on leaves no trace at all. When the turn is really over, main._commit writes it
all at once — and from there it is the same turn as on every other path: the
same filters, the same watcher breaking in between sentences, the same
remembering.

── HE CAN BE INTERRUPTED, AND DOES NOT HEAR HIMSELF ─────────────────────────

`duplex` (the default since 2026-09-30): the microphone stays open while he
speaks, and somebody who talks over him stops him — what the owner liked in
ChatGPT's voice, and what a conversation is. A speaker and a microphone in one
room, though: his voice comes back into the microphone. Echo cancellation in
the phone or the browser takes most of it out; what it misses, Flux hears as
HIS words, and talks_over tells those — and an «угу» — from somebody talking.

Without `duplex` (a room where he keeps hearing himself anyway): while his
voice plays, and a moment after, Flux is sent silence instead of the
microphone, and he cannot be interrupted. The end-of-turn threshold is then
more patient (config.FLUX_EOT_THRESHOLD), because a turn he ends too early
cannot be mended by carrying on.
"""

from __future__ import annotations

import asyncio
import json
import random
import re
import sys
import time
from collections import deque
from collections.abc import AsyncIterator, Iterable

from fastapi import BackgroundTasks, WebSocket

from . import allowance, brain, config, hearing, identity, memory, persona, tts, vow

#: Said the moment a question about the world is heard: the search takes
#: seconds, and a friend who is looking something up says so.
_FILLERS = ("Сейчас гляну.", "Секунду, посмотрю.", "Дай гляну.")
#: After his last sound, how long before the microphone counts again — the
#: room's echo has to die away first.
_ECHO_TAIL = 0.3
#: No audio from the phone for this long, and Flux gets silence in its place:
#: it has no KeepAlive and hangs up after about ten seconds without audio.
_FILL_AFTER = 1.0
_FILL = 0.25
#: How far ahead of what is playing the next piece of his voice is started.
_AHEAD = 1
#: A microphone frame bigger than this is not a microphone.
_MAX_FRAME = 64 * 1024
#: How long the phone has to say who it is before the line is closed.
_START_TIMEOUT = 10.0
#: The lines to the brain and the voice are opened again when somebody starts
#: talking after this long — a provider may have closed them meanwhile.
_REWARM_AFTER = 20.0
#: After his goodbye, how long the line stays open before it closes. The
#: goodbye is his reading of the moment, and the reading can be wrong: the
#: voice marked «Домой сразу. Спать.» as a goodbye, and a plain answer about
#: school (rehearsals and a scripted meeting, 2026-09-29/30). Somebody who
#: carries on talking is answered, not hung up on.
_FAREWELL_GRACE = 8.0

#: Said over him, these keep a person listening rather than take the turn…
_BACKCHANNEL = frozenset({"а", "ага", "угу", "ну", "да", "мм", "м", "хм", "эм", "э",
                          "ой", "ок", "окей", "так", "ясно", "понятно", "ладно"})
#: …and these take it at once, however short.
_STOP = frozenset({"стоп", "стой", "подожди", "подождите", "погоди", "погодите",
                   "постой", "постойте", "хватит", "извини", "слушай"})


_WORD = re.compile(r"[a-zA-Zа-яА-ЯёЁ]+")


def _words(text: str) -> list[str]:
    return [w.lower().replace("ё", "е") for w in _WORD.findall(text)]


def _stem(word: str) -> str:
    """Enough of a word to know it again in another ending — «море», «морю» —
    or half-heard back from the speaker: «автобусе», «автоматии»."""
    return word[:3] if len(word) <= 4 else word[:4]


def talks_over(heard: str, said: Iterable[str]) -> bool:
    """Is what the ears caught while he was speaking somebody talking over
    him — and not his own voice coming back from the speaker, nor a «угу»?

    Echo cancellation in the phone or browser takes his voice out of the
    microphone; what it misses, Flux hears as words — HIS words, which is how
    they are told apart. A stop word interrupts at once; otherwise two words
    of their own, or one long one. Words under three letters do not count: a
    garbled echo is made of them as easily as «а я» is."""
    his = _stems(said)
    new = [w for w in _words(heard) if _theirs(w, his)]
    if any(w in _STOP for w in new):
        return True
    return len(new) >= 2 or any(len(w) >= 5 for w in new)


def their_part(heard: str, said: Iterable[str]) -> str:
    """A turn with his own voice caught at its start — the ears glue the tail
    of his echo to what the person says next — from the person's first word
    on. Empty if none of it is theirs."""
    his = _stems(said)
    start = 0                        # where their part begins
    for m in _WORD.finditer(heard):
        word = m.group(0).lower().replace("ё", "е")
        if _theirs(word, his):
            break                    # their first word: what is before it is his
        if len(word) >= 3 and _stem(word) in his:
            start = m.end()          # still his voice; a short word after it may be theirs
    else:
        return ""
    return heard[start:].lstrip(" ,.;:!?…—–-").strip()


def _stems(said: Iterable[str]) -> set[str]:
    return {_stem(w) for text in said for w in _words(text)}


def _theirs(word: str, his: set[str]) -> bool:
    return len(word) >= 3 and word not in _BACKCHANNEL and _stem(word) not in his

#: One live channel per person. A second one — another tab, a reconnect —
#: replaces the first, so two conversations never write one diary.
_open: dict[str, Session] = {}
#: Background work (learning from the turn) that must not be garbage-collected
#: half-way through.
_later: set[asyncio.Task] = set()


class _Failed:
    def __init__(self, error: Exception) -> None:
        self.error = error


_END = object()


class Draft:
    """A reply being written — perhaps before the person has finished.

    Built from main._assemble(pending=True) when there is a transcript (their
    line, not yet theirs for keeps), or from the hello cue when there is none.
    Nothing it does is written anywhere until the session commits it.
    """

    def __init__(self, session: Session, transcript: str | None, *, web: bool = False) -> None:
        self.session = session
        self.transcript = transcript
        self.web = web
        #: What memory recalled for this reply, to be marked if it is said.
        self.marks: list = []
        self.voice: str | None = None
        #: Set once the prompt is built — the marks are complete then.
        self.ready = asyncio.Event()
        self.born = time.monotonic()
        #: When the brain was actually asked — after the prompt was built.
        self.asked: float | None = None
        self.first_words: float | None = None
        self._texts: asyncio.Queue = asyncio.Queue()
        self._task = asyncio.create_task(self._write())

    async def _write(self) -> None:
        from . import main as app_main  # the one place what he knows is decided

        try:
            stable, variable, history, voice, _watcher = await app_main._assemble(
                self.session.user_id,
                self.transcript,
                pending=self.transcript is not None,
                marks=self.marks,
                by_ear=True,
            )
            self.voice = voice
            self.ready.set()
            self.asked = time.monotonic()
            if self.web:
                # A search turn is written whole — its sources come out of the
                # finished text (brain._uncited) — and said in pieces after.
                text = await brain.generate_reply(history, stable, variable, fresh_info=True)
                self.first_words = time.monotonic()
                self._texts.put_nowait(text)
            else:
                async for text in brain.stream_reply(history, stable, variable):
                    if self.first_words is None:
                        self.first_words = time.monotonic()
                    self._texts.put_nowait(text)
            self._texts.put_nowait(_END)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 — handed to whoever reads the draft
            self.ready.set()
            self._texts.put_nowait(_Failed(e))

    def drop(self) -> None:
        self._task.cancel()

    async def texts(self) -> AsyncIterator[str]:
        """The reply as it grows: all of what is written so far at once, then
        each newer version; the last one is the finished reply. A failure of
        the brain is raised here, to the one who is waiting on it."""
        while True:
            batch = [await self._texts.get()]
            while not self._texts.empty():
                batch.append(self._texts.get_nowait())
            written = [item for item in batch if isinstance(item, str)]
            if written:
                yield written[-1]
            for item in batch:
                if isinstance(item, _Failed):
                    raise item.error
                if item is _END:
                    return


class _Voicing:
    """One piece of his answer being made into sound — started early, played in
    order. The next piece's voice is asked for while this one is still
    playing, so there is no silence between sentences."""

    def __init__(self, text: str, voice: str | None) -> None:
        self._chunks: asyncio.Queue = asyncio.Queue()
        self._task = asyncio.create_task(self._make(text, voice))

    async def _make(self, text: str, voice: str | None) -> None:
        try:
            async for rate, pcm in tts.stream(text, voice):
                self._chunks.put_nowait((rate, pcm))
            self._chunks.put_nowait(_END)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            self._chunks.put_nowait(_Failed(e))

    async def chunks(self) -> AsyncIterator[tuple[int, bytes]]:
        while True:
            item = await self._chunks.get()
            if item is _END:
                return
            if isinstance(item, _Failed):
                raise item.error
            yield item

    def cancel(self) -> None:
        self._task.cancel()


class Session:
    """One person's live conversation."""

    def __init__(self, ws: WebSocket, user_id: str, *, duplex: bool) -> None:
        self.ws = ws
        self.user_id = user_id
        self.duplex = duplex
        self.who = persona.load_persona(user_id)
        self.voice = tts.voice_for(self.who)
        self.ears: hearing.Ears | None = None
        self._send_lock = asyncio.Lock()
        self._stopping = asyncio.Event()
        self._draft: Draft | None = None
        self._reply: asyncio.Task | None = None
        #: When his audio stops playing on the phone, as best the server knows.
        self._playing_until = 0.0
        #: His voice is going out right now (a reply between its first sound and
        #: its end) — the microphone is not listened to meanwhile.
        self._voicing = False
        self._last_in = time.monotonic()
        self._last_life = time.monotonic()
        self._heard_so_far = ""
        #: Seconds of audio Flux has been sent, and when each piece arrived —
        #: to turn Flux's «the last word ended at 5.06 s» into a moment in time.
        self._clock = 0.0
        self._arrivals: deque[tuple[float, float]] = deque(maxlen=4000)
        #: When the lines to the brain and the voice were last opened ahead of need.
        self._warmed = 0.0
        #: What he has said aloud lately — to know his own voice when the
        #: microphone brings it back (talks_over).
        self._said: deque[str] = deque(maxlen=8)
        #: The turn the ears are in began while his voice was in the room — so
        #: it is judged as possibly his voice to its very end, which comes a
        #: second or so after the room goes quiet, when he is no longer audible.
        self._over_him = False
        #: The line closing after his goodbye — called off if they carry on.
        self._leaving: asyncio.Task | None = None

    # ── talking to the phone ────────────────────────────────────────────────

    async def _send(self, payload: dict) -> bool:
        """A message to the phone. False, never an exception, once it has gone."""
        try:
            async with self._send_lock:
                await self.ws.send_text(json.dumps(payload, ensure_ascii=False))
            return True
        except Exception:  # noqa: BLE001 — the phone left; the session is ending
            return False

    async def _send_audio(self, pcm: bytes, rate: int) -> None:
        now = time.monotonic()
        self._playing_until = max(self._playing_until, now) + len(pcm) / (2 * rate)
        self._voicing = True
        self._last_life = now
        async with self._send_lock:
            await self.ws.send_bytes(pcm)

    def _mic_open(self) -> bool:
        if self.duplex:
            return True
        return not self._voicing and time.monotonic() >= self._playing_until + _ECHO_TAIL

    def _audible(self) -> bool:
        """His voice is in the room — playing, or still dying away."""
        return self._voicing or time.monotonic() < self._playing_until + _ECHO_TAIL

    # ── the conversation ────────────────────────────────────────────────────

    async def run(self, *, hello: bool) -> None:
        earlier = _open.get(self.user_id)
        if earlier is not None:
            await earlier.stop({"kind": "replaced"})
        _open[self.user_id] = self
        tasks: set[asyncio.Task] = set()
        try:
            verdict = allowance.check(self.user_id)
            if not verdict.allowed:
                await self._refuse(verdict)
                return
            try:
                name = persona.persona_name(self.who)
                threshold = (config.FLUX_EOT_THRESHOLD_DUPLEX if self.duplex
                             else config.FLUX_EOT_THRESHOLD)
                self.ears = await hearing.Ears.open(
                    keyterms=(name.split()[0],) if name else (), eot_threshold=threshold)
            except Exception as e:  # noqa: BLE001
                _log("👂 the live ears (Deepgram)", e)
                await self._send({"kind": "trouble", "detail": f"the ears: {e}"})
                return
            self._warm()
            await self._send({
                "kind": "ready",
                "listen": {"format": "pcm_s16le", "rate": hearing.RATE, "frame_ms": 80},
                "speak": {"format": "pcm_s16le"},
                "duplex": self.duplex,
            })
            receiver = asyncio.create_task(self._receive())
            listener = asyncio.create_task(self._listen())
            keeper = asyncio.create_task(self._tend_line())
            stopper = asyncio.create_task(self._stopping.wait())
            tasks = {receiver, listener, keeper, stopper}
            if hello and not memory.recent_turns(self.user_id, limit=1):
                self._reply = asyncio.create_task(self._answer(Draft(self, None), time.monotonic()))
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            # A line to Deepgram that drops fails whichever task touches it
            # first — the listener, or a send of the microphone or of silence —
            # and a listener that simply ends means Deepgram hung up. Either
            # way the phone is told why, never just hung up on.
            errors = [t.exception() for t in (listener, receiver, keeper)
                      if t in done and not t.cancelled() and t.exception()]
            if errors or (listener in done and not self._stopping.is_set()):
                error = errors[0] if errors else RuntimeError("Deepgram closed the line")
                _log("👂 the live ears (Deepgram)", error)
                await self._send({"kind": "trouble", "detail": f"the ears: {error}"})
        finally:
            for task in tasks:
                if task.done() and not task.cancelled():
                    task.exception()   # read: a second failure is not a second report
                task.cancel()
            await self._halt()
            if _open.get(self.user_id) is self:
                del _open[self.user_id]
            if self.ears is not None:
                await self.ears.close()
            try:
                await self.ws.close()
            except Exception:  # noqa: BLE001 — already closed from the other side
                pass

    async def stop(self, message: dict | None = None) -> None:
        """End this conversation — saying why, if there is anything to say."""
        if message:
            await self._send(message)
        self._stopping.set()

    async def _halt(self) -> None:
        """Whatever he was doing stops, and what he got out is kept."""
        if self._draft is not None:
            self._draft.drop()
            self._draft = None
        reply = self._reply
        if reply is not None and not reply.done():
            reply.cancel()
            try:
                await reply
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass

    async def _receive(self) -> None:
        while True:
            message = await self.ws.receive()
            if message.get("type") == "websocket.disconnect":
                return
            data = message.get("bytes")
            if data is not None:
                if len(data) > _MAX_FRAME:
                    await self.stop({"kind": "trouble", "detail": "audio frame too large"})
                    return
                await self._on_audio(data)
            elif (text := message.get("text")) is not None:
                await self._on_control(text)

    async def _on_audio(self, pcm: bytes) -> None:
        pcm = pcm[: len(pcm) - len(pcm) % 2]     # whole samples only
        if not pcm or self.ears is None:
            return
        now = time.monotonic()
        self._last_in = now
        if not self._mic_open():
            pcm = bytes(len(pcm))                 # his own voice, coming back
        await self.ears.hear(pcm)
        self._clock += len(pcm) / (2 * hearing.RATE)
        self._arrivals.append((self._clock, now))

    async def _on_control(self, raw: str) -> None:
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            return
        kind = message.get("type") if isinstance(message, dict) else None
        if kind == "played":
            self._playing_until = min(self._playing_until, time.monotonic())
        elif kind == "done_talking" and self.ears is not None:
            await self.ears.finished()
        elif kind == "stop":
            self._stopping.set()

    async def _tend_line(self) -> None:
        """Silence into a quiet line, and the line closed when nobody is there."""
        while True:
            await asyncio.sleep(_FILL)
            now = time.monotonic()
            if self.ears is not None and now - self._last_in > _FILL_AFTER:
                silence = bytes(int(hearing.RATE * _FILL) * 2)
                await self.ears.hear(silence)
                self._clock += _FILL
                self._arrivals.append((self._clock, now))
            idle = now - self._last_life > config.LIVE_IDLE_SECONDS
            busy = self._reply is not None and not self._reply.done()
            if idle and not busy and self._mic_open():
                await self.stop({"kind": "idle"})
                return

    async def _listen(self) -> None:
        assert self.ears is not None
        async for message in self.ears.events():
            kind = message.get("type")
            if kind == "Warning":
                print(f"[live] Deepgram warning: {message}", file=sys.stderr, flush=True)
                continue
            if kind != "TurnInfo":
                continue
            event = message.get("event")
            text = (message.get("transcript") or "").strip()
            if event == "StartOfTurn":
                self._over_him = self.duplex and self._audible()
            if self._over_him and event != "TurnResumed":
                # The microphone is open while he speaks: what it heard may be
                # his own voice back from the speaker, or an «угу». Neither is
                # a turn. Somebody talking over him is — and he stops.
                if not talks_over(text, self._said):
                    if event in ("EagerEndOfTurn", "EndOfTurn"):
                        self._drop_draft()
                    if event == "EndOfTurn":
                        # That turn was his voice, and it is over. Not on the
                        # «похоже» before it: the same turn's EndOfTurn follows.
                        self._over_him = False
                    continue
                await self._on_start_of_turn()
                text = their_part(text, self._said)
            if text:
                self._last_life = time.monotonic()
                if event in ("StartOfTurn", "Update") and text != self._heard_so_far:
                    self._heard_so_far = text
                    await self._send({"kind": "hearing", "text": text})
            if event == "StartOfTurn":
                await self._on_start_of_turn()
            elif event == "EagerEndOfTurn":
                self._on_eager(text)
            elif event == "TurnResumed":
                self._drop_draft()
            elif event == "EndOfTurn":
                self._heard_so_far = ""
                self._over_him = False
                await self._on_end_of_turn(text, message)

    # ── turns ───────────────────────────────────────────────────────────────

    def _warm(self) -> None:
        """Open the lines to the brain and the voice while they are still
        talking, so the answer does not start with a handshake."""
        self._warmed = time.monotonic()

        async def both() -> None:
            await asyncio.gather(brain.warm(), tts.warm(), return_exceptions=True)

        _track(asyncio.create_task(both()))

    async def _on_start_of_turn(self) -> None:
        """They are talking. Whatever he was about to say gives way — and over
        headphones, whatever he is saying."""
        if time.monotonic() - self._warmed > _REWARM_AFTER:
            self._warm()
        if self._leaving is not None:
            self._leaving.cancel()   # he said goodbye, and they are still talking
            self._leaving = None
        reply = self._reply
        if reply is None or reply.done() or reply.cancelling():
            return
        if self._voicing and not self.duplex:
            return   # cannot be them: the microphone is closed while he speaks
        reply.cancel()
        self._playing_until = time.monotonic()
        await self._send({"kind": "interrupted"})

    def _on_eager(self, text: str) -> None:
        """«Похоже, договорил» — start writing, in case they have."""
        if not text or brain.wants_fresh_info(text):
            return   # a search is seconds and money; not on a guess
        if self._draft is not None and self._draft.transcript == text:
            return
        self._drop_draft()
        if allowance.check(self.user_id).allowed:
            self._draft = Draft(self, text)

    def _drop_draft(self) -> None:
        if self._draft is not None:
            self._draft.drop()
            self._draft = None

    async def _on_end_of_turn(self, text: str, message: dict) -> None:
        ended = time.monotonic()
        if not text:
            self._drop_draft()
            return
        # Before any paid work, exactly as /api/talk: did that sound like a
        # person, is he awake, has he got the day left?
        allowance.note_turn(self.user_id, text)
        if allowance.is_asleep(self.user_id):
            self._drop_draft()
            await self.stop({"kind": "asleep", "transcript": text,
                             "seconds_left": allowance.seconds_left(self.user_id)})
            return
        verdict = allowance.check(self.user_id)
        if not verdict.allowed:
            self._drop_draft()
            await self._refuse(verdict)
            return
        if self._reply is not None and not self._reply.done():
            self._reply.cancel()
        web = brain.wants_fresh_info(text)
        draft = self._draft
        reused = draft is not None and draft.transcript == text and not web
        if not reused:
            self._drop_draft()
            draft = Draft(self, text, web=web)
        self._draft = None
        speech_end = self._speech_end(message)
        await self._send({
            "kind": "heard",
            "transcript": text,
            "timing": {"end_of_turn": _after(ended, speech_end), "draft_reused": reused},
        })
        self._reply = asyncio.create_task(
            self._answer(draft, ended, speech_end=speech_end, reused=reused)
        )

    def _speech_end(self, message: dict) -> float | None:
        """When — on this server's clock — the last word of the turn arrived."""
        words = message.get("words") or []
        try:
            said_until = float(words[-1]["end"])
        except (IndexError, KeyError, TypeError, ValueError):
            return None
        for clock, arrived in self._arrivals:
            if clock >= said_until:
                return arrived
        return None

    # ── his answer ──────────────────────────────────────────────────────────

    async def _answer(self, draft: Draft, ended: float, *, speech_end: float | None = None,
                      reused: bool = False) -> None:
        """Say the draft, piece by piece, and keep what was said.

        The same turn as every other path's: the vows between pieces, the
        watcher breaking in between sentences, the farewell, the body, the
        remembering — see main._speak_as_he_thinks, which this mirrors."""
        from . import main as app_main

        user_id = self.user_id
        hello = draft.transcript is None
        start = speech_end or ended
        timing: dict = {"draft_reused": reused}
        if reused:
            timing["draft_started"] = _after(draft.born, start)
        spoken: list[str] = []
        sounded = False
        dropped = False
        watcher: asyncio.Task | None = None
        final = ""
        ahead: deque[tuple[str, _Voicing]] = deque()
        pieces: asyncio.Queue = asyncio.Queue()
        cutter: asyncio.Task | None = None

        async def cut() -> None:
            nonlocal final
            committed, first = 0, True
            try:
                async for text in draft.texts():
                    final = text
                    while True:
                        tail = text[committed:]
                        at = tts.ready_split(tail, first=first)
                        if not at:
                            break
                        committed += at
                        piece = tail[:at].strip()
                        if piece:
                            if first:
                                timing["first_piece"] = _after(time.monotonic(), start)
                            await pieces.put(piece)
                            first = False
                for piece in tts.speakable_chunks(final[committed:]):
                    await pieces.put(piece)
            finally:
                await pieces.put(None)

        async def ready_ahead(wait: bool) -> bool:
            """Start the voice on the next piece if it is written — or, with
            `wait`, wait for it. False once there is nothing left to say."""
            nonlocal dropped
            while len(ahead) < _AHEAD or (wait and not ahead):
                if wait and not ahead:
                    piece = await pieces.get()
                else:
                    try:
                        piece = pieces.get_nowait()
                    except asyncio.QueueEmpty:
                        return True
                if piece is None:
                    pieces.put_nowait(None)   # stays the end for anyone asking again
                    return bool(ahead)
                # THE TWO THINGS HE NEVER SAYS, checked before they are said.
                if slip := vow.broken(piece):
                    vow.note(user_id, slip, piece)
                    dropped = True
                    continue
                # Nothing but a stage direction: nothing to say.
                if not tts.audible(piece):
                    continue
                ahead.append((piece, _Voicing(piece, voice)))
            return True

        def spent() -> None:
            if not hello:
                allowance.spend(user_id, time.monotonic() - ended)

        voice = self.voice
        try:
            await draft.ready.wait()
            voice = draft.voice or self.voice
            if not hello:
                # From here it is their turn for keeps.
                watcher = app_main._commit(user_id, draft.transcript, draft.marks)
            if draft.web:
                filler = random.choice(_FILLERS)
                if await self._speak_line(filler, voice):
                    spoken.append(filler)
                    sounded = True
            cutter = asyncio.create_task(cut())
            breaking, verdict = "", None
            while await ready_ahead(wait=True):
                piece, voicing = ahead.popleft()
                announced = False
                async for rate, pcm in voicing.chunks():
                    if not announced:
                        announced = True
                        self._said.append(tts.spoken(piece))
                        await self._send({"kind": "say", "text": tts.spoken(piece), "rate": rate})
                        if "first_audio" not in timing:
                            timing["first_audio"] = _after(time.monotonic(), start)
                            timing["brain_asked"] = _after(draft.asked, start)
                            timing["first_words"] = _after(draft.first_words, start)
                    await self._send_audio(pcm, rate)
                    sounded = True
                    await ready_ahead(wait=False)
                spoken.append(piece)
                if watcher is not None:
                    # BETWEEN SENTENCES: has the watcher found something that
                    # cannot wait for him to finish?
                    breaking, verdict = await app_main._breaking_in(watcher, user_id, wait=False)
                    if breaking:
                        break
            if breaking:
                cutter.cancel()
            else:
                await cutter   # a failure of the brain surfaces here
            for _, voicing in ahead:
                voicing.cancel()
            ahead.clear()
            if watcher is not None and not breaking:
                breaking, verdict = await app_main._breaking_in(watcher, user_id, wait=True)

            if breaking:
                # The button before the words — see main._alarm.
                if alarm := app_main._alarm(verdict, user_id):
                    await self._send({"kind": "alarm", "alarm": alarm})
                said = app_main._body(user_id, app_main._farewell(" ".join(spoken).strip())[0])
                await self._speak_line(breaking, voice)
                reply, leaving = f"{said} {breaking}".strip(), False
            else:
                reply, leaving = app_main._farewell(final.strip())
                reply, _slip = vow.keep(reply)
                if dropped and not spoken and not reply:
                    reply = vow.LAST_RESORT
                    sounded = await self._speak_line(reply, voice) or sounded
                if draft.web and spoken and spoken[0] in _FILLERS:
                    reply = f"{spoken[0]} {reply}".strip()
                reply = app_main._body(user_id, reply)
            self._remember(draft, reply, leaving, sounded)
            spent()
            timing["done"] = _after(time.monotonic(), start)
            await self._send({
                "kind": "done",
                "reply": reply,
                "farewell": leaving,
                "seconds_left": allowance.seconds_left(user_id),
                "timing": timing,
            })
            if leaving:
                self._leave_after_playing()
        except asyncio.CancelledError:
            self._give_up(cutter, ahead, draft)
            said = " ".join(spoken).strip()
            if said:
                kept, _slip = vow.keep(app_main._body(user_id, app_main._farewell(said)[0]))
                self._remember(draft, kept, False, sounded)
            spent()
            raise
        except Exception as e:  # noqa: BLE001 — a turn cannot raise at the phone
            self._give_up(cutter, ahead, draft)
            _log("🧠 the brain / 🗣️ the voice (live)", e)
            said = " ".join(spoken).strip()
            if said:
                kept, _slip = vow.keep(app_main._body(user_id, app_main._farewell(said)[0]))
                self._remember(draft, kept, False, sounded)
            spent()
            await self._send({"kind": "trouble", "detail": str(e)})
        finally:
            self._voicing = False

    def _give_up(self, cutter: asyncio.Task | None, ahead: deque, draft: Draft) -> None:
        if cutter is not None:
            cutter.cancel()
        for _, voicing in ahead:
            voicing.cancel()
        ahead.clear()
        draft.drop()

    def _remember(self, draft: Draft, reply: str, leaving: bool, sounded: bool) -> None:
        """Remember what he said — as /api/hello does for a greeting (only once it
        was heard), as every turn does for an answer (main._remember)."""
        if not reply:
            return
        from . import main as app_main

        if draft.transcript is None:
            if sounded:
                memory.log_turn(self.user_id, "assistant", reply)
            return
        work = BackgroundTasks()
        app_main._remember(self.user_id, draft.transcript, reply, work, farewell=leaving)
        _run_later(work)

    async def _speak_line(self, text: str, voice: str | None) -> bool:
        """A line said as it is — a filler, an alarm, a goodnight. True if any
        of it was heard."""
        sounded = False
        for piece in tts.speakable_chunks(text):
            if not tts.audible(piece):
                continue
            announced = False
            async for rate, pcm in tts.stream(piece, voice):
                if not announced:
                    announced = True
                    self._said.append(tts.spoken(piece))
                    await self._send({"kind": "say", "text": tts.spoken(piece), "rate": rate})
                await self._send_audio(pcm, rate)
                sounded = True
        return sounded

    async def _refuse(self, verdict: allowance.Verdict) -> None:
        """He cannot talk now — asleep, or the day is spent — and says so in his
        own voice, never as an error."""
        try:
            await self._speak_line(verdict.reason, self.voice)
        except Exception as e:  # noqa: BLE001 — the words are sent anyway
            _log("🗣️ the voice (live)", e)
        self._voicing = False
        await self.stop({"kind": verdict.code, "reply": verdict.reason,
                         "seconds_left": verdict.seconds_left})

    def _leave_after_playing(self) -> None:
        """A goodbye: the line closes once the phone has played it and nobody
        has said anything more for _FAREWELL_GRACE — if they do, it stays open."""
        async def later() -> None:
            await asyncio.sleep(max(0.0, self._playing_until - time.monotonic()) + _FAREWELL_GRACE)
            self._stopping.set()

        if self._leaving is not None:
            self._leaving.cancel()
        self._leaving = asyncio.create_task(later())
        _track(self._leaving)


def _after(moment: float | None, start: float | None) -> float | None:
    """Seconds from `start` to `moment`, or None when either is unknown — a
    measurement must never cost anybody their answer."""
    if moment is None or start is None:
        return None
    return round(moment - start, 3)


def _log(stage: str, error: BaseException | None) -> None:
    print(f"\n  ✗ {stage} failed\n    {error}\n", file=sys.stderr, flush=True)


def _track(task: asyncio.Task) -> None:
    _later.add(task)
    task.add_done_callback(_later.discard)


def _run_later(work: BackgroundTasks) -> None:
    """The learning after a turn — never in the conversation's way, and never
    silent when it fails."""
    async def run() -> None:
        try:
            await work()
        except Exception as e:  # noqa: BLE001
            _log("learning after a live turn", e)

    _track(asyncio.create_task(run()))


async def serve(ws: WebSocket) -> None:
    """/api/live: who is calling, then their conversation."""
    await ws.accept()
    try:
        first = await asyncio.wait_for(ws.receive(), timeout=_START_TIMEOUT)
        start = json.loads(first.get("text") or "{}")
        if not isinstance(start, dict) or start.get("type") != "start":
            raise ValueError("the first message must be {\"type\": \"start\"}")
    except Exception as e:  # noqa: BLE001 — a caller that never says hello is hung up on
        try:
            await ws.send_text(json.dumps({"kind": "trouble", "detail": f"start: {e}"}))
            await ws.close()
        except Exception:  # noqa: BLE001
            pass
        return
    header = ws.headers.get("authorization")
    given = start.get("token")
    token = header if header else (f"Bearer {given}" if isinstance(given, str) and given else None)
    user_id = identity.user_id_from_token(token)
    session = Session(ws, user_id, duplex=start.get("duplex") is not False)
    await session.run(hello=bool(start.get("hello")))
