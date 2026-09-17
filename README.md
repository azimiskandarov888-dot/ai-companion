# Voice Companion 👴🎙️

A warm, talking friend for lonely people — of **any age**, in **Russian**,
**voice only**. The person speaks, it listens, and it speaks back in a gentle
voice. It remembers their stories, notices when something has changed, and has
a life of its own to talk about.

It does **not** start conversations. There is no scheduler, no push and no
outbound call anywhere in the codebase, and he is forbidden to promise anything
that would need one — a friend who says «я тебе завтра напомню» and cannot is
worse than no friend.

> **START HERE — everything a new session needs:** **[docs/HANDOVER.md](./docs/HANDOVER.md)**
> **Complete build blueprint:** **[docs/BUILD-PLAN.md](./docs/BUILD-PLAN.md)**
> **Who Bob is** (his life, story & soul): **[docs/BOB-PERSONA.md](./docs/BOB-PERSONA.md)**
> **How the companion behaves** (character & guardrails): **[docs/VISION.md](./docs/VISION.md)**
> **Always-on listening design** (iOS research): **[docs/ALWAYS-ON.md](./docs/ALWAYS-ON.md)**
> **How a friend is made** (the soul): **[docs/SOUL.md](./docs/SOUL.md)**
> **Many people, one server** (identity & privacy): **[docs/MANY-PEOPLE.md](./docs/MANY-PEOPLE.md)**
> **His voice** (which one, what Russian really costs, why he answers faster): **[docs/HIS-VOICE.md](./docs/HIS-VOICE.md)**
> **The family's original plan:** **[PLAN.md](./PLAN.md)**

## The parts (like a person)

| Part | Job | Powered by |
| ---- | --- | ---------- |
| 🧠 **Voice** | the companion speaking — fast, because somebody is waiting | **Claude Haiku 4.5** |
| 🧩 **Brain** | web search, intake, distilling memory, his week | **Claude Sonnet 5** |
| ✍️ **Reader & writer** | reads the person, invents the companion | **Claude Opus 5** |
| 🚨 **Watchman** | is this person in danger right now | **Claude Haiku 4.5**, outside the character |
| 👂 **Ears** | hears messy, accented speech | **Whisper** (OpenAI) — due for replacement |
| 🗣️ **Mouth** | warm Russian voice | **Fish Audio** (default; ElevenLabs optional) |
| 📔 **Memory** | remembers stories, family, routine | file-based now → Postgres + pgvector later |

## Where we are

We build the **backend first** (works on any computer, testable in a browser),
then the iPhone app on the Mac. This repo currently contains **Phase 1: the
talking loop** — record his voice in the browser, hear the companion reply.

```
backend/   ← Python + FastAPI: the brain, ears, mouth, and a browser mic test page
ios/       ← (later) the SwiftUI iPhone app
PLAN.md    ← the plan (source of truth)
```

## Try it (once you have API keys)

```bash
cd backend
cp .env.example .env        # then paste in your Anthropic, OpenAI, and Fish Audio keys
./run.sh                    # sets up a venv, installs deps, starts the server
```

Open **http://localhost:8000**, press the button, and speak Russian. See
[backend/README.md](./backend/README.md) for details.

## Build phases (from PLAN.md)

1. ✅ **Talking loop** — Whisper → Claude → Fish Audio (browser test page)
2. ✅ **Memory** — facts + semantic story recall + spontaneous resurfacing +
   caring follow-ups + mood (SQLite now → Postgres + pgvector later)
3. 🔨 **iPhone app** ← *next* — voice only, launched hands-free by voice (Siri),
   always-listening kiosk when docked at home. **He always speaks first; the
   companion only ever responds — it never initiates.**
4. **Family & safety** — family voice messages, "call my son", quiet alerts if he
   goes silent or seems persistently low
5. **Polish** — mood/health tracking over time, a simple doctor summary

> **Interaction model (locked):** voice only — no typing, no reading, no buttons.
> He talks; it answers. See [docs/VISION.md](./docs/VISION.md).

---

Guardrails, always on: **never medical advice** ("давайте позвоним вашему
врачу"), **never a promise about the real world** (he cannot visit, ring first
or remind anybody of anything), health data kept private.

**What he is, and where that is said.** He never tells anybody he is an AI —
he does not confess it, hint at it, or argue about it. That is the product,
and the rules are in `backend/app/companion.py`. The truth is told in the app
instead, in plain words, one tap away in Settings → «О приложении»
(`ios/BobCompanion/Design/Strings.swift`, `aboutBody`): that he is not a living
person, that his life is invented, that the listening and the memory are real,
and what he cannot do. See [docs/VISION.md](./docs/VISION.md) for why it is
split that way.
