"""FastAPI app — the voice loop and memory.

Voice only. HE always speaks first (even by launching the app hands-free); the
companion only ever *responds* — never initiates.

Talking loop (with memory + persona):
    audio → 👂 Whisper → [persona + recalled facts/stories/follow-ups/mood]
          → 🧠 Claude → 🗣️ Fish Audio → audio
          → (in the background) learn new memories

── WHO IS TALKING ──────────────────────────────────────────────────────────

Every endpoint that touches a person's life takes `user_id` from the
`Authorization: Bearer <token>` header, through the `_user` dependency and
identity.py. It is NEVER taken from the request body, the form, or the query
string — those are chosen by the caller, and an identity the caller can choose
is an identity anyone can borrow. The old `session_id` field is gone for
exactly that reason; clients that still send it are simply ignored, and land
where a request with no token lands (the anonymous user, i.e. the data that
existed before multi-user).

Endpoints:
    GET  /            → browser mic test page (a developer tool)
    GET  /api/health  → which services are configured + this person's memory
    POST /api/talk    → audio in  → {transcript, reply, audio}   (the real loop)
    POST /api/say     → text in   → {reply, audio}   (dev only: test brain+memory)
    POST /api/companion/create → the user's story + age/gender/origin → the friend
                        walks in (his name is chosen here, never by the user)
    GET  /api/diary   → the companion's handwritten diary about his friend —
                        the ONLY memory users ever see
    GET  /api/memory  → raw distilled memory (internal/dev only — never in the app)
"""

from __future__ import annotations

import asyncio
import base64
import json
import sys
import time
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from . import (
    allowance,
    brain,
    companion,
    config,
    db,
    diary,
    identity,
    intake,
    learn,
    matchmaker,
    memory,
    occasions,
    persona,
    reading,
    stt,
    tts,
)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    db.init_db()
    # data/facts.json belongs to whoever runs the server, so it seeds the
    # anonymous user and nobody else.
    memory.seed_facts_from_file(identity.ANONYMOUS)
    yield


app = FastAPI(title="Voice Companion", version="0.4.0", lifespan=_lifespan)

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def _user(authorization: str | None = Header(default=None)) -> str:
    """Whose request this is. The ONLY place identity enters the server.

    A missing header is not an error: it means the anonymous user, which is
    how the browser dev page, curl, and every build that predates the token
    keep working. See identity.py for why a *malformed* token is never
    anonymous.
    """
    return identity.user_id_from_token(authorization)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


@app.get("/api/health")
async def health(user_id: str = Depends(_user)) -> JSONResponse:
    services = config.service_status()
    p = persona.load_persona(user_id)
    return JSONResponse(
        {
            "ok": True,
            "companion_name": persona.persona_name(p),
            # Has THIS person met their friend yet? The app uses it to tell a
            # fresh phone from one that already has someone waiting — the
            # question that, answered from a single global persona file, gave
            # a new phone somebody else's companion.
            "has_companion": persona.has_persona(user_id),
            "language": config.LANGUAGE,
            "brain_model": config.BRAIN_MODEL,
            "tts_provider": tts.provider_name(),
            "services": services,
            "all_ready": all(services.values()),
            "memory": memory.counts(user_id, "elder"),
            "bob_self_facts": memory.counts(user_id, "bob").get("fact", 0),
        }
    )


def _log_failure(stage: str, error: Exception) -> None:
    """Say out loud, in the terminal, what actually broke."""
    print(f"\n  ✗ {stage} failed\n    {error}\n", file=sys.stderr, flush=True)
    if not isinstance(error, RuntimeError):
        traceback.print_exc()


def _unavailable(stage: str, error: Exception) -> HTTPException:
    """Return a 503 — and say out loud, in the terminal, what actually broke.

    Uvicorn logs an HTTPException as one anonymous line:

        INFO: 192.168.0.107:59760 - "POST /api/talk HTTP/1.1" 503 Service Unavailable

    That is the whole message. No stage, no provider, no reason — while the
    app, correctly, shows only «не слышит», because it must never show an
    error code to a lonely person. So the fact needed to fix it existed
    nowhere. Every 503 in this file now goes through here instead, and the
    person running the server can always see which of the three parts failed.

    A RuntimeError in this codebase always means "not configured / the
    provider said no", so its message is the answer and a traceback would
    only bury it. Anything else is a genuine bug and gets the full traceback.
    """
    _log_failure(stage, error)
    return HTTPException(status_code=503, detail=f"{stage}: {error}")


async def _assemble(user_id: str, user_text: str) -> tuple[str, str, list]:
    """Recall everything he should have in mind, and log that he was spoken to.

    Shared by both reply paths — the whole-reply one and the streaming one —
    so there is exactly one place where what he knows is decided.
    """
    memory.log_turn(user_id, "user", user_text)

    # All of it this person's.
    persona_block = persona.build_persona_block(persona.load_persona(user_id))
    elder_facts = memory.facts_context(user_id, "elder")
    bob_facts = memory.bob_self_context(user_id)
    mem_ctx = await memory.build_memory_context(user_id, user_text)

    # If today is a special date, let Bob mention it warmly — but only in reply
    # to him (he never speaks first).
    occ = occasions.occasion_for()
    if occ:
        note = (
            f"Сегодня {occ['name']}. {occ['note']} "
            "Если это уместно и к слову — тепло упомяни это сам."
        )
        mem_ctx = f"{mem_ctx}\n\n{note}".strip() if mem_ctx else note

    system_stable, system_variable = companion.build_system_parts(
        persona_block=persona_block,
        # How this person needs to be spoken to, and what must never be
        # joked about. Stable, so it rides in the cached half for free.
        reading_block=reading.standing_block(reading.load(user_id)),
        elder_facts=elder_facts,
        bob_facts=bob_facts,
        memory_context=mem_ctx,
        elder_name=config.ELDER_NAME,
    )

    return system_stable, system_variable, memory.recent_turns(user_id)


def _remember(
    user_id: str, user_text: str, reply: str, background_tasks: BackgroundTasks
) -> None:
    """Log what he said back, and learn from the exchange once nobody's waiting."""
    memory.log_turn(user_id, "assistant", reply)
    background_tasks.add_task(learn.learn_from_exchange, user_id, user_text, reply)


async def _think_and_speak(
    user_id: str, user_text: str, background_tasks: BackgroundTasks
) -> dict[str, str]:
    """The whole reply, in one piece — the original path, still the fallback.

    Used for clients that don't ask for a stream, and for the turns that can't
    be streamed honestly (web search — see brain.stream_reply).
    """
    system_stable, system_variable, history = await _assemble(user_id, user_text)
    reply = await brain.generate_reply(
        history,
        system_stable,
        system_variable,
        # Web search only when the message actually asks about the world right
        # now — an available tool invites the model to consider it, and a
        # search turn costs seconds.
        fresh_info=brain.wants_fresh_info(user_text),
    )

    _remember(user_id, user_text, reply, background_tasks)

    # The mouth is optional. With a voice provider configured we return warm
    # spoken audio. Without one (MVP / browser testing), we return no audio and
    # let the client speak the reply with its own free voice — so testing needs
    # only Whisper + Claude. "voice" tells the client which path to take.
    if tts.configured():
        audio_bytes = await tts.synthesize(reply)
        return {
            "reply": reply,
            "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
            "audio_mime": "audio/mpeg",
            "voice": "server",
        }
    return {"reply": reply, "audio_base64": "", "audio_mime": "", "voice": "client"}


# --------------------------------------------------------------------------- #
# Speaking while still thinking
# --------------------------------------------------------------------------- #
#
# A turn used to be three waits end to end: hear it all, think it all, say it
# all, and only then send anything. The listener sat through the sum. Here the
# three overlap — the first sentence is spoken aloud while the second is still
# being written — which takes several seconds out of every silence.
#
# The wire format is newline-delimited JSON, one object per line:
#
#   {"kind":"heard","transcript":"…"}      what Whisper made of it
#   {"kind":"say","text":"…","audio_base64":"…"}   speak this now
#   {"kind":"say", …}                       …and this next
#   {"kind":"done","reply":"…","seconds_left":1234}
#   {"kind":"trouble","detail":"…"}         it broke mid-sentence
#
# NDJSON rather than SSE because the phone is not a browser and has no use for
# EventSource, and because a line is trivially parseable from
# URLSession.bytes(for:) with no framing library.
#
# `trouble` exists because a StreamingResponse has already sent its status line
# by the time anything can go wrong, so a 503 is no longer available. That is
# an improvement, not a workaround: some of his answer may already have been
# heard, and the phone knows how to keep it.

_NDJSON = "application/x-ndjson"


def _line(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")


async def _speak_as_he_thinks(
    user_id: str,
    transcript: str,
    started: float,
    background_tasks: BackgroundTasks,
):
    """Yield his reply as spoken pieces, in order, as fast as each is ready."""
    yield _line({"kind": "heard", "transcript": transcript})

    reply = ""
    try:
        system_stable, system_variable, history = await _assemble(user_id, transcript)
        speak = tts.configured()

        # TWO TASKS, NOT ONE LOOP. The obvious version — read a token, and when
        # a sentence is finished go and synthesise it — was measurably wrong:
        # an async generator only advances when it is asked to, so the half
        # second spent waiting on the voice is half a second in which Claude is
        # not being read. Writing and speaking serialise, and the streaming
        # buys a fraction of what it should.
        #
        # Here the writer runs flat out and drops finished sentences into a
        # queue; this loop takes them to the voice. The model is never waiting
        # on the voice, and the voice is never waiting on the model.
        fragments: asyncio.Queue = asyncio.Queue()

        async def write() -> None:
            nonlocal reply
            try:
                committed = 0
                first = True
                async for reply in brain.stream_reply(
                    history, system_stable, system_variable
                ):
                    tail = reply[committed:]
                    cut = tts.ready_split(tail, first=first)
                    if not cut:
                        continue
                    committed += cut
                    fragment = tail[:cut].strip()
                    if fragment:
                        await fragments.put(fragment)
                        first = False
                # Whatever is left when he stops — usually the last sentence,
                # which never gets whitespace after it to prove it finished.
                rest = reply[committed:].strip()
                if rest:
                    await fragments.put(rest)
            finally:
                # The consumer below waits on this. Without it in a `finally`,
                # a failure while writing hangs the request open forever.
                await fragments.put(None)

        writer = asyncio.create_task(write())
        try:
            while True:
                fragment = await fragments.get()
                if fragment is None:
                    break
                if not speak:
                    yield _line({"kind": "say", "text": fragment, "audio_base64": ""})
                    continue
                audio = await tts.synthesize(fragment)
                yield _line(
                    {
                        "kind": "say",
                        "text": fragment,
                        "audio_base64": base64.b64encode(audio).decode("ascii"),
                        "audio_mime": "audio/mpeg",
                    }
                )
            await writer  # re-raise whatever went wrong while writing
        finally:
            writer.cancel()

        reply = reply.strip()
        if reply:
            _remember(user_id, transcript, reply, background_tasks)

    except Exception as e:  # noqa: BLE001 — a stream cannot raise a status code
        _log_failure("🧠 the brain (Claude) / 🗣️ the voice", e)
        yield _line({"kind": "trouble", "detail": str(e)})

    allowance.spend(user_id, time.monotonic() - started)
    yield _line(
        {
            "kind": "done",
            "reply": reply,
            "voice": "server" if tts.configured() else "client",
            "seconds_left": allowance.seconds_left(user_id),
        }
    )


@app.post("/api/talk")
async def talk(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    user_id: str = Depends(_user),
    accept: str = Header(default=""),
):
    """Full voice loop: audio → transcript → reply → spoken audio.

    Two shapes, chosen by the caller's `Accept` header:

      application/x-ndjson  → he starts speaking while he is still thinking
                              (see _speak_as_he_thinks). What the app asks for.
      anything else         → one JSON object with the whole reply and the
                              whole audio. The original shape, kept exactly as
                              it was so the browser dev page, curl and every
                              build that predates streaming keep working.

    Content negotiation rather than a second URL: the phone has one address to
    know, and a client that has never heard of streaming cannot accidentally
    receive one.
    """
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio upload.")

    # Before ANY paid work: has he got the day left, and is he even awake?
    # This is deliberately the first thing that happens — checking after
    # transcribing would already have cost money.
    verdict = allowance.check(user_id)
    if not verdict.allowed:
        return JSONResponse(
            {
                "transcript": "",
                "reply": verdict.reason,
                "audio_base64": "",
                "audio_mime": "",
                "voice": "client",
                "state": verdict.code,
                "seconds_left": verdict.seconds_left,
            }
        )

    started = time.monotonic()

    try:
        transcript = await stt.transcribe(
            audio_bytes, filename=audio.filename or "audio.webm"
        )
    except Exception as e:  # noqa: BLE001 — every failure gets named, none is silent
        raise _unavailable("👂 the ears (Whisper)", e)

    # Judge whether that sounded like a person before spending on a reply. A
    # room with a television produces a steady trickle of short fragments; a
    # person produces sentences.
    allowance.note_turn(user_id, transcript)

    if not transcript:
        allowance.spend(user_id, time.monotonic() - started)
        return JSONResponse(
            {"transcript": "", "reply": "", "note": "No speech detected."}
        )

    if allowance.is_asleep(user_id):
        allowance.spend(user_id, time.monotonic() - started)
        return JSONResponse(
            {
                "transcript": transcript,
                "reply": "",
                "audio_base64": "",
                "audio_mime": "",
                "voice": "client",
                "state": "asleep",
                "seconds_left": allowance.seconds_left(user_id),
            }
        )

    # Web-search turns can't be streamed honestly — the answer may still change
    # after the search returns, and half of it has already been spoken aloud by
    # then. Those turns are rare and slow anyway, so they take the whole-reply
    # path even when the caller asked for a stream.
    if _NDJSON in accept and not brain.wants_fresh_info(transcript):
        return StreamingResponse(
            _speak_as_he_thinks(user_id, transcript, started, background_tasks),
            media_type=_NDJSON,
            # Nothing between here and the phone may hold these lines back
            # waiting for more: the entire point is that the first one leaves
            # immediately.
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
            background=background_tasks,
        )

    try:
        result = await _think_and_speak(user_id, transcript, background_tasks)
    except Exception as e:  # noqa: BLE001
        raise _unavailable("🧠 the brain (Claude) / 🗣️ the voice", e)

    allowance.spend(user_id, time.monotonic() - started)

    return JSONResponse(
        {
            "transcript": transcript,
            **result,
            "seconds_left": allowance.seconds_left(user_id),
        }
    )


class SayRequest(BaseModel):
    text: str
    #: Speak the text back EXACTLY, without thinking about it and without
    #: remembering it. Used by the background-voice test, where the question is
    #: only "does his voice come out of a backgrounded app" — a brain round trip
    #: would add seconds and another way to fail, and logging the test line as a
    #: real memory would quietly poison his diary.
    verbatim: bool = False


@app.post("/api/say")
async def say(
    req: SayRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(_user),
) -> JSONResponse:
    """Text-in voice loop (skips the ears) — for testing brain + memory + mouth."""
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text.")

    if req.verbatim:
        if not tts.configured():
            return JSONResponse(
                {"transcript": text, "reply": text, "audio_base64": "",
                 "audio_mime": "", "voice": "client"}
            )
        try:
            audio_bytes = await tts.synthesize(text)
        except Exception as e:  # noqa: BLE001
            raise _unavailable("🗣️ the voice", e)
        return JSONResponse({
            "transcript": text,
            "reply": text,
            "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
            "audio_mime": "audio/mpeg",
            "voice": "server",
        })

    try:
        result = await _think_and_speak(user_id, text, background_tasks)
    except Exception as e:  # noqa: BLE001
        raise _unavailable("🧠 the brain (Claude) / 🗣️ the voice", e)
    return JSONResponse({"transcript": text, **result})


@app.post("/api/wake")
async def wake(user_id: str = Depends(_user)) -> JSONResponse:
    """Someone came back and tapped — he opens his eyes.

    The daily allowance is NOT reset by this; only the dozing is. Waking him is
    always free.
    """
    allowance.wake(user_id)
    return JSONResponse(
        {"awake": True, "seconds_left": allowance.seconds_left(user_id)}
    )


@app.get("/api/usage")
async def usage(user_id: str = Depends(_user)) -> JSONResponse:
    """What this person has used today, and what's left.

    Also the honest answer to «how much is this costing me» during the test
    month: seconds x the per-second rate of whichever providers are configured.

    Read from the token, never from a query string — `?session_id=` would have
    let anyone read anyone's usage, and a limit you can look up for someone
    else is a limit you can work out how to dodge for yourself.
    """
    used = allowance.used_today(user_id)
    return JSONResponse(
        {
            "seconds_used_today": round(used, 1),
            "seconds_left_today": allowance.seconds_left(user_id),
            "daily_allowance": allowance.SECONDS_PER_DAY,
            "asleep": allowance.is_asleep(user_id),
        }
    )


# ── Size limits ─────────────────────────────────────────────────────────────
#
# Every field below reaches a model, and a model is charged by the character.
# With one user these caps were pointless; on a shared server an uncapped text
# field is a bill anybody can run up. The numbers are generous — far past what
# the app itself can produce — so no real person will ever meet one.
_MAX_QUESTION = 2_000
_MAX_ANSWER = 8_000
_MAX_TURNS = 40          # the intake stops itself at 18; this is the hard floor
_MAX_STORY = 40_000
_MAX_WISHES = 4_000
_MAX_CHIP = 200


class IntakeTurn(BaseModel):
    q: str = Field("", max_length=_MAX_QUESTION)   # what was asked
    a: str = Field("", max_length=_MAX_ANSWER)     # what they answered


class IntakeRequest(BaseModel):
    #: Everything said so far, oldest first. The client holds it: an intake is
    #: one continuous sitting, and half a personal conversation is not
    #: something to resume days later — starting fresh is the kinder default.
    conversation: list[IntakeTurn] = Field(default_factory=list, max_length=_MAX_TURNS)


@app.post("/api/intake/next")
async def intake_next(
    req: IntakeRequest, user_id: str = Depends(_user)
) -> JSONResponse:
    """The next question in «пока его нет» — the conversation that replaces
    the blank «расскажите о себе» page. See app/intake.py for the design.

    Empty conversation → the fixed opener, with no model call at all: the one
    question that decides whether someone engages must be instant and can't
    be allowed to come out badly.
    """
    if not req.conversation:
        return JSONResponse(intake.opening())

    # This is a paid call, so it is metered like every other paid call. On a
    # server with one person that didn't matter; on a shared one, an endpoint
    # that spends money without counting is a hole anybody can pour through.
    # Someone out of allowance is simply told the conversation is finished —
    # the client already knows how to end gracefully, and what they've said so
    # far is enough to build a friend from.
    if not allowance.check(user_id).allowed:
        return JSONResponse({"say": "", "enough": True})

    started = time.monotonic()
    turns = [t.model_dump() for t in req.conversation]
    try:
        result = await intake.next_question(turns)
        allowance.spend(user_id, time.monotonic() - started)
        return JSONResponse(result)
    except Exception as e:  # noqa: BLE001
        # A dead question must not strand someone mid-conversation with no way
        # forward. Ending gracefully hands them whatever they've already said,
        # which the reading can still work with.
        print(f"\n  ⚠ следующий вопрос не получился — заканчиваю разговор\n    {e}\n",
              file=sys.stderr, flush=True)
        return JSONResponse({"say": "", "enough": True})


class CreateCompanionRequest(BaseModel):
    #: «Tell your story» — free writing. Still supported, and still how the
    #: browser dev page works, but no longer what the app shows anyone.
    about: str = Field("", max_length=_MAX_STORY)
    #: The intake conversation (app/intake.py). When present it BECOMES the
    #: story — a dozen natural answers carry far more of a person than a
    #: composed paragraph, which is the whole reason the blank page went.
    conversation: list[IntakeTurn] = Field(default_factory=list, max_length=_MAX_TURNS)
    #: «Who would you like to meet?» — free writing, may be empty
    wishes: str = Field("", max_length=_MAX_WISHES)
    age: str = Field("", max_length=_MAX_CHIP)  # the optional chips that screen offers…
    gender: str = Field("", max_length=_MAX_CHIP)
    origin: str = Field("", max_length=_MAX_CHIP)  # …never a name: he arrives with his own.

    def story(self) -> str:
        spoken = intake.as_story([t.model_dump() for t in self.conversation])
        written = self.about.strip()
        if spoken and written:
            return spoken + "\n\n" + written
        return spoken or written


@app.post("/api/companion/create")
async def companion_create(
    req: CreateCompanionRequest, user_id: str = Depends(_user)
) -> JSONResponse:
    """From the user's own words, and whatever they asked for, the friend walks in.

    They may describe him as much or as little as they like — including not at
    all. However much they specify, he still arrives as his own person, with his
    own name, opinions, and things he honestly doesn't like.
    """
    req = req.model_copy(update={"about": req.story()})
    if not req.about.strip():
        raise HTTPException(
            status_code=400, detail="Расскажите о себе — хоть немного."
        )

    # By some distance the most expensive thing the server does — the deepest
    # model, real thinking time, then two more calls — and until multi-user it
    # was completely unmetered. A person meeting their friend has spent
    # nothing yet and will never see this; someone hammering the endpoint will
    # see it immediately.
    verdict = allowance.check(user_id)
    if not verdict.allowed:
        raise HTTPException(status_code=429, detail=verdict.reason)

    started = time.monotonic()
    try:
        p = await matchmaker.create_companion(
            user_id,
            req.about,
            wishes=req.wishes.strip(),
            age=req.age.strip(),
            gender=req.gender.strip(),
            origin=req.origin.strip(),
        )
    except Exception as e:  # noqa: BLE001
        raise _unavailable("🧠 writing him (Claude)", e)
    finally:
        allowance.spend(user_id, time.monotonic() - started)
    return JSONResponse({"name": p.get("name"), "persona": p})


@app.get("/api/diary")
async def companion_diary(user_id: str = Depends(_user)) -> JSONResponse:
    """His diary — the beautifully written book about his friend.

    This is the ONLY memory view users ever see; the raw distilled memory
    below stays internal.
    """
    try:
        return JSONResponse(await diary.get_diary(user_id))
    except Exception as e:  # noqa: BLE001
        raise _unavailable("📖 the diary (Claude)", e)


@app.get("/api/memory")
async def memory_dump(user_id: str = Depends(_user)) -> JSONResponse:
    """Raw distilled memory — internal/dev inspection only, never shown in the app.

    Scoped to the caller. It used to `SELECT ... FROM memories` with no WHERE
    at all, which on a server with more than one person on it is a single
    unauthenticated GET that returns everybody's private life.
    """
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT owner, kind, title, content, status, recall_count, created_ts "
            "FROM memories WHERE user_id=? ORDER BY created_ts DESC LIMIT 200",
            (user_id,),
        ).fetchall()
    return JSONResponse(
        {
            "elder": memory.counts(user_id, "elder"),
            "bob": memory.counts(user_id, "bob"),
            "memories": [dict(r) for r in rows],
        }
    )
