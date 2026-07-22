"""FastAPI app — the voice loop and the browser mic test page.

The talking loop (Phase 1):
    recorded audio  →  Whisper (ears)  →  Claude (brain)  →  ElevenLabs (mouth)  →  audio back

Endpoints:
    GET  /              → the browser mic test page
    GET  /api/health    → which services are configured (no secrets)
    POST /api/talk      → audio in  → {transcript, reply, audio} out  (full loop)
    POST /api/say       → text in   → {reply, audio} out  (skip the ears; for testing the brain+mouth)
"""

from __future__ import annotations

import base64
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from . import brain, config, memory, stt, tts

app = FastAPI(title="Voice Companion", version="0.1.0")

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
        }
    )


async def _think_and_speak(session_id: str, user_text: str) -> dict[str, str]:
    """Shared path: run the brain + mouth for a given user utterance."""
    history = memory.history_for_brain(session_id)
    history.append({"role": "user", "content": user_text})

    reply = await brain.generate_reply(
        history=history,
        facts_context=memory.facts_context(),
    )

    memory.save_turn(session_id, user_text, reply)

    audio_bytes = await tts.synthesize(reply)
    return {
        "reply": reply,
        "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
        "audio_mime": "audio/mpeg",
    }


@app.post("/api/talk")
async def talk(
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
        result = await _think_and_speak(session_id, transcript)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return JSONResponse({"transcript": transcript, **result})


class SayRequest(BaseModel):
    text: str
    session_id: str = "default"


@app.post("/api/say")
async def say(req: SayRequest) -> JSONResponse:
    """Text-in voice loop (skips the ears) — handy for testing brain + mouth."""
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text.")
    try:
        result = await _think_and_speak(req.session_id, text)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return JSONResponse({"transcript": text, **result})
