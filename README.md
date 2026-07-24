# Voice Companion 👴🎙️

A warm, talking friend for my great-grandad — in **Russian**, **voice only**.
He speaks, it listens, and it speaks back in a gentle Russian voice. It
remembers his stories and can start a conversation on its own.

> **Complete build blueprint** (start here): **[docs/BUILD-PLAN.md](./docs/BUILD-PLAN.md)**
> **Who Bob is** (his life, story & soul): **[docs/BOB-PERSONA.md](./docs/BOB-PERSONA.md)**
> **How the companion behaves** (character & guardrails): **[docs/VISION.md](./docs/VISION.md)**
> **Always-on listening design** (iOS research): **[docs/ALWAYS-ON.md](./docs/ALWAYS-ON.md)**
> **The family's original plan:** **[PLAN.md](./PLAN.md)**

## The parts (like a person)

| Part | Job | Powered by |
| ---- | --- | ---------- |
| 🧠 **Brain** | thinks, remembers, replies warmly | **Claude** (`claude-opus-4-8`) |
| 👂 **Ears** | hears messy, elderly Russian | **Whisper** (OpenAI) |
| 🗣️ **Mouth** | warm Russian voice | **ElevenLabs** |
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
cp .env.example .env        # then paste in your Anthropic, OpenAI, ElevenLabs keys
./run.sh                    # sets up a venv, installs deps, starts the server
```

Open **http://localhost:8000**, press the button, and speak Russian. See
[backend/README.md](./backend/README.md) for details.

## Build phases (from PLAN.md)

1. ✅ **Talking loop** — Whisper → Claude → ElevenLabs (browser test page)
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
врачу"), always **honest that it's an AI**, health data kept private.
