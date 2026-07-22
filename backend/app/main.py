"""FastAPI app — the voice loop, memory, and the proactive good-morning.

Talking loop (with memory):
    audio → 👂 Whisper → [recall facts + stories + follow-ups + mood]
          → 🧠 Claude → 🗣️ ElevenLabs → audio
          → (in the background) learn new facts/stories/follow-ups

Endpoints:
    GET  /               → browser mic test page
    GET  /api/health     → which services are configured + memory counts
    POST /api/talk       → audio in  → {transcript, reply, audio}
    POST /api/say        → text in   → {reply, audio}  (skip the ears)
    POST /api/proactive  → the companion speaks first (good morning / spontaneous)
    GET  /api/memory     → what it currently remembers (for you to inspect)
"""

from __future__ import annotations

import base64
import datetime as dt
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from . import brain, config, db, learn, memory, occasions, stt, tts


@asynccontextmanager
async def _lifespan(app: FastAPI):
    db.init_db()
    memory.seed_facts_from_file()  # import data/facts.json if the family provided one
    yield


app = FastAPI(title="Voice Companion", version="0.2.0", lifespan=_lifespan)

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
            "companion_name": config.COMPANION_NAME,
            "language": config.LANGUAGE,
            "brain_model": config.BRAIN_MODEL,
            "services": services,
            "all_ready": all(services.values()),
            "memory": memory.counts(),
        }
    )


async def _think_and_speak(
    session_id: str, user_text: str, background_tasks: BackgroundTasks
) -> dict[str, str]:
    """Shared path: recall → reply → speak, then learn in the background."""
    memory.log_turn(session_id, "user", user_text)

    facts_ctx, mem_ctx = await memory.build_reply_context(session_id, user_text)
    history = memory.recent_turns(session_id)

    reply = await brain.generate_reply(
        history=history, memory_context=mem_ctx, facts_context=facts_ctx
    )

    memory.log_turn(session_id, "assistant", reply)
    # Learn from this exchange after the response is sent (keeps the voice fast).
    background_tasks.add_task(learn.learn_from_exchange, session_id, user_text, reply)

    audio_bytes = await tts.synthesize(reply)
    return {
        "reply": reply,
        "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
        "audio_mime": "audio/mpeg",
    }


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


class ProactiveRequest(BaseModel):
    session_id: str = "default"
    kind: str = "morning"  # morning | spontaneous
    # Optional override so you can test a special-date greeting on any day,
    # e.g. {"occasion": "8 Марта"}.
    occasion: str | None = None


@app.post("/api/proactive")
async def proactive(
    req: ProactiveRequest, background_tasks: BackgroundTasks
) -> JSONResponse:
    """The companion starts the conversation first — a warm good morning that
    weaves in a memory, a caring follow-up, his mood, and any special date."""
    facts_ctx, mem_ctx = await memory.build_reply_context(
        req.session_id, "", for_greeting=True
    )

    now = dt.datetime.now()
    part_of_day = (
        "утро" if now.hour < 12 else "день" if now.hour < 18 else "вечер"
    )
    occ = occasions.occasion_for(now.date())
    occasion_line = ""
    if req.occasion:
        occasion_line = f"Сегодня особый день: {req.occasion}. "
    elif occ:
        occasion_line = f"Сегодня {occ['name']}. {occ['note']} "

    if req.kind == "morning":
        stage = (
            f"Сейчас {part_of_day}. Ты сам начинаешь разговор — тёпло поздоровайся "
            f"и пожелай доброго утра. {occasion_line}"
        )
    else:
        stage = (
            f"Сейчас {part_of_day}. Ты сам, по-дружески, заводишь разговор. "
            f"{occasion_line}"
        )

    try:
        reply = await brain.compose_opening(
            stage_direction=stage, memory_context=mem_ctx, facts_context=facts_ctx
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    memory.log_turn(req.session_id, "assistant", reply)

    audio_b64 = ""
    audio_mime = "audio/mpeg"
    try:
        audio_b64 = base64.b64encode(await tts.synthesize(reply)).decode("ascii")
    except RuntimeError:
        pass  # voice optional here; text greeting still returned

    return JSONResponse(
        {"reply": reply, "audio_base64": audio_b64, "audio_mime": audio_mime}
    )


@app.get("/api/memory")
async def memory_dump() -> JSONResponse:
    """A window into what the companion currently remembers (for inspection)."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT kind, title, content, status, recall_count, created_ts "
            "FROM memories ORDER BY created_ts DESC LIMIT 200"
        ).fetchall()
    return JSONResponse(
        {
            "counts": memory.counts(),
            "memories": [dict(r) for r in rows],
        }
    )
