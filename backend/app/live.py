"""The live channel — he hears you while you speak, and starts on his answer
before he is sure you have finished.

The old way was a relay race: the phone waited 1.2 s of silence, sent the whole
recording, Whisper transcribed it, the brain wrote a sentence, the voice made
all of it — and only then did anything play. About 6.5 s, every turn
(docs/LATENCY.md). Here every runner starts early:

    the phone streams the microphone          → Flux hears it as it is said
    somebody starts talking                   → the brain reads ahead (prewarm),
                                                if it has been quiet a while
    Flux: «похоже, договорил» (~0.37 s)       → a DRAFT reply is already being
                                                written — by the brain alone
    Flux: «договорил» (~0.64 s)               → the draft becomes the answer, and
                                                only now is any of it voiced
    its first pause («Ого,»)                  → that piece to the voice (or ready-made)
    first bytes of his voice                  → straight to the phone, played

── THINKING WHILE THEY TALK, AND WHAT IT COSTS ──────────────────────────────

The owner, 2026-10-05, of drafting at every pause: «будет тратить больше
денег и лишней энергии». Measured on the real ears (Flux, five phrases, two
with pauses inside): a draft at every 0.2 s pause began 69 replies for five
turns, against 10 begun at «похоже, договорил». Flux sends the words about
every quarter second, the last of them ending ~0.16 s behind the voice, so
«0.2 s since the last word» was true between nearly any two of its messages.
Every draft is the whole prompt, paid for. So a draft is begun only where the ears judge,
by meaning and intonation, that the person may have finished — and at most
_GUESSES times a turn — as Deepgram, LiveKit and Pipecat all do.

And none of it is voiced until the turn is certain: on all five, «договорил»
came before the draft had written its first piece — waiting for it cost
nothing, and a guess thrown away costs no voice (LiveKit's own default).

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

from . import (allowance, aloud, brain, config, first_sound, hearing, identity, lang, memory,
               persona, tts, voices, vow)

#: Said the moment a question about the world is heard: the search takes
#: seconds, and a friend who is looking something up says so.
_FILLERS = ("Сейчас гляну.", "Секунду, посмотрю.", "Дай гляну.")
_FILLERS_EN = ("Let me look.", "One sec, I'll check.", "Hang on, let me see.")
#: After his last sound, how long before the microphone counts again — the
#: room's echo has to die away first.
_ECHO_TAIL = 0.3
#: No audio from the phone for this long, and Flux gets silence in its place:
#: it has no KeepAlive and hangs up after about ten seconds without audio.
_FILL_AFTER = 1.0
_FILL = 0.25
#: How far ahead of what is playing the next piece of his voice is started:
#: one for a voice whose first sound is quick (Fish, ~0.45 s); two for one that
#: takes longer to begin (Gemini, 0.6–0.9 s; tts.slow_start) — while «Ого,»
#: plays, the rest of the sentence is being made.
_AHEAD = 1
_AHEAD_WHOLE = 2
#: On a voice rationed by the minute (tts.limited — ten requests a minute on
#: Google's first paid tier, measured 2026-10-07) an answer is voiced in as
#: few requests as it can be: its first piece, then the rest of it at once
#: when it is written, not every sentence on its own — two requests for most
#: answers, where it used to be three or four. A rest still being written
#: past this many letters is voiced as far as it goes: a long answer must
#: not become a long silence.
_REST_AT_ONCE = 300
#: …and the short piece after a ready-made first word («Ох…» — «понимаю.»)
#: only while this many requests are left in the minute; with fewer, the rest
#: follows «Ох…» whole, after a longer pause.
_ROOM_FOR_SHORT = 5
#: Drafts begun on a guess («похоже, договорил») in one turn, at most — then
#: only «договорил» begins one. LiveKit's default too (max_retries 3): a turn
#: that keeps stopping and going on would otherwise be paid for again at
#: every stop.
_GUESSES = 3
#: A microphone frame bigger than this is not a microphone.
_MAX_FRAME = 64 * 1024
#: How long the phone has to say who it is before the line is closed.
_START_TIMEOUT = 10.0
#: The lines to the brain and the voice are opened again when somebody starts
#: talking after this long — a provider may have closed them meanwhile.
_REWARM_AFTER = 20.0
#: The brain reads ahead (brain.prewarm) when somebody starts talking and it
#: has not been asked anything for this long — on the first turn, and after a
#: pause long enough for the host to have forgotten the instructions. In a
#: conversation that is going, every turn keeps them warm by itself.
_READ_AHEAD_AFTER = 45.0
#: After his goodbye, how long the line stays open before it closes. The
#: goodbye is his reading of the moment, and the reading can be wrong: the
#: voice marked «Домой сразу. Спать.» as a goodbye, and a plain answer about
#: school (rehearsals and a scripted meeting, 2026-09-29/30). Somebody who
#: carries on talking is answered, not hung up on.
_FAREWELL_GRACE = 8.0

#: Said over him, these keep a person listening rather than take the turn…
_BACKCHANNEL = frozenset({"а", "ага", "угу", "ну", "да", "мм", "м", "хм", "эм", "э",
                          "ой", "ок", "окей", "так", "ясно", "понятно", "ладно",
                          # and in an English conversation (lang.py)
                          "yeah", "yep", "yes", "uh", "huh", "mm", "mhm", "hmm", "um", "oh",
                          "ok", "okay", "right", "sure", "true", "wow", "cool", "nice", "ah",
                          "aha"})
#: …and these take it at once, however short.
_STOP = frozenset({"стоп", "стой", "подожди", "подождите", "погоди", "погодите",
                   "постой", "постойте", "хватит", "извини", "слушай",
                   "stop", "wait", "hold", "hang", "sorry", "listen", "excuse", "hey"})


_WORD = re.compile(r"[a-zA-Zа-яА-ЯёЁ]+")


def _first_cut(voice: str | None, text: str) -> int:
    """Where his answer's first piece ends: at one of his ready-made first
    words, however short (first_sound.opener) — it plays at once — or at his
    first pause (tts.first_pause). 0 for «not yet»."""
    return first_sound.opener(voice, text) or tts.first_pause(text)


def _same(a: str | None, b: str | None) -> bool:
    """The same words, whatever the punctuation and capitals Flux gave them."""
    return a is not None and b is not None and [
        w.lower().replace("ё", "е") for w in _WORD.findall(a)] == [
        w.lower().replace("ё", "е") for w in _WORD.findall(b)]


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
    Nothing it does is written anywhere until the session commits it — and
    nothing of it is voiced until then either (see the module docstring): the
    answer cuts and voices it once their turn is certain (Session._answer).
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
        #: When his first piece (up to his first pause) was written — set or
        #: not by the time their turn is certain, it says whether waiting for
        #: that certainty kept his voice waiting (timing «head_waited»).
        self.opened: float | None = None
        #: The reply so far, for whoever reads it (texts()).
        self._latest = ""
        self._version = 0
        self._finished = False
        self._error: Exception | None = None
        self._waiters: set[asyncio.Event] = set()
        #: How he says it aloud — one per reply.
        self.speaker = aloud.Speaker(young=aloud.young(session.who))
        self._task = asyncio.create_task(self._write())

    @property
    def opening(self) -> str:
        """His first piece, as far as it is written — up to his first pause —
        or "" while it is not."""
        at = _first_cut(self.voice or self.session.voice, self._latest)
        return self._latest[:at].strip() if at else ""

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
                self._publish(text)
            else:
                async for text in brain.stream_reply(
                        history, stable, variable, hedge_after=config.BRAIN_HEDGE_AFTER or None):
                    if self.first_words is None:
                        self.first_words = time.monotonic()
                    self._publish(text)
            self._finish()
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 — handed to whoever reads the draft
            self.ready.set()
            self._finish(e)

    def _publish(self, text: str) -> None:
        self._latest = text
        self._version += 1
        if self.opened is None and _first_cut(self.voice or self.session.voice, text):
            self.opened = time.monotonic()
        self._wake()

    def _finish(self, error: Exception | None = None) -> None:
        self._error = error
        self._finished = True
        self._wake()

    def _wake(self) -> None:
        for waiter in list(self._waiters):
            waiter.set()

    def drop(self) -> None:
        self._task.cancel()

    async def texts(self) -> AsyncIterator[str]:
        """The reply as it grows: all of what is written so far at once, then
        each newer version; the last one is the finished reply. A failure of
        the brain is raised here, to the one who is waiting on it."""
        seen = 0
        while True:
            if self._version > seen:
                seen = self._version
                yield self._latest
                continue
            if self._finished:
                if self._error is not None:
                    raise self._error
                return
            woken = asyncio.Event()
            self._waiters.add(woken)
            try:
                await woken.wait()
            finally:
                self._waiters.discard(woken)


class _Voicing:
    """One piece of his answer being made into sound — started early, played in
    order. The next piece's voice is asked for while this one is still
    playing, so there is no silence between sentences."""

    def __init__(self, text: str, voice: str | None, *, made: tuple[int, bytes] | None = None) -> None:
        self._chunks: asyncio.Queue = asyncio.Queue()
        #: Its first sound is in — or it has failed, which is as ready to play.
        self.sounding = asyncio.Event()
        #: When the voice was asked, and when its first sound came — the two
        #: moments of the voice's own share of the wait (docs/LATENCY.md).
        self.asked_at = time.monotonic()
        self.first_at: float | None = None
        if made is not None:
            self.first_at = self.asked_at
            # Ready-made in his voice (first_sound.REACTIONS): nothing to wait for.
            self._chunks.put_nowait(made)
            self._chunks.put_nowait(_END)
            self.sounding.set()
            self._task = asyncio.create_task(asyncio.sleep(0))
        else:
            self._task = asyncio.create_task(self._make(text, voice))

    @classmethod
    def first(cls, text: str, voice: str | None) -> _Voicing:
        """The voice of an answer's FIRST piece: ready-made when it is one of
        his usual first words, made now when it is not."""
        return cls(text, voice, made=first_sound.reaction(voice, text))

    async def _make(self, text: str, voice: str | None) -> None:
        try:
            async for rate, pcm in tts.stream(text, voice):
                if self.first_at is None:
                    self.first_at = time.monotonic()
                self._chunks.put_nowait((rate, pcm))
                self.sounding.set()
            self._chunks.put_nowait(_END)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            self._chunks.put_nowait(_Failed(e))
        finally:
            self.sounding.set()

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
        self.who = voices.ensure(user_id)   # his own voice, given once and kept
        self.voice = tts.voice_for(self.who)
        #: An older friend breathes more before he answers (first_sound.SHARES).
        self._older = (voices.years(self.who) or 0) >= first_sound.OLDER_FROM
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
        #: When the brain was last asked to read this conversation — a draft,
        #: or reading ahead (_read_ahead).
        self._read_at = 0.0
        #: What he has said aloud lately — to know his own voice when the
        #: microphone brings it back (talks_over).
        self._said: deque[str] = deque(maxlen=8)
        #: The turn the ears are in began while his voice was in the room — so
        #: it is judged as possibly his voice to its very end, which comes a
        #: second or so after the room goes quiet, when he is no longer audible.
        self._over_him = False
        #: The line closing after his goodbye — called off if they carry on.
        self._leaving: asyncio.Task | None = None
        #: His last sound (first_sound.py): when it went out, and which it was.
        self._sound_at = 0.0
        self._sound_text = ""
        self._rng = random.Random()
        #: His words are going out: no sound of his may cut into them.
        self._answering_aloud = False
        #: Drafts begun on a guess in the turn they are in (_GUESSES).
        self._guesses = 0

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

    async def _send_sound(self, text: str, rate: int, pcm: bytes) -> bool:
        """One of his sounds (first_sound.py), whole and at once — never into
        the middle of his words, which take the line first. It plays for a
        known length, so it marks the room as his for exactly that long
        without holding the microphone shut after it (_voicing)."""
        async with self._send_lock:
            if self._answering_aloud:
                return False
            now = time.monotonic()
            try:
                await self.ws.send_text(json.dumps({"kind": "say", "text": text, "rate": rate},
                                                   ensure_ascii=False))
                await self.ws.send_bytes(pcm)
            except Exception:  # noqa: BLE001 — the phone left
                return False
            self._playing_until = max(self._playing_until, now) + len(pcm) / (2 * rate)
            self._last_life = now
            if _WORD.search(text) and text not in (first_sound.BREATH_SHOWN, first_sound.BREATH_SHOWN_EN):
                self._said.append(text)   # a word of his, to know again from the speaker
            self._sound_at, self._sound_text = now, text
        return True

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
            greeting = hello and not memory.recent_turns(self.user_id, limit=1)
            if not greeting:
                self._read_ahead()   # his hello is itself the first reading
            if tts.configured():
                first_sound.prepare(self.voice)   # in his voice, while they start talking
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
            if greeting:
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
                        self._guesses = 0
                    continue
                await self._on_start_of_turn()
                text = their_part(text, self._said)
            if text:
                self._last_life = time.monotonic()
                if event in ("StartOfTurn", "Update") and text != self._heard_so_far:
                    self._heard_so_far = text
                    await self._send({"kind": "hearing", "text": text})
            if (event in ("StartOfTurn", "Update") and self._draft is not None
                    and not _same(self._draft.transcript, text)):
                self._drop_draft()   # they said more: a draft for a turn that did not happen
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
                self._guesses = 0

    # ── turns ───────────────────────────────────────────────────────────────

    def _warm(self) -> None:
        """Open the lines to the brain and the voice while they are still
        talking, so the answer does not start with a handshake."""
        self._warmed = time.monotonic()

        async def both() -> None:
            lines = _AHEAD_WHOLE if tts.slow_start() else _AHEAD   # as many as _answer keeps going
            await asyncio.gather(brain.warm(), tts.warm(lines), return_exceptions=True)

        _track(asyncio.create_task(both()))

    def _read_ahead(self) -> None:
        """The brain reads his instructions and the conversation so far while
        they are talking, so that their last word is all it has left to read
        (brain.prewarm, main.prewarm)."""
        from . import main as app_main

        self._read_at = time.monotonic()
        _track(asyncio.create_task(app_main.prewarm(self.user_id)))

    async def _on_start_of_turn(self) -> None:
        """They are talking. Whatever he was about to say gives way — and over
        headphones, whatever he is saying."""
        if time.monotonic() - self._warmed > _REWARM_AFTER:
            self._warm()
        if time.monotonic() - self._read_at > _READ_AHEAD_AFTER:
            self._read_ahead()
        if self._leaving is not None:
            self._leaving.cancel()   # he said goodbye, and they are still talking
            self._leaving = None
        reply = self._reply
        if reply is None or reply.done() or reply.cancelling():
            return
        if self._voicing and not self.duplex:
            return   # cannot be them: the microphone is closed while he speaks
        reply.cancel()
        self._warm()   # what he was saying took its lines with it (_drop_draft)
        self._playing_until = time.monotonic()
        await self._send({"kind": "interrupted"})

    def _think(self, text: str) -> None:
        """A draft for what they have said — in case it is all they will say.
        The brain only (Draft), and at most _GUESSES a turn."""
        if not text or brain.wants_fresh_info(text):
            return   # a search is seconds and money; not on a guess
        if self._guesses >= _GUESSES:
            return   # «договорил» will begin one
        self._drop_draft()
        if allowance.check(self.user_id).allowed:
            self._guesses += 1
            self._draft = Draft(self, text)
            self._read_at = time.monotonic()

    def _on_eager(self, text: str) -> None:
        """«Похоже, договорил» — writing, in case they have; and, as a listener
        does in a pause, perhaps say «м-м»."""
        self._sound_in_pause(text)
        if self._draft is not None and _same(self._draft.transcript, text):
            return
        self._think(text)

    def _sound_in_pause(self, text: str) -> None:
        """A listener's «м-м» into their pause (first_sound.py) — only where they
        can carry on over it: with the microphone closed while he makes a
        sound, their next words would be lost."""
        if not (self.duplex and first_sound.in_pause(text)) or self._audible():
            return
        if self._reply is not None and not self._reply.done():
            return
        if time.monotonic() - self._sound_at < first_sound.SPACING:
            return
        if self._rng.random() >= first_sound.CHANCE_IN_PAUSE:
            return
        made = first_sound.pick(self.voice, "listening", self._rng, avoid=self._sound_text)
        if made:
            _track(asyncio.create_task(self._send_sound(*made)))

    async def _sound_at_end(self, transcript: str) -> None:
        """Their turn is over: his first sound, at once — unless the «м-м» that
        went into their last pause a moment ago already was it."""
        kind = first_sound.at_end(transcript)
        if kind is None or time.monotonic() - self._sound_at < first_sound.SPACING_AT_END:
            return
        made = first_sound.choose(self.voice, kind, self._rng, older=self._older,
                                  avoid=self._sound_text)
        if made:
            await self._send_sound(*made)

    async def _sound_if_late(self, ended: float, transcript: str) -> None:
        """His words still not there LATE seconds after their turn: one more sound."""
        if first_sound.LATE is None:
            return
        await asyncio.sleep(max(0.0, ended + first_sound.LATE - time.monotonic()))
        if self._answering_aloud or time.monotonic() < self._playing_until:
            return
        made = first_sound.pick(self.voice, first_sound.at_end(transcript) or "statement",
                                self._rng, avoid=self._sound_text)
        if made:
            await self._send_sound(*made)

    def _drop_draft(self) -> None:
        """A draft that will not be said, thrown away — and the line to the
        brain opened again at once, while they talk. A reply cut off half-way
        takes its connection with it (HTTP/1.1 keeps one only for a reply read
        to its end), and the next draft would begin with a handshake: +0.2 s
        from Tashkent (measured 2026-10-05). The opening is free (brain.warm)."""
        if self._draft is not None:
            self._draft.drop()
            self._draft = None
            _track(asyncio.create_task(brain.warm()))

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
        reused = draft is not None and _same(draft.transcript, text) and not web
        if not reused:
            self._drop_draft()
            draft = Draft(self, text, web=web)
            self._read_at = time.monotonic()
        self._draft = None
        speech_end = self._speech_end(message)
        await self._send({
            "kind": "heard",
            "transcript": text,
            # «guesses»: drafts begun before this turn was certain — what the
            # thinking ahead cost, the one that became the answer included.
            "timing": {"end_of_turn": _after(ended, speech_end), "draft_reused": reused,
                       "guesses": self._guesses},
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
        #: (what he means, how he says it aloud, its voice being made) — see aloud.py.
        ahead: deque[tuple[str, str, _Voicing]] = deque()
        #: One for a voice that streams, two for one that makes pieces whole.
        keep_ahead = _AHEAD_WHOLE if tts.slow_start() else _AHEAD
        #: Requests to the voice are counted by the minute (_REST_AT_ONCE).
        rationed = tts.limited()
        speaker = draft.speaker
        pieces: asyncio.Queue = asyncio.Queue()
        cutter: asyncio.Task | None = None
        late: asyncio.Task | None = None
        #: A sound of his since their last word (first_sound.py) that the first
        #: words of the answer must not say again.
        echoed = ""

        async def cut() -> None:
            nonlocal final
            committed, first = 0, True
            #: The piece after a ready-made first word is the voice's first:
            #: cut as short, so that «Ох…» is not followed by a silence while
            #: a whole sentence is written and made.
            short = False
            try:
                async for text in draft.texts():
                    final = text
                    while True:
                        tail = text[committed:]
                        at = (_first_cut(voice, tail) if first
                              else tts.first_pause(tail) if short
                              else 0 if rationed and len(tail) < _REST_AT_ONCE
                              else tts.ready_split(tail, first=False))
                        if not at:
                            break
                        committed += at
                        piece = tail[:at].strip()
                        if first and echoed:
                            piece = first_sound.without_repeat(piece, echoed).strip()
                        if piece:
                            if first:
                                timing["first_piece"] = _after(time.monotonic(), start)
                            await pieces.put(piece)
                            short = (first and first_sound.opener(voice, tail) == at
                                     and (not rationed or tts.room() >= _ROOM_FOR_SHORT))
                            first = False
                for piece in tts.speakable_chunks(final[committed:]):
                    if first and echoed:
                        piece = first_sound.without_repeat(piece, echoed).strip()
                    if piece:
                        await pieces.put(piece)
                        first = False
            finally:
                await pieces.put(None)

        def accept(piece: str) -> tuple[str, str] | None:
            """(what he means, how he says it aloud) — or None for a piece he
            must not say, or that has nothing in it to say."""
            nonlocal dropped
            # THE TWO THINGS HE NEVER SAYS, checked before they are said.
            if slip := vow.broken(piece):
                vow.note(user_id, slip, piece)
                dropped = True
                return None
            # Nothing but a stage direction: nothing to say.
            if not tts.audible(piece):
                return None
            return piece, speaker.say(piece)

        async def ready_ahead(wait: bool) -> bool:
            """Start the voice on the next piece if it is written — or, with
            `wait`, wait for it. False once there is nothing left to say."""
            while len(ahead) < keep_ahead or (wait and not ahead):
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
                if (taken := accept(piece)) is None:
                    continue
                meant, heard = taken
                opening = not spoken and not ahead and not sounded
                # Rationed: whatever else is written already goes with it, in
                # one request — never into his first piece, which may be ready-made.
                while rationed and not opening:
                    try:
                        more = pieces.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                    if more is None:
                        pieces.put_nowait(None)
                        break
                    if (extra := accept(more)) is not None:
                        meant, heard = f"{meant} {extra[0]}", f"{heard} {extra[1]}"
                ahead.append((meant, heard, _Voicing.first(heard, voice) if opening else _Voicing(heard, voice)))
            return True

        def spent() -> None:
            if not hello:
                allowance.spend(user_id, time.monotonic() - ended)

        voice = self.voice
        try:
            opening = draft.opening   # his first piece, if the brain has got that far
            if opening and first_sound.reaction(voice, opening) is not None:
                timing["head_ready"] = True   # written, and ready-made: no «м-м» before it
            elif not hello and not draft.web:
                # Before anything is waited on: the sound IS the not waiting.
                # A sound the answer opens with is taken off the answer (cut):
                # nothing of it is voiced yet, so it still can be.
                await self._sound_at_end(draft.transcript)
                late = asyncio.create_task(self._sound_if_late(ended, draft.transcript))
            if self._sound_at >= start:
                echoed = self._sound_text
                timing["first_sound"] = _after(self._sound_at, start)
            await draft.ready.wait()
            voice = draft.voice or self.voice
            if not hello:
                # From here it is their turn for keeps.
                watcher = app_main._commit(user_id, draft.transcript, draft.marks)
            if draft.web:
                filler = random.choice(lang.pick(_FILLERS, _FILLERS_EN))
                if await self._speak_line(filler, voice):
                    spoken.append(filler)
                    sounded = True
            cutter = asyncio.create_task(cut())
            breaking, verdict = "", None
            while await ready_ahead(wait=True):
                piece, heard, voicing = ahead.popleft()
                announced = False
                async for rate, pcm in voicing.chunks():
                    if not announced:
                        announced = True
                        self._answering_aloud = True   # no «м-м» into his words from here
                        if late is not None:
                            late.cancel()
                        self._said.append(tts.spoken(heard))
                        await self._send({"kind": "say", "text": tts.spoken(heard), "rate": rate})
                        if "first_audio" not in timing:
                            timing["first_audio"] = _after(time.monotonic(), start)
                            timing["brain_asked"] = _after(draft.asked, start)
                            timing["first_words"] = _after(draft.first_words, start)
                            timing["voice_asked"] = _after(voicing.asked_at, start)
                            timing["voice_ready"] = _after(voicing.first_at, start)
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
            for *_, voicing in ahead:
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
                    reply = vow.last_resort()
                    sounded = await self._speak_line(reply, voice) or sounded
                if draft.web and spoken and spoken[0] in _FILLERS + _FILLERS_EN:
                    reply = f"{spoken[0]} {reply}".strip()
                reply = app_main._body(user_id, reply)
            self._remember(draft, reply, leaving, sounded)
            spent()
            if draft.opened is not None and draft.opened < ended:
                # His first piece was written before their turn was certain,
                # and waited this long for it: what not voicing a guess cost.
                timing["head_waited"] = _after(ended, draft.opened)
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
            if late is not None:
                late.cancel()
            self._answering_aloud = False
            self._voicing = False

    def _give_up(self, cutter: asyncio.Task | None, ahead: deque, draft: Draft) -> None:
        if cutter is not None:
            cutter.cancel()
        for *_, voicing in ahead:
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
    # The kind as well as the words — a timeout says nothing in words at all —
    # and where it came from: «the brain / the voice» is two suspects.
    told = f"{type(error).__name__}: {error}" if error is not None else "—"
    where = ""
    if error is not None and error.__traceback__ is not None:
        import traceback

        frames = traceback.extract_tb(error.__traceback__)[-3:]
        where = "".join(f"\n      at {f.filename.rsplit('/', 1)[-1]}:{f.lineno} {f.name}" for f in frames)
    print(f"\n  ✗ {stage} failed\n    {told}{where}\n", file=sys.stderr, flush=True)


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
