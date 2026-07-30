"""FastAPI app — the voice loop and memory.

Voice only. HE always speaks first (even by launching the app hands-free); Bob
only ever *responds* — never initiates.

Talking loop (with memory + persona):
    audio → 👂 Whisper → [persona + recalled facts/stories/follow-ups/mood]
          → 🧠 Claude → 🗣️ ElevenLabs → audio
          → (in the background) learn new memories

Endpoints:
    GET  /            → browser mic test page (a developer tool — he never sees a screen)
    GET  /api/health  → which services are configured + memory counts
    POST /api/talk    → audio in  → {transcript, reply, audio}   (the real loop)
    POST /api/say     → text in   → {reply, audio}   (dev only: test brain+memory)
    GET  /api/memory  → what it currently remembers (for you to inspect)
"""

from __future__ import annotations

import base64
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from . import brain, companion, config, db, learn, memory, occasions, persona, stt, tts


@asynccontextmanager
async def _lifespan(app: FastAPI):
    db.init_db()
    memory.seed_facts_from_file()  # import data/facts.json if the family provided one
    yield


app = FastAPI(title="Voice Companion", version="0.3.0", lifespan=_lifespan)

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> JSONResponse:
    services = config.service_status()
    return JSONResponse(
        {
            "ok": True,
            "companion_name": persona.persona_name(),
            "language": config.LANGUAGE,
            "brain_model": config.BRAIN_MODEL,
            "tts_provider": tts.provider_name(),
            "services": services,
            "all_ready": all(services.values()),
            "memory": memory.counts("elder"),
            "bob_self_facts": memory.counts("bob").get("fact", 0),
        }
    )


async def _think_and_speak(
    session_id: str, user_text: str, background_tasks: BackgroundTasks
) -> dict[str, str]:
    """Shared path: recall → assemble prompt → reply → speak, then learn."""
    memory.log_turn(session_id, "user", user_text)

    # Assemble everything Bob should have in mind.
    persona_block = persona.build_persona_block()
    elder_facts = memory.facts_context("elder")
    bob_facts = memory.bob_self_context()
    mem_ctx = await memory.build_memory_context(session_id, user_text)

    # If today is a special date, let Bob mention it warmly — but only in reply
    # to him (he never speaks first).
    occ = occasions.occasion_for()
    if occ:
        note = (
            f"Сегодня {occ['name']}. {occ['note']} "
            "Если это уместно и к слову — тепло упомяни это сам."
        )
        mem_ctx = f"{mem_ctx}\n\n{note}".strip() if mem_ctx else note

    system_prompt = companion.build_system_prompt(
        persona_block=persona_block,
        elder_facts=elder_facts,
        bob_facts=bob_facts,
        memory_context=mem_ctx,
        elder_name=config.ELDER_NAME,
    )

    history = memory.recent_turns(session_id)
    reply = await brain.generate_reply(history, system_prompt)

    memory.log_turn(session_id, "assistant", reply)
    # Learn from this exchange after the response is sent (keeps the voice fast).
    background_tasks.add_task(learn.learn_from_exchange, session_id, user_text, reply)

    # The mouth is optional. With an ElevenLabs key we return warm spoken audio.
    # Without one (MVP / browser testing), we return no audio and let the client
    # speak the reply with its own free voice — so testing needs only Whisper +
    # Claude. "voice" tells the client which path to take.
    if tts.configured():
        audio_bytes = await tts.synthesize(reply)
        return {
            "reply": reply,
            "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
            "audio_mime": "audio/mpeg",
            "voice": "server",
        }
    return {"reply": reply, "audio_base64": "", "audio_mime": "", "voice": "client"}


@app.post("/api/talk")
async def talk(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    session_id: str = Form("default"),
) -> JSONResponse:
    """Full voice loop: audio → transcript → reply → spoken audio."""
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio upload.")

    try:
        transcript = await stt.transcribe(
            audio_bytes, filename=audio.filename or "audio.webm"
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if not transcript:
        return JSONResponse(
            {"transcript": "", "reply": "", "note": "No speech detected."}
        )

    try:
        result = await _think_and_speak(session_id, transcript, background_tasks)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return JSONResponse({"transcript": transcript, **result})


class SayRequest(BaseModel):
    text: str
    session_id: str = "default"


@app.post("/api/say")
async def say(req: SayRequest, background_tasks: BackgroundTasks) -> JSONResponse:
    """Text-in voice loop (skips the ears) — for testing brain + memory + mouth."""
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text.")
    try:
        result = await _think_and_speak(req.session_id, text, background_tasks)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return JSONResponse({"transcript": text, **result})


@app.get("/api/memory")
async def memory_dump() -> JSONResponse:
    """A window into what the companion currently remembers (for inspection)."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT owner, kind, title, content, status, recall_count, created_ts "
            "FROM memories ORDER BY created_ts DESC LIMIT 200"
        ).fetchall()
    return JSONResponse(
        {
            "elder": memory.counts("elder"),
            "bob": memory.counts("bob"),
            "memories": [dict(r) for r in rows],
        }
    )
