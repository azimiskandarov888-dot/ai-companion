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
#
# THE VOICE IS GEMMA 4, through OpenRouter — the owner's choice by ear
# (2026-10-02, docs/ALIVE-BRAIN.md, round 3): four whole conversations, the
# same model on both sides, voiced blind as A–D — he picked D; and against a
# version of itself with a short prompt: «the conversation D is much, better».
# What was known when it was chosen, so nobody has to find it again:
#   · fast — 0.8–0.9 s to first words on the real prompt (live-talk check);
#   · in Russian it slips: «такой пекло» in round 1, «Чем обычнось
#     занимаешься» in its first call through the app — it was chosen by ear
#     in ENGLISH, so a Russian conversation wants listening to;
#   · its hosts keep no cache, so every turn pays for the whole prompt:
#     ~$0.0026 a reply, ~$2 a person a month at 25 exchanges a day — 4–5×
#     what Luna cost;
#   · at the provider's own temperature it gave the same reply word for word
#     twice in a row on the same prompt.
# Before it: GPT-5.6 Luna (2026-09-28, from 24 rehearsed first meetings). A
# model id with a «/» is sent to OpenRouter; CHAT_MODEL=openai/gpt-5.6-luna
# brings Luna back, CHAT_MODEL=claude-haiku-4-5 goes back to Claude.
#
# EVERY MODEL ID HERE IS THE UNDATED ALIAS, and that is a rule, not a
# preference. A dated id pins this app to one snapshot: it keeps answering in
# the voice of the day it was written until somebody happens to notice, and
# when that snapshot is retired it stops answering at all — on the turn, in
# front of the person, with no way for them to tell it from the friend having
# gone. The alias moves; the friend keeps talking.
#
# THE BACKGROUND AGENTS GO THROUGH OPENROUTER TOO (2026-10-08). Their ids carry
# a «/» now, so brain.think / brain.generate_text send them where the voice's
# goes, on the one key the owner has — with no Anthropic key, the old bare ids
# made every one of them quietly do nothing. The models are still the ones
# they were; each becomes whoever wins its stage of the owner's own blind test
# (myself.py, docs/MODELS-FOR-EACH-AGENT.md). A bare «claude-…» id set in .env
# still goes straight to Anthropic.
#
# The scribe, his week and the diary.
BRAIN_MODEL: str = os.getenv("ANTHROPIC_MODEL", "anthropic/claude-sonnet-5")
CHAT_MODEL: str = os.getenv("CHAT_MODEL", "google/gemma-4-31b-it")
#: The key for every «vendor/model» id — the voice above, and the owner's tools.
OPENROUTER_API_KEY: str | None = os.getenv("OPENROUTER_API_KEY")
#: WHERE OpenRouter sends him. Left to itself it picks a place by price, not
#: speed: Luna's first words came back in 1.46 s (median of three, the real
#: prompt, 2026-09-29), against 0.79 s from OpenAI's «fast» tier and 0.94 s
#: from Azure in Europe. So an OpenAI model goes to OpenAI's own places, in
#: this order (fast costs twice per token — about $0.0004 a Luna reply);
#: any other model — Gemma 4 is served by several hosts and none of these —
#: to whichever of its hosts is fastest right now. CHAT_PROVIDERS, when set,
#: is the order for any model. Fallbacks stay allowed either way: a host that
#: is down costs speed, never the answer (brain._where).
OPENAI_PROVIDERS: list[str] = ["openai/fast", "azure/eu", "openai", "amazon-bedrock/us-east-1"]
#: …and the places for the other models, in order — measured, never left to
#: OpenRouter. Asked to sort by latency, it sent Gemma 4 to SiliconFlow: first
#: words in 2.0–3.5 s on the real prompt, the live channel's answer 3.7–4.3 s
#: after the person stopped (2026-10-03). ModelRun: 0.33–0.45 s. And ONE host
#: for the whole conversation is the point: its prompt cache lives there —
#: 1.25 s cold, 0.32–0.54 s once it has read the instructions (5,120 of 5,177
#: tokens cached). All three keep Gemma at 4 bits; the hosts that keep it at 8
#: or 16 took 0.8–25 s or refused (rate-limited) — whether 4 bits costs her
#: Russian is a question for the brains' Russian round (docs/ALIVE-BRAIN.md).
CHAT_PROVIDERS_FOR: dict[str, list[str]] = {
    "google/gemma-4-31b-it": ["modelrun/fp4", "deepinfra/turbo", "coreweave/fp4"],
}
CHAT_PROVIDERS: list[str] = [
    p.strip() for p in os.getenv("CHAT_PROVIDERS", "").split(",") if p.strip()
]
#: How long he thinks before he speaks: not at all. Luna reasoned silently
#: before answering — 43–91 tokens of it on a second turn, a second of silence —
#: and «minimal» did NOT stop it (the first turn fooled an earlier test into
#: thinking it had). «none»: no reasoning, first words in 0.79–0.86 s on the
#: same prompt (2026-09-29). Empty leaves it to the model.
CHAT_REASONING: str = os.getenv("CHAT_REASONING", "none").strip()
#: When his first words have not come this many seconds after the brain was
#: asked, it is asked again, and whichever answers first is the one he says
#: (brain.stream_reply). Usually they come in 0.7–0.95 s from Tashkent; now and
#: then 2.8 s (2026-10-07). 0 turns it off.
BRAIN_HEDGE_AFTER: float = float(os.getenv("BRAIN_HEDGE_AFTER", "1.1"))

# READING him — once, before he even exists. The deepest work the app does:
# understanding a person from HOW they wrote, not just what they wrote (see
# reading.py). This is the one call where the best model and real thinking
# time are worth minutes and cents, because it happens once per person and
# every other stage is built on its output.
READING_MODEL: str = os.getenv("READING_MODEL", "anthropic/claude-opus-5")

# WRITING him — also once, immediately after the reading, and by the same
# argument. This used to run on BRAIN_MODEL (Sonnet) purely because it sat in
# the "composed writing" bucket with the diary. That was wrong on the merits:
# the diary can be rewritten any time and nobody depends on it, whereas THIS
# call produces the person somebody will talk to every day for months. It is,
# with the reading, one of the two calls in the app where quality outranks
# everything, and it happens once per user.
#
# So: the best model, real thinking time before writing, and a token budget
# generous enough that a rich character is never cut off (see
# matchmaker._WRITE_MAX_TOKENS — the previous 2500 was truncating people
# mid-backstory).
WRITER_MODEL: str = os.getenv("WRITER_MODEL", "anthropic/claude-opus-5")
#: How long the writer may think before it starts writing him.
#:
#: This used to be "medium", on the argument that «the reading is inference and
#: wants depth; this is composition, where past a point more deliberation buys
#: tidiness rather than life». The worry was right and the conclusion was not,
#: for two reasons.
#:
#: The prompt it is thinking about is now almost entirely ANTI-polish: real
#: faults with the smooth ones named and banned, a contradiction in himself,
#: something he is hopeless at, objects instead of adjectives, unfinished
#: business with the people around him. Deliberation against that prompt goes
#: into honouring those constraints, which is exactly where a fast pass fails —
#: the flawless, frictionless character is what you get when a model does not
#: think, not when it thinks too hard.
#:
#: And this is the ONE call that decides who somebody talks to every day for
#: months. It happens once per person and costs cents. Stepping its effort down
#: is a cost saving, and there is nothing here worth saving on.
WRITER_EFFORT: str = os.getenv("WRITER_EFFORT", "high")

# ASKING him about himself (app/intake.py) — the conversation that replaces
# the blank «расскажите о себе» page. Every question is the model's now, and
# each one's quality decides whether somebody opens up or gives up — so it
# gets the model with the best measured ear for what a particular person
# needs in a multi-turn conversation (#1 on EQ-Bench 4), not the middle one.
# It had been the middle one by default, never by comparison. Compared
# (2026-09-24), all seven candidates kept the list and all followed «ничем»
# with «а вчера, например?»; this one did it fastest of the Claude models,
# about three seconds a question. Once per person: about thirty cents.
INTAKE_MODEL: str = os.getenv("INTAKE_MODEL", "anthropic/claude-opus-5")
#: low | medium | high | xhigh | max — how long it may think before answering.
READING_EFFORT: str = os.getenv("READING_EFFORT", "high")

# WATCHING for danger (app/safety.py) — the one call in the app whose prompt
# does exactly one thing. The fast model, deliberately: the question is narrow
# ("is this person in danger right now?"), a bigger model buys nothing on it,
# and this runs on every single turn beside a person who may be having a
# stroke. Cheap and quick is the requirement, not deep.
#
# Its OWN default, not the voice's. It used to be CHAT_MODEL — and when the
# voice moved to OpenRouter, the watcher would have followed it onto a Claude
# client that cannot call it, failed on every turn, and, because safety.look
# never raises, quietly answered «no danger» to everybody from then on.
# Through OpenRouter since 2026-10-08, the same model: which one watches is
# decided by a labelled Russian crisis set, never by feel (HANDOVER §11).
SAFETY_MODEL: str = os.getenv("SAFETY_MODEL", "anthropic/claude-haiku-4.5")
#: Hard ceiling. It runs concurrently with work the turn was doing anyway, so
#: it normally costs no wall time at all — but a hung connection must never be
#: what stands between somebody and their answer. Missing the alarm once is
#: bad; freezing the conversation of everyone who is fine is worse.
SAFETY_TIMEOUT: float = float(os.getenv("SAFETY_TIMEOUT", "6"))
#: What he tells somebody to dial. 103 is the ambulance in Russia and most of
#: the former USSR; 112 reaches emergency services from any phone including one
#: with no SIM, which is why both are said. Set EMERGENCY_NUMBER for elsewhere.
EMERGENCY_NUMBER: str = os.getenv("EMERGENCY_NUMBER", "103")

# --- The ears: OpenAI Whisper ----------------------------------------------
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "whisper-1")

# --- The ears, live: Deepgram Flux (the live channel — live.py) ------------
#
# Whisper hears a FINISHED recording: the phone waited 1.2 s of silence, sent
# the file, and only then did 0.75–1.5 s of recognising begin. Flux hears while
# the person is still talking, and says itself when they have finished — by
# what was said and how, not by a timer. Measured on Russian through the
# European address (2026-09-29): «похоже, договорил» 0.34 s after the last
# word, «договорил» 0.63 s after it at the 0.7 threshold — 0.8–1.6 s at the
# 0.85 it uses now, which cuts people off less (below). See docs/LATENCY.md.
DEEPGRAM_API_KEY: str | None = os.getenv("DEEPGRAM_API_KEY")
#: Europe: 80 ms there and back from Tashkent, against 240 for the US address.
DEEPGRAM_URL: str = os.getenv("DEEPGRAM_URL", "wss://api.eu.deepgram.com/v2/listen")
#: Russian lives in the multilingual model; the hint is COMPANION_LANGUAGE.
FLUX_MODEL: str = os.getenv("FLUX_MODEL", "flux-general-multi")
#: How sure Flux must be that somebody has finished. Deepgram's default, 0.7,
#: cut the owner off in the middle of what he was saying (2026-09-30). Measured
#: on six phrases with a pause in the middle, streamed in real time: 0.7 ended
#: the turn inside the pause in four of the five that had one, 0.8 in three,
#: 0.85 in two, 0.9 in none — but 0.9 then waited out the whole five-second
#: timeout at the real end as well. 0.85 answers a finished phrase 0.8–1.6 s
#: after its last word, which is mostly time the brain is still writing
#: anyway (its first words take ~1.3 s from the end), so it costs at most
#: ~0.2 s, on long phrases only. A pause after a finished sentence stays
#: ambiguous at any threshold; the real answer to that is letting them talk
#: over him (the live channel's `duplex`).
FLUX_EOT_THRESHOLD: float = float(os.getenv("FLUX_EOT_THRESHOLD", "0.85"))
#: The same when they CAN talk over him (the live channel's `duplex`, now the
#: default): a turn ended too early is mended by carrying on — he stops and
#: listens — so it can be quicker. 0.8 still cuts in less than 0.7 did, and
#: its «договорил» (0.5–1.3 s after the last word) almost always comes while
#: the brain is still writing.
FLUX_EOT_THRESHOLD_DUPLEX: float = float(os.getenv("FLUX_EOT_THRESHOLD_DUPLEX", "0.8"))
#: The earlier, less certain «похоже, договорил» — the brain starts writing
#: then, and the draft is thrown away if they carry on. Lower is earlier and
#: more drafts wasted (Deepgram: 0.3–0.5 costs 50–70% more calls — for Luna,
#: fractions of a cent).
FLUX_EAGER_EOT_THRESHOLD: float = float(os.getenv("FLUX_EAGER_EOT_THRESHOLD", "0.4"))
#: The most silence that can still mean «not finished». Five seconds: an old
#: man gathering a thought is not a man who has stopped.
FLUX_EOT_TIMEOUT_MS: int = int(os.getenv("FLUX_EOT_TIMEOUT_MS", "5000"))
#: Deepgram bills every second the line is open, silence included. A tab left
#: open all night must not be a night of billing: after this long with nobody
#: speaking, the live channel closes itself.
LIVE_IDLE_SECONDS: float = float(os.getenv("LIVE_IDLE_SECONDS", "120"))

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
#   "gemini"     — Google's Gemini voices (GEMINI_TTS_MODEL), streamed on Google's key.
#                  THE DEFAULT SINCE 2026-10-03: the owner heard 21 voices of
#                  five makers blind, and all six he liked were Gemini's; then
#                  all thirty of Gemini's: «all of them are briliant». Every
#                  companion gets one of his own (voices.py). Streamed only —
#                  the owner: «We are never going to use non-streaming voice».
#   "yandex"     — Yandex SpeechKit. Cheapest for Russian by a distance, and
#                  the most Russian-sounding. See docs/HIS-VOICE.md.
#   "openai"     — same key as the ears; takes a direction on HOW to speak.
#   "fish"       — Fish Audio. Bills UTF-8 BYTES, so Russian costs double the
#                  headline. The default until 2026-10-03; its Russian voices
#                  were the ones the owner called «horrible». With no Fish key
#                  but an OpenRouter one, the same voice through OpenRouter
#                  (voice_provider, below).
#   "elevenlabs" — warmest, several times the price.
#   "openrouter" — Fish Audio (FISH_MODEL) through OpenRouter, on the one key
#                  the owner has. Exactly how his sounds were tested (docs/SOUNDS.md).
#   ""/"none"    — no server voice → the client speaks with its own free voice
#                  (the MVP path).
# NOTE: this is only the VOICE. The EARS stay on Whisper above — Fish Audio's
# speech-to-text does NOT support Russian, so it can't replace Whisper.
TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "gemini").strip().lower()

#: Which Gemini voice model (an OpenRouter id; Google's own is the part after
#: the «/»). The owner heard the same voice in three of them, blind: «Equally
#: good. But they are different» — 3.8 Flash the calmest, 3.8 Flash-Lite
#: neutral, 3.1 Flash the most emotional; then, told that only 3.8 makes voices
#: from a description and costs a quarter: «we will go with 3.8 for more voices
#: and less price tag» (2026-10-03). Flash-Lite of the two: on Google's own
#: stream its first sound came in 0.63–0.93 s, Flash's in 1.07–1.10 s, and it
#: costs $6 a million sound tokens to Flash's $9.
GEMINI_TTS_MODEL: str = os.getenv("GEMINI_TTS_MODEL", "google/gemini-3.8-flash-lite-tts")
#: Google's own key for the same voices (aistudio.google.com → «Get API key»).
#: The voice comes as a STREAM on it — the first sound while the rest is still
#: being made (tts._gemini_direct_stream). Without it there is no server voice.
#: Google's free tier allows 10 requests a day per model: a conversation needs
#: billing on the Google project.
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
#: …and how many requests a minute Google takes on it for the voice model: 10
#: on a paid key's first tier (measured 2026-10-07 — the 11th within a minute
#: is refused, GenerateRequestsPerMinutePerProjectPerModel). Kept to by
#: tts._budget, so his words are never refused for it. 0: no limit.
GEMINI_TTS_RPM: int = int(os.getenv("GEMINI_TTS_RPM", "10"))
#: The same voices on Google Cloud (Gemini Enterprise Agent Platform): an API
#: key bound to a service account, and the project it is in. When both are
#: set the voice goes there: on the AI Studio key Google takes 10 requests a
#: minute and 100 a day for it — not one conversation's worth (2026-10-07);
#: here, fifteen in ten seconds went through, first sound 0.49–0.66 s once
#: the line was open (2026-10-08). Billed to the card at the month's end.
GOOGLE_CLOUD_API_KEY: str | None = os.getenv("GOOGLE_CLOUD_API_KEY")
GOOGLE_CLOUD_PROJECT: str | None = os.getenv("GOOGLE_CLOUD_PROJECT")


def gemini_on_cloud() -> bool:
    return bool(GOOGLE_CLOUD_API_KEY and GOOGLE_CLOUD_PROJECT)

# Fish Audio (https://fish.audio) — the default voice.
FISH_API_KEY: str | None = os.getenv("FISH_API_KEY")
# The voice to speak in — a "reference_id" from the Fish Audio voice library
# (the same ids through OpenRouter). UNTIL THE OWNER CHOOSES BY EAR, two
# generic library voices, neither of them anybody's clone by name: «Молодой
# Русский Рассказчик» and «Молодой Женский Голос» — the second is plainly a
# woman (≈210 Hz, heard as one); the «Спокойный женский голос» the sound tests
# used is heard as a man. Empty would be whatever Fish defaults to — a voice
# nobody chose, which is no voice for somebody's friend.
FISH_VOICE_ID: str = os.getenv("FISH_VOICE_ID", "c962ed46edfd419abc530d1e33a7435f")
#: The voice for a companion who turns out to be a woman. Left empty, a female
#: character speaks in the voice above, which is wrong and audible.
FISH_VOICE_ID_FEMALE: str = os.getenv("FISH_VOICE_ID_FEMALE", "d567e990d9ad433892ed15ecfd70ce54")
#: The voices of a conversation in English (COMPANION_LANGUAGE=en): Fish's own
#: English companion voices, not anybody's clone — «Kai — Male companion (EN)»
#: and «Mila — Female companion (EN)» from the Fish Official library
#: (2026-10-02). The Russian voices above would read English with an accent.
FISH_VOICE_ID_EN: str = os.getenv("FISH_VOICE_ID_EN", "0db6e93af420470b9d9b9a886dbaa954")
FISH_VOICE_ID_FEMALE_EN: str = os.getenv("FISH_VOICE_ID_FEMALE_EN", "7f3375b90d3e4494bbb1a3cbbf56c607")
# Fish model version — the `model` HTTP header, or «fish-audio/<it>» through
# OpenRouter. s2.1-pro — Fish's own production model, S1 is legacy — at the
# same $15 per million bytes. It is the one that can make his SOUNDS: a
# cough, «кхм», a sigh, a laugh, a yawn, played in his own voice from a tag
# rather than read out (docs/SOUNDS.md; tts.SOUNDS). S1 cannot, and with it
# the markers are simply removed as before.
FISH_MODEL: str = os.getenv("FISH_MODEL", "s2.1-pro")

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


def voice_provider() -> str:
    """Which voice actually speaks: TTS_PROVIDER, with one substitution.

    «fish» with no Fish key but an OpenRouter one is the SAME voice — Fish
    S2.1, the same voice ids — reached through OpenRouter. The owner has only
    that key, and without this the server said nothing at all: every reply went
    to the phone's own free voice, and his sounds went nowhere.
    """
    if TTS_PROVIDER == "fish" and not FISH_API_KEY and OPENROUTER_API_KEY:
        return "openrouter"
    return TTS_PROVIDER


def tts_configured() -> bool:
    """Is the selected voice provider set up? If not, the client speaks free."""
    provider = voice_provider()
    if provider == "gemini":
        return bool(GEMINI_API_KEY) or gemini_on_cloud()
    if provider == "fish":
        return bool(FISH_API_KEY)
    if provider == "openrouter":
        return bool(OPENROUTER_API_KEY)
    if provider == "openai":
        return bool(OPENAI_API_KEY)
    if provider == "yandex":
        return bool(YANDEX_API_KEY) and bool(YANDEX_FOLDER_ID)
    if provider == "elevenlabs":
        return bool(ELEVENLABS_API_KEY) and bool(ELEVENLABS_VOICE_ID)
    return False

# --- General ----------------------------------------------------------------
LANGUAGE: str = os.getenv("COMPANION_LANGUAGE", "ru")
#: The name of the FALLBACK companion only (persona.DEFAULT_PERSONA) — whoever
#: has no friend of their own yet. He is an 87-year-old man, so «Боб»: the old
#: default «Соня» gave a man's life, a man's grammar and a man's voice a
#: woman's name, and the model mixed them («Я Соня… гулял»).
COMPANION_NAME: str = os.getenv("COMPANION_NAME", "Боб")
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
        # Named for what it used to be; the app shows it as «мозг». It is the
        # key the CONVERSATION needs — OpenRouter's once the voice is there.
        "brain_claude": bool(OPENROUTER_API_KEY if "/" in CHAT_MODEL else ANTHROPIC_API_KEY),
        "ears_whisper": bool(OPENAI_API_KEY),
        # The live channel's ears (live.py). Without them /api/live says so
        # and the file-by-file path above is all there is.
        "ears_live": bool(DEEPGRAM_API_KEY),
        "mouth": tts_configured(),
    }
