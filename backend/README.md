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
| `POST` | `/api/say`       | Text in → `{reply, audio}` out (**dev only** — he never types; test brain + memory + mouth) |
| `GET`  | `/api/memory`    | What it currently remembers (facts, stories, follow-ups, mood) |

> **Voice only, and he always speaks first.** The companion only responds — it
> never initiates. Special dates are mentioned reactively (woven into a reply),
> never announced.

## Layout

```
app/
  config.py      # keys + settings from .env (the only place secrets live)
  companion.py   # STABLE behavior: warmth, the "third way" honesty, safety guardrails
  persona.py     # WHO Bob is (name, home, story, cast, habits) — loaded from editable data
  stt.py         # ears   — Whisper
  brain.py       # brain  — Claude (claude-opus-4-8): produces the reply
  tts.py         # mouth  — ElevenLabs
  memory.py      # memory — facts, stories, health, mood, follow-ups (owner: elder | bob)
  learn.py       # turns each conversation into memory (runs in the background)
  embeddings.py  # semantic recall (OpenAI embeddings + cosine)
  db.py          # SQLite storage + migrations (→ Postgres + pgvector later)
  occasions.py   # calendar of special dates (with origin-story hints, mentioned reactively)
  main.py        # FastAPI app: the voice loop
tests/           # pytest suite (memory, persona, behavior, occasions, db, api)
conftest.py      # test fixtures (isolated temp DB per test)
static/
  index.html     # browser mic test page
data/            # memory DB + persona.json + facts.json (git-ignored, never committed)
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
+ his recent mood + today's occasion — all woven into a reply (Bob never speaks
first). Bob also keeps a small **self-memory** (`owner='bob'`) of what he's said
about his own life, so he stays consistent.

**Storage:** SQLite now (zero setup — nothing to install), behind a small
interface so Phase 2 can move to **Postgres + pgvector** without touching the
rest of the app. For one person, in-Python cosine similarity is instant.

**Hand-seed what you know:** copy `data/facts.example.json` → `data/facts.json`
and fill in family, birthdays, home town, favorite songs, routine, and his
doctor/contact. It's imported into memory on startup (duplicates are skipped).

**Peek at its memory anytime:** `curl http://localhost:8000/api/memory`

## Bob's persona — change his story anytime (no code)

Who Bob *is* — name, home, backstory, friends, habits, opinions, his current
life — lives in editable data, **not** in code. To set or change him:

```bash
cp data/persona.example.json data/persona.json   # then edit persona.json
```

Edit it whenever you like (after deciding the real story with your family) and
restart — no code changes. If the file is absent, a safe built-in default is
used. The *stable* parts (warmth, the honesty "third way", safety guardrails)
live in `app/companion.py`; the *changeable* character lives in the JSON.

Full character design: [../docs/BOB-PERSONA.md](../docs/BOB-PERSONA.md).

## Testing the brain alone

No microphone needed — test the brain + voice with text:

```bash
curl -s -X POST http://localhost:8000/api/say \
  -H "Content-Type: application/json" \
  -d '{"text":"Здравствуй! Как тебя зовут?"}' | python3 -m json.tool
```

## Running the tests

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
```

The suite covers memory (owner isolation, semantic recall, follow-up lifecycle),
the persona assembly, the behavior/guardrail rules (incl. that Bob never
confesses to being a machine), occasions, the DB migration, and every endpoint
(with the AI services mocked).
