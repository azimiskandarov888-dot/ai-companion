"""The mouth: text-to-speech.

Three providers, chosen by config.TTS_PROVIDER:
  - "fish"       Fish Audio — open-weight, fast, good Russian. Default.
  - "openai"     OpenAI — same key as the ears, same price as Fish, speaks
                 Russian, and reachable where fish.audio is not.
  - "yandex"     Yandex SpeechKit — Russian voices made for Russian. Best
                 prosody of the lot on Russian text, and cheap.
  - "elevenlabs" ElevenLabs — warmest, and several times the price.
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
_OPENAI_TTS_URL = "https://api.openai.com/v1/audio/speech"
_YANDEX_TTS_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"


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

    if config.TTS_PROVIDER == "openai":
        if not config.OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY is not set — the OpenAI voice is not configured."
            )
        return await _synthesize_openai(text)

    if config.TTS_PROVIDER == "yandex":
        if not (config.YANDEX_API_KEY and config.YANDEX_FOLDER_ID):
            raise RuntimeError(
                "YANDEX_API_KEY / YANDEX_FOLDER_ID not set — the Yandex voice "
                "is not configured."
            )
        return await _synthesize_yandex(text)

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
        # "balanced" starts returning audio sooner than "normal" at a
        # quality cost nobody has ever noticed in a spoken sentence. The
        # voice is the slowest link in the turn, so this is the cheapest
        # second available.
        "latency": "balanced",
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


async def _synthesize_openai(text: str) -> bytes:
    """OpenAI TTS. Returns MP3 bytes.

    `instructions` is the interesting part: gpt-4o-mini-tts takes a plain-language
    direction for HOW to speak, not just what to say. That is where his warmth
    actually comes from — the same words read as a news bulletin or as a friend
    are two different products.
    """
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload: dict = {
        "model": config.OPENAI_TTS_MODEL,
        "voice": config.OPENAI_VOICE,
        "input": text,
        "response_format": "mp3",
    }
    if config.OPENAI_VOICE_STYLE:
        payload["instructions"] = config.OPENAI_VOICE_STYLE

    async with httpx.AsyncClient(timeout=60.0) as http:
        resp = await http.post(_OPENAI_TTS_URL, headers=headers, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(
                f"OpenAI TTS failed ({resp.status_code}): {resp.text[:300]}"
            )
        return resp.content


async def _synthesize_yandex(text: str) -> bytes:
    """Yandex SpeechKit. Form-encoded, not JSON. Returns MP3 bytes."""
    headers = {"Authorization": f"Api-Key {config.YANDEX_API_KEY}"}
    data = {
        "text": text,
        "lang": "ru-RU",
        "voice": config.YANDEX_VOICE,
        "speed": config.YANDEX_SPEED,
        "format": "mp3",
        "folderId": config.YANDEX_FOLDER_ID,
    }
    # Not every voice accepts an emotion, and sending one to a voice that
    # doesn't is an error rather than a shrug — so it stays optional.
    if config.YANDEX_EMOTION:
        data["emotion"] = config.YANDEX_EMOTION

    async with httpx.AsyncClient(timeout=60.0) as http:
        resp = await http.post(_YANDEX_TTS_URL, headers=headers, data=data)
        if resp.status_code != 200:
            raise RuntimeError(
                f"Yandex SpeechKit failed ({resp.status_code}): {resp.text[:300]}"
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
