# Voice Companion for Great-Grandad — PLAN

A talking friend for my great-grandad. He speaks, it speaks back — in Russian.
It remembers his stories and health, says "good morning," and tells stories too.
**Voice only. No typing.**

---

## THE SIMPLE VERSION

### What it does
- Listens to him in Russian and talks back in a warm Russian voice
- Remembers everything he says (stories, family, health) and brings it up later
- Starts talking on its own: "Good morning", reminders, old stories
- Never gives medical advice — only says "let's call your doctor"
- Always honest that it is an AI

### The iPhone truth (important)
An iPhone **cannot listen when the app is closed** — only Siri is allowed to do that.
So:
- **At home (main use):** phone in a stand, plugged in, app always open and locked to just this one app (iOS "Guided Access"). It listens all day and talks on its own. Works perfectly.
- **Walking around:** he says *"Привет Siri, открой [name]"* to start it. (Plus a best-effort background mode, since this is a private family app.)

### The parts (like a person)
- **Brain** (thinks + remembers) = **Claude**
- **Ears** (hears messy old Russian) = **Whisper** (OpenAI)
- **Mouth** (warm Russian voice) = **Fish Audio** (default; ElevenLabs optional)
- **Memory** (stores everything) = a database (storage is cheap, not a problem)

We mix the best from each company. We are not locked to one.
Before trusting the "ears," we test it with a **real recording of his voice**.

### The plan (fast)
1. **First:** build the brain + memory. Hear it talk Russian in a simple test page — before the iPhone app exists.
2. **Then:** build the iPhone app (on the Mac).
3. **Later:** family voice messages, reminders, emergency call.

---

## DECISIONS ALREADY MADE (locked)
- **Phone:** iPhone (private app, not from the App Store — we install it ourselves)
- **Build machine:** Mac Pro (Windows cannot build iPhone apps)
- **Language:** Russian
- **Voice:** warm neutral Russian voice (no voice cloning)
- **Cost:** not a concern — use the best tools
- **Brain:** Claude (recommended over ChatGPT for Russian + memory + warmth)

---

## GET THESE READY (accounts / keys)
So we can move fast, create these and save the API keys:
1. **Anthropic** (Claude brain) → console.anthropic.com
2. **OpenAI** (Whisper ears) → platform.openai.com
3. **Fish Audio** (Russian voice) → fish.audio
4. **Picovoice** (wake word) → picovoice.ai
5. **Apple Developer** account (~$99/yr) to put the app on his iPhone → developer.apple.com

---

## HOW TO CONTINUE ON THE MAC
1. Copy this whole `companion` folder to the Mac.
2. Install the **Claude desktop app** from **claude.ai/download** (NOT the App Store).
3. Open it, start a new chat/session in this folder.
4. Say: **"Read PLAN.md and continue building the companion, start with the backend."**
5. We build the brain + memory first, then the iPhone app.

Note: this chat does not copy itself to the Mac — this file is the handoff. Nothing is lost.

---

## TECHNICAL HANDOFF (for the AI/builder — skip if you're not coding)

**Architecture:** on-device iOS app ⇄ backend server ⇄ AI services + database.

- **App:** iOS, Swift/SwiftUI. Sideloaded (private family app, no App Store review).
  - Wake word: **Picovoice Porcupine** (on-device, custom Russian wake word).
  - Always-on listening only guaranteed while foreground; use **Guided Access** kiosk when docked.
  - On-the-go: **App Intents / Siri Shortcut** to launch hands-free + best-effort background-audio session.
  - UI is minimal: a face/animation + optional photos. No text input.
- **Backend:** **Python + FastAPI**. Holds all API keys, orchestrates the voice loop, owns memory + the proactive scheduler. Build and test this FIRST (works on any OS, incl. a browser mic test page).
  - **STT (ears):** OpenAI **Whisper** primary (best for elderly/noisy Russian). Optional **Deepgram** streaming for lower latency later.
  - **Brain:** **Claude Opus 4.8** (`claude-opus-4-8`) via Anthropic API. Holds personality + reads memory before each reply.
  - **TTS (mouth):** **Fish Audio** (open-weight, cheaper), warm Russian voice; ElevenLabs optional.
  - Target round-trip latency ~1–1.5s (fine for an elderly user).
- **Memory (Postgres + pgvector):**
  - *Facts table:* name, family tree, birthdays, meds, doctors, conditions, routine, preferences.
  - *Story memory (vectors):* each anecdote embedded for semantic recall months later.
  - Before every reply: load relevant facts + relevant past stories + recent mood/health notes → into Claude's context.
  - Also keep raw audio (cheap) so nothing is ever lost.
- **Proactive engine:** backend scheduler (cron) triggers the app to speak first — morning greeting, med/meal nudges, story recall, bedtime. Claude composes each from memory.
- **Guardrails:** never give medical advice ("let's call your doctor"); honest it's an AI; health data kept private; emergency escalation to family.
- **Reminiscence / life-review** is a deliberate feature (clinically supported for elderly depression), not filler.

**Build phases:**
1. Talking loop (wake word → Whisper → Claude → Fish Audio). Browser mic test page first.
2. Memory (Postgres + pgvector; facts + story recall).
3. Proactive/daily (scheduler, greetings, reminders, story recall).
4. Family & safety (family voice messages, "call my son", silence/health alerts).
5. Polish (photos on screen, mood/health tracking, doctor summary).
