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
    POST /api/companion/start-over → he goes and everything between them goes
                        with him; what is known about the PERSON stays
    DELETE /api/me    → everything, every table, every file, no way back
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
    body,
    brain,
    companion,
    config,
    db,
    diary,
    emergency,
    erase,
    feeling,
    fit,
    identity,
    intake,
    learn,
    life,
    matchmaker,
    memory,
    mood,
    occasions,
    persona,
    reading,
    safety,
    situations,
    stt,
    tts,
    vow,
    young,
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


async def _assemble(user_id: str, user_text: str) -> tuple[str, str, list, str | None]:
    """Recall everything he should have in mind, and log that he was spoken to.

    Shared by both reply paths — the whole-reply one and the streaming one —
    so there is exactly one place where what he knows is decided.
    """
    # BEFORE the log, not after: this asks how long it has been since anybody
    # last said anything, and logging first makes that answer zero — forever.
    broke_off = memory.broke_off_last_time(user_id)
    # Also before the log, for the same reason: it counts turns, and this one
    # would otherwise count itself.
    acquaintance = memory.how_long_acquainted(user_id)
    # …and HOW LONG HE HAS BEEN GONE, which nothing used to say. See
    # memory.how_long_since_last_time. Before the log, like the two above.
    gap = memory.how_long_since_last_time(user_id)
    if gap:
        acquaintance = f"{acquaintance}\n{gap}"
    memory.log_turn(user_id, "user", user_text)

    # All of it this person's — including WHICH VOICE he or she speaks in.
    who = persona.load_persona(user_id)
    persona_block = persona.build_persona_block(who)
    elder_facts = memory.facts_context(user_id, "elder")
    bob_facts = memory.bob_self_context(user_id)
    # THE WATCHER NO LONGER HOLDS UP THE ANSWER. It used to be awaited here,
    # beside the memory work, and the prompt could not be assembled until its
    # verdict came back — so a person who was perfectly fine waited, every
    # single turn, on a question that turned out to be about somebody else.
    #
    # It is a task now, and the reply races it. `danger` does not need to be in
    # a prompt to do its job: it INTERRUPTS, mid-sentence, with words that are
    # written down rather than generated (_breaking_in / safety.spoken_alert).
    # Anything found too late to interrupt is not lost either — it rides in the
    # next turn's prompt, once, via safety.carried(). It cannot raise.
    watcher = asyncio.create_task(safety.look(user_id, user_text))
    mem_ctx = await memory.build_memory_context(user_id, user_text)
    # What the watcher found on some earlier turn and he never got to hear.
    # Empty on virtually every turn, and a live `danger` never arrives here.
    carried = safety.carried(user_id)

    # WHAT DAY IT IS. He did not know — not the date, not the weekday — which
    # meant «дочь Валя, день рождения 3 мая» could sit in his memory for a year
    # and pass unremarked on the third of May. Given the day and given the
    # facts, noticing is his job and he is good at it. See occasions.py.
    today = occasions.today_block(user_id, elder_facts)
    mem_ctx = f"{today}\n\n{mem_ctx}".strip() if mem_ctx else today

    system_stable, system_variable = companion.build_system_parts(
        persona_block=persona_block,
        # How this person needs to be spoken to, and what must never be
        # joked about. Stable, so it rides in the cached half for free.
        reading_block=reading.standing_block(
            reading.load(user_id),
            # Once the register has WATCHED either of these, the reading's guess
            # at it is dropped rather than left to argue with the measurement.
            # Both guesses were made from one paragraph on the day the app was
            # installed, and both are phrased as instructions; the watched
            # answer is phrased mildly, so with both present the louder and
            # weaker one wins, which is backwards.
            lifts_confirmed=mood.lifts_confirmed(user_id),
            closeness_confirmed=mood.closeness(user_id) != "normal",
        ),
        # Proven on him, not guessed about him. See mood.py.
        confirmed_block=mood.standing_block(user_id),
        # How the two of them fit — watched, never guessed.
        fit_block=fit.block(user_id),
        # Empty for every grown-up, which is nearly everybody. It changes how
        # he speaks rather than what he may hear — see young.py.
        young_block=young.block(user_id),
        # Empty on virtually every turn. The one thing allowed to override the
        # character, so it is placed before everything else — see safety.py.
        alert_block=safety.block(carried, user_id),
        # On danger the alert IS the prompt — see build_system_parts.
        alert_level=(carried or {}).get("level", ""),
        # How HE is today, carried over from their last exchange and fading on
        # its own since. The one thing in the prompt that is not about her.
        feeling_block=feeling.block(user_id),
        # His throat and his tiredness — facts about him, never instructions to
        # cough. The valence is his own mood arriving in his breathing, which is
        # where a mood actually goes. See body.py.
        # What is going on in his week — a cold, a brother visiting — with its
        # own shape over days. Background, never the topic; see life.py.
        life_block=life.block(user_id),
        body_block=body.block(user_id, valence=feeling.now(user_id)["valence"]),
        # Rules that only apply to the turn in front of him — the game they are
        # playing, the news he asked for. Empty nearly always; see situations.py
        # for why they are no longer read on every turn.
        situation_block=situations.block(user_text, memory.recent_turns(user_id)),
        elder_facts=elder_facts,
        bob_facts=bob_facts,
        # What the person has taught him, so the pupil actually grows.
        lessons_block=memory.lessons_block(user_id),
        memory_context=mem_ctx,
        elder_name=config.ELDER_NAME,
        broke_off=broke_off,
        acquaintance=acquaintance,
    )

    return (
        system_stable,
        system_variable,
        memory.recent_turns(user_id),
        tts.voice_for(who),
        watcher,
    )


def _alarm(verdict: dict | None, user_id: str) -> dict | None:
    """What the PHONE can do about a danger verdict, which is more than he can.

    He says the number out loud, and that is the right thing for him to say —
    but hearing a number, holding it, leaving the app and typing it correctly
    is a great deal to ask of somebody who is frightened or on the floor. A
    button asks none of it. So the verdict goes to the app as well as to the
    speaker, and the app puts the number of THIS person's country under
    something they can press.

    `danger` distinguishes the two emergencies (safety.spoken_alert): "body"
    wants an ambulance now; "self" is the one where fetching the family is the
    standard contraindication, and the app must not act as though it were the
    same thing. Crisis lines by country do not exist yet — that is a product
    decision with real numbers behind it, and inventing one here would be worse
    than the honest answer, which is the emergency number and a friend who
    stays.
    """
    if not verdict or verdict.get("level") != "danger":
        return None
    return {
        "danger": verdict.get("kind") or "body",
        "numbers": emergency.dialable(user_id),
    }


async def _breaking_in(
    watcher: asyncio.Task, user_id: str, *, wait: bool
) -> tuple[str, dict | None]:
    """The words to break in with and the verdict behind them, or ("", None) —
    which is the answer almost always.

    `wait=False` is the check made between spoken fragments: it asks whether
    the watcher has ALREADY finished and must never block the next sentence.
    `wait=True` is the check made once he has stopped talking, where waiting
    costs nobody anything — the audio is already out — and the alternative is
    losing an alarm that arrived a second too late to interrupt.

    The verdict comes back with the words because the PHONE has something to do
    about it that no sentence can do for it: put the right number under a
    button. See the `alarm` line in _speak_as_he_thinks.
    """
    if not wait and not watcher.done():
        return "", None
    try:
        verdict = await watcher
    except Exception:  # noqa: BLE001 — safety.look does not raise, but a task
        return "", None  # that failed or was cancelled must not take the turn.
    words = safety.spoken_alert(verdict, user_id)
    if words:
        # Said out loud is the only thing that counts as told. Stamping it here
        # is what stops the next turn raising the same alarm a second time.
        safety.mark_told(user_id)
    return words, (verdict if words else None)


def _farewell(reply: str) -> tuple[str, bool]:
    """Split a reply into what he actually said and whether he was saying goodbye.

    The marker never survives past this point: not into the audio, not into
    the conversation log, not into his diary. It exists for exactly one
    instruction — stop listening — and then it is gone.
    """
    if companion.FAREWELL_MARKER not in reply:
        return reply, False
    return reply.replace(companion.FAREWELL_MARKER, "").strip(), True


def _body(user_id: str, reply: str) -> str:
    """Apply what his body just did, and take the markers out of the reply.

    Called on BOTH reply paths, and the markers must be gone before anything is
    remembered: they exist to move a number in body.py and to tell the voice
    where a cough went, and they belong in neither the conversation log nor the
    diary. tts.spoken() strips them again on the way to the audio — that is not
    redundant, it is the streaming path, where a fragment is synthesised long
    before the finished reply exists to be cleaned.
    """
    said = body.read_markers(reply, user_id)
    # HIS age, not the listener's. A thirty-four-year-old companion does not get
    # the throat of an eighty-seven-year-old, and matchmaker.py writes both.
    body.spoke(
        user_id,
        laughed=body.laughed_in(reply),
        age=persona.load_persona(user_id).get("age"),
    )
    return said


def _remember(
    user_id: str,
    user_text: str,
    reply: str,
    background_tasks: BackgroundTasks,
    farewell: bool = False,
) -> None:
    """Log what he said back, and learn from the exchange once nobody's waiting.

    `farewell` is the ONLY trace the marker leaves anywhere. The words it was
    attached to are stored clean, exactly as they were spoken; the fact that
    this line closed a conversation is kept beside them as a flag, because
    otherwise there is no way to tell a conversation that ended from one that
    was abandoned — and that difference is the whole of what he notices next
    time (memory.broke_off_last_time).
    """
    memory.log_turn(user_id, "assistant", reply, farewell=farewell)

    # NOTHING IS KEPT ABOUT SOMEBODY WHO IS NOT AN ADULT, and this is the only
    # place it could be, because this is where a person's life accumulates:
    # the scribe that distils them into facts, the reader that reads them, the
    # register that measures them. For a child none of it runs, and what the
    # earlier turns of today left behind is taken away — see young.py.
    #
    # There is no door anywhere in this app and there will not be one. The fix
    # is not who gets in, it is what is kept, which is also the only part
    # Google actually had to change after the YouTube settlement.
    if young.keeps_nothing(user_id):
        young.forget(user_id)
        # His week and his own character still grow: those are HIS, not theirs.
        background_tasks.add_task(life.maybe_begin, user_id)
        return

    # In batches, not on every exchange. It used to run on each one, which was
    # about a third of what a whole conversation cost — and it was also the
    # worst extraction available, because one exchange is almost nothing to
    # judge from. A goodbye always closes the batch; see learn.unread().
    background_tasks.add_task(
        learn.learn_from_conversation, user_id, farewell=farewell
    )
    # AND, every so often, read the person again. The first reading was made
    # from a few minutes of somebody talking to a machine they had never met;
    # everything since is better evidence. It decides for itself whether
    # enough has been said to be worth it, and costs nothing when it isn't.
    background_tasks.add_task(reading.keep_reading, user_id)
    # And perhaps something starts happening to him this week — a cold, a
    # brother visiting. It decides for itself, rolls rarely, and costs nothing
    # on the days it decides not to. See life.py.
    background_tasks.add_task(life.maybe_begin, user_id)
    # And, more rarely still, let the friendship reveal more of HIM. His facts
    # never move — but who is around him, what is wrong with him and what he
    # is up to this week are things you only learn by knowing somebody.
    background_tasks.add_task(persona.deepen, user_id)


async def _think_and_speak(
    user_id: str, user_text: str, background_tasks: BackgroundTasks
) -> dict[str, str]:
    """The whole reply, in one piece — the original path, still the fallback.

    Used for clients that don't ask for a stream, and for the turns that can't
    be streamed honestly (web search — see brain.stream_reply).
    """
    system_stable, system_variable, history, voice, watcher = await _assemble(
        user_id, user_text
    )
    reply = await brain.generate_reply(
        history,
        system_stable,
        system_variable,
        # Web search only when the message actually asks about the world right
        # now — an available tool invites the model to consider it, and a
        # search turn costs seconds.
        fresh_info=brain.wants_fresh_info(user_text),
    )

    reply, leaving = _farewell(reply)
    # The two things he never says — see vow.py. Whole sentences are removed,
    # never rewritten, and the last resort is reached only when the removal
    # took everything.
    said = reply
    reply, slip = vow.keep(reply)
    if slip:
        vow.note(user_id, slip, said)
        reply = reply or vow.LAST_RESORT
    reply = _body(user_id, reply)
    # The watcher has been running this whole time, so this costs no wall clock
    # worth measuring — and on danger it replaces the answer outright. Nothing
    # of his is worth saying to a man who is on the floor.
    breaking, verdict = await _breaking_in(watcher, user_id, wait=True)
    if breaking:
        reply, leaving = breaking, False
    _remember(user_id, user_text, reply, background_tasks, farewell=leaving)

    # The mouth is optional. With a voice provider configured we return warm
    # spoken audio. Without one (MVP / browser testing), we return no audio and
    # let the client speak the reply with its own free voice — so testing needs
    # only Whisper + Claude. "voice" tells the client which path to take.
    alarm = _alarm(verdict, user_id)
    if tts.configured():
        # Slower for somebody who has been struggling to make him out. The
        # app has counted that for months and only ever answered it with a
        # prompt line asking for shorter sentences; the speed is the knob
        # that was actually asked for. See tts.rate_for.
        audio_bytes = await tts.synthesize(reply, voice, rate=tts.rate_for(user_id))
        return {
            "reply": reply,
            "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
            "audio_mime": "audio/mpeg",
            "voice": "server",
            "farewell": leaving,
            **({"alarm": alarm} if alarm else {}),
        }
    return {
        "reply": reply,
        "audio_base64": "",
        "audio_mime": "",
        "voice": "client",
        "farewell": leaving,
        **({"alarm": alarm} if alarm else {}),
    }


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
#   {"kind":"alarm","alarm":{"danger":"body","numbers":["103","112"]}}
#                                           he is breaking in — put the number
#                                           under a button, now
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
    leaving = False
    try:
        system_stable, system_variable, history, voice, watcher = await _assemble(
            user_id, transcript
        )
        speak = tts.configured()
        # Read once per turn rather than per fragment: it is a database hit,
        # and it cannot change in the middle of one reply.
        rate = tts.rate_for(user_id)

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
        #: What actually left the speaker, sentence by sentence. Needed because
        #: an interrupted turn must be remembered as what he SAID, not as what
        #: the model happened to have written by the time it was cut off.
        spoken: list[str] = []
        breaking = ""
        verdict: dict | None = None
        #: Whether anything was taken out of his mouth on the way past.
        dropped = False

        def _said(text: str, audio: bytes | None) -> bytes:
            return _line(
                {
                    "kind": "say",
                    "text": text,
                    "audio_base64": (
                        base64.b64encode(audio).decode("ascii") if audio else ""
                    ),
                    **({"audio_mime": "audio/mpeg"} if audio else {}),
                }
            )

        try:
            while True:
                fragment = await fragments.get()
                if fragment is None:
                    break
                # THE TWO THINGS HE NEVER SAYS, checked BEFORE they are said
                # rather than found out about afterwards. This is the only
                # place in the app that reads his own words, and it costs
                # nothing to do it: no model, no token, no millisecond.
                #
                # Checked here and not at the end because the end is too late.
                # Audio that has left the speaker has been heard, and a person
                # cannot un-hear «я всего лишь программа».
                if slip := vow.broken(fragment):
                    vow.note(user_id, slip, fragment)
                    dropped = True
                elif not speak:
                    yield _said(fragment, None)
                    spoken.append(fragment)
                # A fragment that is nothing BUT a stage direction («*пауза*»)
                # has nothing left once it's cleaned, and asking the voice to
                # say nothing is an error. Skip it rather than break the turn.
                elif tts.spoken(fragment):
                    yield _said(fragment, await tts.synthesize(fragment, voice, rate=rate))
                    spoken.append(fragment)
                # BETWEEN SENTENCES, never before one: has the watcher come
                # back with something that cannot wait for him to finish? This
                # asks only whether the answer is already sitting there — it
                # never holds up the next sentence to find out.
                breaking, verdict = await _breaking_in(watcher, user_id, wait=False)
                if breaking:
                    break
            if not breaking:
                await writer  # re-raise whatever went wrong while writing
        finally:
            writer.cancel()

        # He has stopped talking. If the watcher still has not answered, wait
        # for it NOW — the audio is already out, so nobody is sitting through
        # the silence, and an alarm that is one second late is worth everything
        # compared to one that is dropped.
        if not breaking:
            breaking, verdict = await _breaking_in(watcher, user_id, wait=True)

        if breaking:
            # THE BUTTON GOES UP BEFORE THE SENTENCE IS SPOKEN, not after.
            # He is about to say a number out loud; by the time he has, the
            # thing to press is already on screen, in the same second. See
            # _alarm — this is the half of an emergency a sentence cannot do.
            if alarm := _alarm(verdict, user_id):
                yield _line({"kind": "alarm", "alarm": alarm})
            # Markers never survive into memory, on this path either.
            said_so_far = _body(user_id, _farewell(" ".join(spoken).strip())[0])
            yield _said(
                breaking,
                await tts.synthesize(breaking, voice, rate=rate) if speak else None,
            )
            # What he said this turn is what got out before he was cut off, and
            # then the thing that mattered. A danger turn is never a goodbye.
            reply, leaving = f"{said_so_far} {breaking}".strip(), False
        else:
            reply, leaving = _farewell(reply.strip())
            # The same removal on what will be REMEMBERED. The fragments above
            # are what left the speaker; this is the model's whole answer, and
            # it goes into the turns table and from there into his diary and
            # everything the scribe reads. Cleaning one and not the other would
            # mean he never said it and remembered saying it.
            reply, _slip = vow.keep(reply)
            # He wrote nothing but the confession, so there is nothing of his
            # left to say. This is the only line here that is invented rather
            # than removed, and it is written down where it can be read.
            if dropped and not spoken and not reply:
                reply = vow.LAST_RESORT
                yield _said(
                    reply,
                    await tts.synthesize(reply, voice, rate=rate) if speak else None,
                )
            reply = _body(user_id, reply)

        if reply:
            _remember(user_id, transcript, reply, background_tasks, farewell=leaving)

    except Exception as e:  # noqa: BLE001 — a stream cannot raise a status code
        _log_failure("🧠 the brain (Claude) / 🗣️ the voice", e)
        yield _line({"kind": "trouble", "detail": str(e)})

    allowance.spend(user_id, time.monotonic() - started)
    yield _line(
        {
            "kind": "done",
            "reply": reply,
            # He said goodbye — the phone stops listening once he has finished
            # speaking. A friend is left by saying so, not by closing an app.
            "farewell": leaving,
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
    #: Which of intake.TARGETS the question was after — handed back so the
    #: server knows what the list still needs. Empty for an older client.
    target: str = Field("", max_length=32)


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
    #: WHERE HE LIVES, in his own words — «в Израиле», «Казахстан», «в Хайфе».
    #: The app asks it outright during the warm-up, so this is one specific
    #: answer rather than something to be dug out of the story, and it is free
    #: text rather than a code because nobody is filling in a form (see
    #: emergency.resolve). It decides the number he is told to dial.
    country: str = Field("", max_length=_MAX_CHIP)

    def story(self) -> str:
        spoken = intake.as_story([t.model_dump() for t in self.conversation])
        written = self.about.strip()
        if spoken and written:
            return spoken + "\n\n" + written
        return spoken or written


@app.post("/api/companion/create")
async def companion_create(
    req: CreateCompanionRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(_user),
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

    # WHERE HE LIVES, WRITTEN DOWN BEFORE HE SAYS A WORD TO ANYBODY.
    #
    # Until now this was only ever learned by the extractor, several exchanges
    # into the friendship, if he happened to mention it — so the first
    # conversation, which is the one where somebody is most likely to say
    # something frightening to a stranger, ran on the deployment's default
    # number. Now it is asked outright at the warm-up and stored here, first
    # thing: before the minute spent writing him, so that a failure to write
    # him does not also lose the one fact that matters in an emergency.
    #
    # Anywhere unrecognised is simply not stored, and 112 still answers.
    if req.country.strip():
        emergency.remember(user_id, req.country)

    # HOW OLD THEY ARE, from the question the warm-up already asks warmly and
    # in the middle of a conversation. Stored as a BAND and never as an age,
    # and only when it is not an adult's — see young.py. Before the matchmaker
    # for the same reason as the country: a failure to write him must not lose
    # the one fact that changes how he will speak.
    if req.age.strip():
        young.remember(user_id, req.age)

    # HIS NAME, which he gave in the very first line of the intake and which
    # never used to reach his friend: the voice took it from a deployment
    # setting from the single-user days. So the friend who had just been
    # written from eighteen of his answers opened by not knowing what to call
    # him. A fact like any other — and, like any other, not kept for a child.
    name = intake.their_name(req.about)
    if name:
        memory.add_memory(user_id, "fact", f"имя: {name}", owner="elder",
                          title="имя", importance=3)

    started = time.monotonic()
    try:
        p = await matchmaker.create_companion(
            user_id,
            req.about,
            wishes=req.wishes.strip(),
            # NOT `age=`. That parameter is the FRIEND's age as the person
            # wished it, and what the app sends as `age` is the person's OWN
            # age from the warm-up — so every adult was being handed a friend
            # their own age as law: «Кого он хотел бы встретить (закон):
            # возраст: 74». The biggest mirror of all, and nobody had asked
            # for it. An age they want for him is in their wishes, in words.
            # A teenager gets somebody their own age. Without this the ten
            # sketches are all grown-ups by construction, and no roll of the
            # dice can produce a peer out of a list that has none.
            band=young.of(user_id),
            gender=req.gender.strip(),
            origin=req.origin.strip(),
        )
    except Exception as e:  # noqa: BLE001
        raise _unavailable("🧠 writing him (Claude)", e)
    finally:
        allowance.spend(user_id, time.monotonic() - started)

    # The reading was made, used to write him, and — for a child — is not kept.
    # Here rather than on the first turn, because otherwise the most private
    # document this app produces would sit on disk from the moment somebody
    # signs up until the moment they say their first word.
    if young.keeps_nothing(user_id):
        young.forget(user_id)
    else:
        # What they told the intake, kept where their friend can use it — the
        # people in their life, the cat, what is coming up this week. After the
        # response, so nobody waits on it. See learn.from_intake.
        background_tasks.add_task(learn.from_intake, user_id, req.about)
    return JSONResponse({"name": p.get("name"), "persona": p})


@app.post("/api/companion/start-over")
async def companion_start_over(user_id: str = Depends(_user)) -> JSONResponse:
    """«Начать заново» — he goes, and everything between them goes with him.

    This is NOT deleting an account, and the two must never be wired to one
    button: somebody here wants a different friend, not to leave. What the app
    understands about them stays, so the next one does not open by asking them
    to tell their whole life again. See erase.py for what falls on each side.

    Until this existed the button cleared five keys on the phone and the sheet
    told the person, in writing, that he would forget everything and his diary
    would close forever. He forgot nothing.
    """
    return JSONResponse({"ok": True, "gone": erase.the_companion(user_id)})


@app.delete("/api/me")
async def erase_me(user_id: str = Depends(_user)) -> JSONResponse:
    """Everything. Every row in every table, every file, no way back.

    Scoped to the caller like every other route here: `user_id` comes from the
    token and from nowhere else, so there is no shape of request that deletes
    somebody else. It answers with what went rather than "ok", because a person
    who has just asked for this is owed more than being told to trust us.
    """
    return JSONResponse({"ok": True, "gone": erase.everything(user_id)})


class MemoryChoice(BaseModel):
    allow: bool


@app.post("/api/memory/keep")
async def memory_keep(
    req: MemoryChoice, user_id: str = Depends(_user)
) -> JSONResponse:
    """A teenager's own answer to «можно тебя помнить?».

    Only theirs. A child's is not taken — consent somebody cannot give is not
    consent, and a button that pretended otherwise would be worse than none,
    because it would look like a choice. An adult has nothing to answer: their
    friend has always remembered them. See young.allow.
    """
    return JSONResponse({"ok": True, "keeps": young.allow(user_id, req.allow)})


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


@app.get("/api/alerts")
async def alerts_dump(user_id: str = Depends(_user)) -> JSONResponse:
    """Everything the danger watcher has flagged — internal inspection only.

    Scoped to the caller, like every other read in this file. This exists
    because a watcher that decides when to break character has to be auditable:
    the only way to know whether it is calibrated is to read what it fired on
    and, beside the conversation log, what it let past. See safety.py.
    """
    return JSONResponse({"alerts": safety.recent(user_id)})


@app.get("/api/memory")
async def memory_dump(user_id: str = Depends(_user)) -> JSONResponse:
    """Raw distilled memory — internal/dev inspection only, never shown in the app.

    Scoped to the caller. It used to `SELECT ... FROM memories` with no WHERE
    at all, which on a server with more than one person on it is a single
    unauthenticated GET that returns everybody's private life.

    Retired memories are INCLUDED, carrying when and why they ended. This is the
    one view that must show them: the question somebody actually asks here is
    "why has he stopped mentioning the dog", and a dump that silently omitted
    the answer would make a wrong retirement impossible to find.
    """
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT owner, kind, title, content, status, recall_count, created_ts,"
            " superseded_ts, superseded_why "
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
