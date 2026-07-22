# Voice Companion 👴🎙️

A warm, talking friend for my great-grandad — in **Russian**, **voice only**.
He speaks, it listens, and it speaks back in a gentle Russian voice. It
remembers his stories and can start a conversation on its own.

> **Who the companion is** (its soul & character): **[docs/VISION.md](./docs/VISION.md)**
> **Decisions, architecture, roadmap:** **[PLAN.md](./PLAN.md)**

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

1. ✅ **Talking loop** — wake word → Whisper → Claude → ElevenLabs (browser test page first) ← *we are here*
2. **Memory** — Postgres + pgvector (facts + story recall)
3. **Proactive/daily** — greetings, reminders, story recall
4. **Family & safety** — voice messages, "call my son", health alerts
5. **Polish** — photos on screen, mood/health tracking, doctor summary

---

Guardrails, always on: **never medical advice** ("давайте позвоним вашему
врачу"), always **honest that it's an AI**, health data kept private.
