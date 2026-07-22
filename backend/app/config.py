"""Central configuration, loaded from environment variables (.env in dev).

All secrets live here and nowhere else. Nothing in this file is ever sent to
the client — the /api/health endpoint only reports whether a key is *present*,
never its value.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env if present (local development).
load_dotenv()

# --- The brain: Claude ------------------------------------------------------
ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
# Per the plan: Claude Opus 4.8.
BRAIN_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")

# --- The ears: OpenAI Whisper ----------------------------------------------
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "whisper-1")

# --- The mouth: ElevenLabs --------------------------------------------------
ELEVENLABS_API_KEY: str | None = os.getenv("ELEVENLABS_API_KEY")
# A warm multilingual voice. Swap for a Russian-suited voice from the
# ElevenLabs voice library. Default = "Sarah" (a gentle, warm preset).
ELEVENLABS_VOICE_ID: str = os.getenv(
    "ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL"
)
# eleven_multilingual_v2 handles Russian well.
ELEVENLABS_MODEL: str = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")

# --- General ----------------------------------------------------------------
LANGUAGE: str = os.getenv("COMPANION_LANGUAGE", "ru")
COMPANION_NAME: str = os.getenv("COMPANION_NAME", "Соня")
# Who the companion is talking to (used in greetings). Optional.
ELDER_NAME: str = os.getenv("ELDER_NAME", "")

# Keep replies short — this is spoken aloud to an elderly listener.
MAX_REPLY_TOKENS: int = int(os.getenv("MAX_REPLY_TOKENS", "400"))

# Where per-user memory + logs live (git-ignored).
DATA_DIR: Path = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


def service_status() -> dict[str, bool]:
    """Which of the three 'senses' are configured (no secrets exposed)."""
    return {
        "brain_claude": bool(ANTHROPIC_API_KEY),
        "ears_whisper": bool(OPENAI_API_KEY),
        "mouth_elevenlabs": bool(ELEVENLABS_API_KEY) and bool(ELEVENLABS_VOICE_ID),
    }
