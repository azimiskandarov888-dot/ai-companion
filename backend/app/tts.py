"""The mouth: text-to-speech via ElevenLabs.

We call the ElevenLabs HTTP API directly (no extra SDK) and return MP3 bytes.
eleven_multilingual_v2 speaks natural Russian; the voice id is configurable so
you can pick a warm, neutral Russian-suited voice from the ElevenLabs library.
"""

from __future__ import annotations

import httpx

from . import config

_API_BASE = "https://api.elevenlabs.io/v1/text-to-speech"


def configured() -> bool:
    """Is the ElevenLabs 'mouth' set up? If not, the browser speaks for free
    (MVP path) — see static/index.html. On the phone the app would need a real
    voice, but for browser testing this keeps costs to just Whisper + Claude."""
    return bool(config.ELEVENLABS_API_KEY and config.ELEVENLABS_VOICE_ID)


async def synthesize(text: str) -> bytes:
    """Turn the companion's reply text into spoken audio (MP3 bytes)."""
    if not config.ELEVENLABS_API_KEY:
        raise RuntimeError(
            "ELEVENLABS_API_KEY is not set — the 'mouth' (ElevenLabs) is not configured."
        )
    if not text.strip():
        raise ValueError("Nothing to say — empty text passed to synthesize().")

    url = f"{_API_BASE}/{config.ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": config.ELEVENLABS_API_KEY,
        "accept": "audio/mpeg",
        "content-type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": config.ELEVENLABS_MODEL,
        # Warm, steady delivery for an elderly listener.
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        },
    }

    async with httpx.AsyncClient(timeout=60.0) as http:
        resp = await http.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
            # ElevenLabs returns JSON error detail on failure.
            detail = resp.text[:300]
            raise RuntimeError(
                f"ElevenLabs TTS failed ({resp.status_code}): {detail}"
            )
        return resp.content
