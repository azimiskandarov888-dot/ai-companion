"""The mouth: text-to-speech.

Two providers, chosen by config.TTS_PROVIDER:
  - "fish"       Fish Audio — cheaper, open-weight, fast, good Russian. Default.
  - "elevenlabs" ElevenLabs — warm, cloud-only.
Both return MP3 bytes, so the rest of the app doesn't care which spoke.

If no provider is configured, main.py falls back to letting the client speak
with its own free voice (the MVP path). The EARS stay on Whisper regardless —
Fish Audio's speech-to-text doesn't support Russian (see stt.py).
"""

from __future__ import annotations

import httpx

from . import config

_FISH_API_URL = "https://api.fish.audio/v1/tts"
_ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1/text-to-speech"


def configured() -> bool:
    """Is the selected voice provider set up? (Single source of truth: config.)"""
    return config.tts_configured()


def provider_name() -> str:
    """Which voice is speaking — for the health endpoint (no secrets)."""
    return config.TTS_PROVIDER or "none"


async def synthesize(text: str) -> bytes:
    """Turn Bob's reply into spoken audio (MP3 bytes), via the chosen provider."""
    if not text.strip():
        raise ValueError("Nothing to say — empty text passed to synthesize().")

    if config.TTS_PROVIDER == "fish":
        if not config.FISH_API_KEY:
            raise RuntimeError(
                "FISH_API_KEY is not set — the Fish Audio voice is not configured."
            )
        return await _synthesize_fish(text)

    if config.TTS_PROVIDER == "elevenlabs":
        if not (config.ELEVENLABS_API_KEY and config.ELEVENLABS_VOICE_ID):
            raise RuntimeError(
                "ELEVENLABS_API_KEY / ELEVENLABS_VOICE_ID not set — the ElevenLabs "
                "voice is not configured."
            )
        return await _synthesize_elevenlabs(text)

    raise RuntimeError(
        f"No voice provider configured (TTS_PROVIDER={config.TTS_PROVIDER!r})."
    )


async def _synthesize_fish(text: str) -> bytes:
    """Fish Audio TTS. POST /v1/tts with the model in a header; returns MP3 bytes."""
    headers = {
        "Authorization": f"Bearer {config.FISH_API_KEY}",
        "Content-Type": "application/json",
        # Fish selects the model version via this header (e.g. "s1", "s2-pro").
        "model": config.FISH_MODEL,
    }
    payload: dict = {
        "text": text,
        "format": "mp3",
        "mp3_bitrate": 128,
        "normalize": True,   # tidy punctuation/numbers for natural speech
        "latency": "normal",
    }
    # A chosen voice from the Fish library; omit to use Fish's default voice.
    if config.FISH_VOICE_ID:
        payload["reference_id"] = config.FISH_VOICE_ID

    async with httpx.AsyncClient(timeout=60.0) as http:
        resp = await http.post(_FISH_API_URL, headers=headers, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(
                f"Fish Audio TTS failed ({resp.status_code}): {resp.text[:300]}"
            )
        return resp.content


async def _synthesize_elevenlabs(text: str) -> bytes:
    """ElevenLabs TTS (eleven_multilingual_v2 handles Russian). Returns MP3 bytes."""
    url = f"{_ELEVENLABS_API_BASE}/{config.ELEVENLABS_VOICE_ID}"
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
            raise RuntimeError(
                f"ElevenLabs TTS failed ({resp.status_code}): {resp.text[:300]}"
            )
        return resp.content
