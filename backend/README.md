# Backend — the brain, ears, mouth & memory

Python + FastAPI. This is the part to build and test **first** — it runs on any
OS and you can test the whole voice loop in a browser before the iPhone app
exists.

## The talking loop (Phase 1)

```
🎙️ recorded audio  →  👂 Whisper (STT, ru)  →  🧠 Claude (reply, ru)  →  🗣️ ElevenLabs (TTS)  →  🔊 audio back
```

## Setup

**1. Get your keys** (see [../PLAN.md](../PLAN.md) → "GET THESE READY"):
Anthropic, OpenAI, ElevenLabs.

**2. Configure:**

```bash
cd backend
cp .env.example .env      # paste your keys into .env
```

**3. Run:**

```bash
./run.sh
```

That creates a virtual environment, installs dependencies, and starts the
server at **http://localhost:8000**. Open it, press **Говорить**, and speak.

<details>
<summary>Manual start (without run.sh)</summary>

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
</details>

## Endpoints

| Method | Path             | What it does |
| ------ | ---------------- | ------------ |
| `GET`  | `/`              | Browser mic test page |
| `GET`  | `/api/health`    | Which services are configured (no secrets) + memory counts |
| `POST` | `/api/talk`      | Full voice loop: audio in → `{transcript, reply, audio}` out |
| `POST` | `/api/say`       | Text in → `{reply, audio}` out (skips the ears — test brain + memory + mouth) |
| `POST` | `/api/proactive` | The companion **speaks first** — a warm good morning (`{kind, occasion?}`) |
| `GET`  | `/api/memory`    | What it currently remembers (facts, stories, follow-ups, mood) |

## Layout

```
app/
  config.py      # keys + settings from .env (the only place secrets live)
  companion.py   # the companion's Russian personality + guardrails  ← edit this to change who it is
  stt.py         # ears   — Whisper
  brain.py       # brain  — Claude (claude-opus-4-8): replies + proactive openers
  tts.py         # mouth  — ElevenLabs
  memory.py      # memory — facts, stories, health, mood, caring follow-ups + recall
  learn.py       # turns each conversation into memory (runs in the background)
  embeddings.py  # semantic recall (OpenAI embeddings + cosine)
  db.py          # SQLite storage (→ Postgres + pgvector later)
  occasions.py   # calendar of special dates (with origin-story hints)
  main.py        # FastAPI app: voice loop + proactive greeting
static/
  index.html     # browser mic test page
data/            # memory database + logs (git-ignored, never committed)
```

## Memory — what makes it feel like a real friend

After each conversation, the companion quietly **learns** (in the background, so
the voice stays fast) and remembers:

- **facts** — family, birthdays, his accident, routine, likes, contacts
- **stories** — anecdotes he shared, recalled later *by meaning* ("а помните, вы
  рассказывали про рыбалку…") via embeddings
- **health** — things he mentioned (remembered, never advised on)
- **mood** — a gentle read of how he seemed, tracked over days
- **follow-ups** — the caring part: things to check back on next time
  ("как ваше колено сегодня?"), so he feels genuinely held in mind

Before each reply it loads the relevant facts + semantically recalled stories +
open follow-ups + (sometimes, spaced out) a spontaneously resurfaced warm memory
+ his recent mood. The good-morning greeting (`/api/proactive`) weaves all of
this together.

**Storage:** SQLite now (zero setup — nothing to install), behind a small
interface so Phase 2 can move to **Postgres + pgvector** without touching the
rest of the app. For one person, in-Python cosine similarity is instant.

**Hand-seed what you know:** copy `data/facts.example.json` → `data/facts.json`
and fill in family, birthdays, home town, favorite songs, routine, and his
doctor/contact. It's imported into memory on startup (duplicates are skipped).

**Peek at its memory anytime:** `curl http://localhost:8000/api/memory`

## Testing the brain alone

No microphone needed — test the brain + voice with text:

```bash
curl -s -X POST http://localhost:8000/api/say \
  -H "Content-Type: application/json" \
  -d '{"text":"Здравствуй! Как тебя зовут?"}' | python3 -m json.tool
```
