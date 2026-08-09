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
# Claude Sonnet 5 by default: fast enough for real-time voice, cheaper, and very
# close to Opus in warmth. For maximum warmth (a touch slower), set
# ANTHROPIC_MODEL=claude-opus-4-8 in .env.
BRAIN_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

# --- The ears: OpenAI Whisper ----------------------------------------------
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "whisper-1")

# --- Memory: embeddings for semantic story recall (reuses the OpenAI key) --
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
# Smaller dimension = lighter storage + faster similarity, still strong for one user.
EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "512"))

# --- The mouth: text-to-speech ---------------------------------------------
# Which voice provider speaks Bob's replies:
#   "fish"       — Fish Audio (cheaper, open-weight, fast). The default.
#   "elevenlabs" — ElevenLabs (warm, cloud-only).
#   ""/"none"    — no server voice → the client speaks with its own free voice
#                  (the MVP path).
# NOTE: this is only the VOICE. The EARS stay on Whisper above — Fish Audio's
# speech-to-text does NOT support Russian, so it can't replace Whisper.
TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "fish").strip().lower()

# Fish Audio (https://fish.audio) — the default voice.
FISH_API_KEY: str | None = os.getenv("FISH_API_KEY")
# The voice to speak in — a "reference_id" from the Fish Audio voice library:
# pick a warm Russian voice on fish.audio and paste its id here. Empty string
# uses Fish's default voice.
FISH_VOICE_ID: str = os.getenv("FISH_VOICE_ID", "")
# Fish model version, sent as the `model` HTTP header. "s1" is stable; set
# FISH_MODEL=s2-pro (or the current name) for the newest open-weight model.
FISH_MODEL: str = os.getenv("FISH_MODEL", "s1")

# ElevenLabs (alternative voice). Used when TTS_PROVIDER=elevenlabs. A warm
# multilingual voice; default = "Sarah". eleven_multilingual_v2 handles Russian.
ELEVENLABS_API_KEY: str | None = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
ELEVENLABS_MODEL: str = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")

# --- Mouth: Yandex SpeechKit (TTS_PROVIDER=yandex) --------------------------
# Russian voices made by Russians, and it shows — the stress, the intonation and
# the way sentences end are right in a way that voices trained mostly on English
# rarely manage on Russian text.
#
# Male voices: filipp · zahar · ermil · anton   (add ":premium" for the best
# quality, e.g. filipp:premium). Female: alena · jane · oksana · omazh.
# Some voices take an emotion: neutral | good | evil.
#
# Needs a Yandex Cloud account: an API key and the folder ID it belongs to.
YANDEX_API_KEY: str | None = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID: str = os.getenv("YANDEX_FOLDER_ID", "")
YANDEX_VOICE: str = os.getenv("YANDEX_VOICE", "filipp")
YANDEX_EMOTION: str = os.getenv("YANDEX_EMOTION", "good")
# 1.0 is normal. Slightly under is kinder to an older listener.
YANDEX_SPEED: str = os.getenv("YANDEX_SPEED", "0.95")

# --- Mouth: OpenAI (TTS_PROVIDER=openai) ------------------------------------
# The same key that already does the ears, so there is nothing new to sign up
# for. Costs the same as Fish ($15 per million characters), speaks Russian, and
# is reachable in places where fish.audio is not.
#
# Voices: alloy · ash · ballad · coral · echo · fable · onyx · nova · sage ·
# shimmer · verse.  For a warm older man, `ash` and `onyx` are the ones to try
# first; `fable` and `ballad` are gentler. Listen before deciding — see
# backend/audition.py.
OPENAI_TTS_MODEL: str = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
OPENAI_VOICE: str = os.getenv("OPENAI_VOICE", "ash")
# Free-text direction for how to speak — supported by gpt-4o-mini-tts and
# genuinely powerful. This is where his warmth is set.
OPENAI_VOICE_STYLE: str = os.getenv(
    "OPENAI_VOICE_STYLE",
    "Тёплый, неторопливый пожилой друг. Говори спокойно и негромко, "
    "с настоящими паузами, как в живом разговоре. Не декламируй.",
)


def tts_configured() -> bool:
    """Is the selected voice provider set up? If not, the client speaks free."""
    if TTS_PROVIDER == "fish":
        return bool(FISH_API_KEY)
    if TTS_PROVIDER == "openai":
        return bool(OPENAI_API_KEY)
    if TTS_PROVIDER == "yandex":
        return bool(YANDEX_API_KEY) and bool(YANDEX_FOLDER_ID)
    if TTS_PROVIDER == "elevenlabs":
        return bool(ELEVENLABS_API_KEY) and bool(ELEVENLABS_VOICE_ID)
    return False

# --- General ----------------------------------------------------------------
LANGUAGE: str = os.getenv("COMPANION_LANGUAGE", "ru")
COMPANION_NAME: str = os.getenv("COMPANION_NAME", "Соня")
# Who the companion is talking to (used in greetings). Optional.
ELDER_NAME: str = os.getenv("ELDER_NAME", "")

# Keep replies short — this is spoken aloud to an elderly listener.
MAX_REPLY_TOKENS: int = int(os.getenv("MAX_REPLY_TOKENS", "400"))

# --- How much of the day he has ---------------------------------------------
# Three hours of conversation a day. Not rationing for its own sake: at API
# prices that is already about $40 a month, more than the subscription. The
# limit exists so one person cannot cost more than they pay. Enforced on the
# server (see allowance.py), never in the app.
DAILY_SECONDS: int = int(os.getenv("DAILY_SECONDS", str(3 * 60 * 60)))

# Where per-user memory + logs live (git-ignored).
DATA_DIR: Path = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# The memory database (SQLite now; a clean interface so Phase 2 can move to
# Postgres + pgvector without touching the rest of the app).
DB_PATH: Path = Path(os.getenv("DB_PATH", DATA_DIR / "companion.db"))

# Bob's persona lives in DATA (editable JSON) so his name, home, story, cast,
# and habits can be changed anytime WITHOUT touching code. If the file is
# absent, a built-in default persona is used. See app/persona.py.
PERSONA_PATH: Path = Path(os.getenv("PERSONA_PATH", DATA_DIR / "persona.json"))


def service_status() -> dict[str, bool]:
    """Which of the three 'senses' are configured (no secrets exposed)."""
    return {
        "brain_claude": bool(ANTHROPIC_API_KEY),
        "ears_whisper": bool(OPENAI_API_KEY),
        "mouth": tts_configured(),
    }
