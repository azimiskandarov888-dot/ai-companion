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
# Two models, because the app does two very different kinds of thinking:
#
#   WRITING him (once, at the arriving screen) — deep work. Creating a person,
#   rewriting the diary. Seconds don't matter there; quality does.
#
#   BEING him (every turn, out loud) — a short warm sentence or two. Here every
#   second is a silence the listener sits through, so speed IS the quality.
#
# One model for both means either slow conversation or a shallow character.
# Haiku 4.5 answers noticeably faster than Sonnet and, given a fully written
# persona to inhabit (it plays the character; it doesn't have to invent one),
# the warmth survives. If a Mac and budget can take it, CHAT_MODEL=claude-sonnet-5
# in .env brings the bigger brain back to every turn.
BRAIN_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
CHAT_MODEL: str = os.getenv("CHAT_MODEL", "claude-haiku-4-5-20251001")

# READING him — once, before he even exists. The deepest work the app does:
# understanding a person from HOW they wrote, not just what they wrote (see
# reading.py). This is the one call where the best model and real thinking
# time are worth minutes and cents, because it happens once per person and
# every other stage is built on its output.
READING_MODEL: str = os.getenv("READING_MODEL", "claude-opus-5")

# ASKING him about himself (app/intake.py) — the conversation that replaces
# the blank «расскажите о себе» page. Not deep work, but the quality of each
# follow-up decides whether someone opens up or gives up, so it gets the
# middle model rather than the fast one: a bad question wastes the only
# chance the app has to hear this person in their own voice.
INTAKE_MODEL: str = os.getenv("INTAKE_MODEL", BRAIN_MODEL)
#: low | medium | high | xhigh | max — how long it may think before answering.
READING_EFFORT: str = os.getenv("READING_EFFORT", "high")

# --- The ears: OpenAI Whisper ----------------------------------------------
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "whisper-1")

# --- Memory: embeddings for semantic story recall (reuses the OpenAI key) --
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
# Smaller dimension = lighter storage + faster similarity, still strong for one user.
EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "512"))

# --- The mouth: text-to-speech ---------------------------------------------
#
# TWO VOICES, NOT ONE. The companion is invented per person (matchmaker.py)
# and roughly half of the people it invents are women — Зоя the crane
# operator, Тамара who spent thirty years as a train conductor. With a
# single global voice setting, every one of them spoke as a man. Nothing
# breaks the illusion faster, and it is the illusion the whole app rests on.
#
# So each provider has a male and a female voice, and the persona says which
# it is. Leaving the female one empty falls back to the other — the old
# behaviour, kept so nothing silently stops speaking.
# Which voice provider speaks Bob's replies:
#   "yandex"     — Yandex SpeechKit. Cheapest for Russian by a distance, and
#                  the most Russian-sounding. See docs/HIS-VOICE.md.
#   "openai"     — same key as the ears; takes a direction on HOW to speak.
#   "fish"       — Fish Audio. Excellent, but bills UTF-8 BYTES, so Russian
#                  costs double the headline. The current default.
#   "elevenlabs" — warmest, several times the price.
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
#: The voice for a companion who turns out to be a woman. Fish has no
#: sensible default here — pick a second id from fish.audio/discovery. Left
#: empty, a female character speaks in the voice above, which is wrong and
#: audible.
FISH_VOICE_ID_FEMALE: str = os.getenv("FISH_VOICE_ID_FEMALE", "")
# Fish model version, sent as the `model` HTTP header. "s1" is stable; set
# FISH_MODEL=s2-pro (or the current name) for the newest open-weight model.
FISH_MODEL: str = os.getenv("FISH_MODEL", "s1")

# ElevenLabs (alternative voice). Used when TTS_PROVIDER=elevenlabs. A warm
# multilingual voice; default = "Sarah". eleven_multilingual_v2 handles Russian.
ELEVENLABS_API_KEY: str | None = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
#: NOTE the default above ("Sarah") is a WOMAN's voice, so on ElevenLabs it
#: is the MALE voice that needs setting, not the female one.
ELEVENLABS_VOICE_ID_FEMALE: str = os.getenv("ELEVENLABS_VOICE_ID_FEMALE", "")
ELEVENLABS_MODEL: str = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")

# --- Mouth: Yandex SpeechKit (TTS_PROVIDER=yandex) --------------------------
# Russian voices made by Russians, and it shows — the stress, the intonation and
# the way sentences end are right in a way that voices trained mostly on English
# rarely manage on Russian text.
#
# Voices are BARE NAMES. The `:premium` suffix that much of Yandex's own
# documentation still shows is rejected with a 400 by the live API.
#   premium tier:  filipp (male) · alena (female)
#   standard tier: ermil · zahar · jane · omazh · oksana
# `python3 audition.py --yandex` reports what your account really has.
#
# EMOTION IS OFF BY DEFAULT, and that makes him MORE expressive, not less.
# `emotion` is a crude override — one of neutral | good | evil applied to a
# WHOLE utterance — and not every voice accepts it. The better voices read
# each sentence and choose its intonation themselves, which is the thing
# `emotion` crudely approximates. Forcing "good" onto every line he ever says
# is what makes synthetic speech sound like a call centre.
#
# Set it only if you deliberately want one tone held throughout. If the voice
# rejects it, tts.py says so once and speaks without it rather than failing.
#
# Needs a Yandex Cloud account: an API key and the folder ID it belongs to.
YANDEX_API_KEY: str | None = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID: str = os.getenv("YANDEX_FOLDER_ID", "")
YANDEX_VOICE: str = os.getenv("YANDEX_VOICE", "filipp")
YANDEX_VOICE_FEMALE: str = os.getenv("YANDEX_VOICE_FEMALE", "alena")
YANDEX_EMOTION: str = os.getenv("YANDEX_EMOTION", "")
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
OPENAI_VOICE_FEMALE: str = os.getenv("OPENAI_VOICE_FEMALE", "sage")
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
# 260, not 400. Two reasons, both of them the same reason: a long reply takes
# longer to WRITE and much longer to SPEAK, and the voice is the slowest link
# in the turn. Cutting the ceiling shortens the silence before he answers —
# and he was talking too much anyway.
MAX_REPLY_TOKENS: int = int(os.getenv("MAX_REPLY_TOKENS", "260"))

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

# The reading of the USER (app/reading.py) — kept beside the persona but
# outliving it: a new companion doesn't make the person a different person, so
# «Начать заново» replaces persona.json and leaves this alone. Internal, like
# the distilled memory — never shown, never quoted back.
READING_PATH: Path = Path(os.getenv("READING_PATH", DATA_DIR / "reading.json"))


def service_status() -> dict[str, bool]:
    """Which of the three 'senses' are configured (no secrets exposed)."""
    return {
        "brain_claude": bool(ANTHROPIC_API_KEY),
        "ears_whisper": bool(OPENAI_API_KEY),
        "mouth": tts_configured(),
    }
