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

| Method | Path          | What it does |
| ------ | ------------- | ------------ |
| `GET`  | `/`           | Browser mic test page |
| `GET`  | `/api/health` | Which services are configured (no secrets exposed) |
| `POST` | `/api/talk`   | Full voice loop: audio in → `{transcript, reply, audio}` out |
| `POST` | `/api/say`    | Text in → `{reply, audio}` out (skips the ears — test brain + mouth) |

## Layout

```
app/
  config.py      # keys + settings from .env (the only place secrets live)
  companion.py   # the companion's Russian personality + guardrails  ← edit this to change who it is
  stt.py         # ears  — Whisper
  brain.py       # brain — Claude (claude-opus-4-8)
  tts.py         # mouth — ElevenLabs
  memory.py      # Phase-1 memory (JSON); swaps to Postgres+pgvector in Phase 2
  main.py        # FastAPI app + the voice loop
static/
  index.html     # browser mic test page
data/            # per-user memory + logs (git-ignored, never committed)
```

## Memory now vs. later

Phase 1 keeps conversation history as JSON in `data/` so the loop already feels
continuous across restarts. You can also drop a `data/facts.json` (see
`data/facts.example.json`) with what you know about him — family, routine,
likes — and the companion will weave it in naturally.

Phase 2 replaces this with Postgres + pgvector for semantic story recall months
later, without changing the rest of the app (`memory.py` is a small interface).

## Testing the brain alone

No microphone needed — test the brain + voice with text:

```bash
curl -s -X POST http://localhost:8000/api/say \
  -H "Content-Type: application/json" \
  -d '{"text":"Здравствуй! Как тебя зовут?"}' | python3 -m json.tool
```
