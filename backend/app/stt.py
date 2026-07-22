"""The ears: speech-to-text via OpenAI Whisper.

Whisper is strong on elderly / accented / noisy Russian, which is exactly our
case. We transcribe with language hint "ru".
"""

from __future__ import annotations

from openai import AsyncOpenAI

from . import config

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if not config.OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not set — the 'ears' (Whisper) are not configured."
        )
    if _client is None:
        _client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    return _client


async def transcribe(
    audio_bytes: bytes,
    filename: str = "audio.webm",
    language: str = config.LANGUAGE,
) -> str:
    """Turn recorded audio into text. Returns the recognized transcript."""
    client = _get_client()
    result = await client.audio.transcriptions.create(
        model=config.WHISPER_MODEL,
        file=(filename, audio_bytes),
        language=language,
    )
    return (result.text or "").strip()
