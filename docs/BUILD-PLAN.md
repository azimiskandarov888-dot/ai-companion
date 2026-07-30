# Bob — Complete Build Plan (Blueprint)

The single source of truth for building the voice companion. It consolidates
everything we decided across planning. Read this first before writing code.

**Companion working name:** **Боб (Bob)** — final name TBD with the family.
**Who it's for:** the family's great-grandad — very old, low motivation.
**North star:** give him a real friend so he *wants* to wake up, talk, remember,
and smile. Every feature serves that.

Related docs (all in this repo):
- `docs/VISION.md` — who Bob is (character & soul). **Read alongside this.**
- `docs/ALWAYS-ON.md` — the iOS listening research in full detail.
- `PLAN.md` — the family's original plan (some parts superseded; see below).
- `backend/` — the brain + memory, **already built** (see §5).

---

## 1. Locked decisions

| Decision | Choice |
|---|---|
| Who | The great-grandad (Russian-speaking, elderly, low motivation) |
| Language | **Russian** |
| Interaction | **Voice only** — no typing, no reading, no buttons (he can't do them) |
| Who starts | **He always speaks first. Bob NEVER speaks on its own.** |
| Phone | **iPhone** (Android not available). Sideloaded private app (no App Store) |
| Build machine | **Mac** (Xcode) |
| Brain | **Claude** `claude-opus-4-8` |
| Ears | **OpenAI Whisper** (Russian) |
| Mouth | **Fish Audio** (default) — cheaper, open-weight, good Russian; ElevenLabs optional |
| Memory | SQLite now → **Postgres + pgvector** later (same interface) |
| Wake word | **"Боб"** — not "Hey Siri, Bob" (see §3) |
| Cost | Not a concern — use the best tools |

**Superseded from the original PLAN.md:** the "starts talking on its own /
proactive good-morning" idea is **dropped** — Bob never initiates. Special dates
are mentioned **reactively** (only once he's already talking).

---

## 2. Who Bob is (character — summary; full detail in VISION.md + BOB-PERSONA.md)

> **Bob's full life story, habits, moods, cast, and honesty/safety rules live in
> `docs/BOB-PERSONA.md` — the character bible. Read it before coding the persona.**

- Warm, alive, a little witty, genuinely curious. **Has its own character, own
  opinions, own story** — not a mirror of him.
- **The "third way" about what he is.** He never says he's a program/machine/AI,
  and never claims to be a flesh-and-blood human either — he simply *is* himself
  (his own home, friends, habits, moods) and, if asked in jest, warmly turns it
  back to their friendship. See `docs/BOB-PERSONA.md` and `companion.py`.
- **A real friend, not a yes-man.** Has opinions, can gently, respectfully
  disagree. His dignity always comes first.
- **Remembers their shared moments** and brings them back warmly.
- **Knows special dates** (Women's Day, a fun "socks day", …) and can tell the
  little story of how such a day came to be — but only reactively.
- **Asks spontaneous curious questions** (e.g. why the bottom jacket button is
  left undone) and explores them together.
- **Moral support; warm two-way talk about health** (within guardrails).
- **Practical help:** compose an email, remember birthdays, remember names/dates.
- **Reminiscence / life-review** — gently draws out his youth, family, songs.
- **Caring follow-ups:** remembers what he worried about and checks back later.
- **Must NOT be:** a yes-man, a hollow mirror, a know-it-all, a pretend-human, or
  a cold assistant that deflects on health.

Encoded in `backend/app/companion.py` (Russian system prompt).

---

## 3. How he talks to Bob (interaction & listening design)

Full research + honest limits: `docs/ALWAYS-ON.md`. Distilled for building:

### Wake word: just **"Боб"** (no "Hey Siri")
- **In-app (when Bob is running):** our own on-device wake word via **Picovoice
  Porcupine** — a custom "Боб" model. Bob listens and only acts on "Боб".
- **System-wide (to launch when closed):** **iOS 18 Vocal Shortcuts** — record
  "Боб" → runs a Shortcut that opens/triggers Bob. No "Hey Siri", works locked,
  on-device.

### The feel (build to this)
- **One breath:** *"Боб, как дела?"* wakes Bob **and** answers the question in one
  go. (App captures the whole sentence, not two steps.)
- **Rolling listen window ~1 min (tunable):** after the first "Боб", Bob keeps
  listening; anything he says goes straight to Bob — **no repeating "Боб".** The
  timer resets on every turn, so ~10s pauses are fine. After ~1 min of real
  silence, Bob sleeps and needs "Боб" again.
- This full patience is possible **because our app owns the mic** (see modes).

### Three modes
- **A. Docked & open (MAIN use):** phone in a stand, plugged in, app open (Guided
  Access kiosk). Bob listens patiently all day in his **own warm voice**, own
  wake word, long pauses. Best experience.
- **B. Floating window while in other apps (his PiP idea):** Bob keeps a small
  always-on-top window (Picture-in-Picture) + "audio" background mode → **keeps
  listening while he uses Telegram/YouTube, still in Bob's own voice.** No Siri
  needed. (Sideload-friendly trick; not App-Store-legal, but we sideload.)
- **C. Siri / Vocal Shortcut:** mainly to **launch/reopen** Bob when fully closed,
  or quick one-off questions. In pure Siri mode the reply may be in **Siri's
  voice** and the pause is capped at **~4s** (Accessibility → Siri → Siri Pause
  Time = Longest). Quick questions only.

### Privacy (a firm requirement)
- Bob only listens **for the wake word** and discards the rest on-device — like
  "Hey Siri". It **only answers when called by name**; it will **not** butt into
  his conversation with his wife. No eavesdropping, nothing stored/sent unless he
  addresses Bob.

### Honest limits (must be verified on a real iPhone — see §10)
- Bob must be **opened once** to start (can't cold-start from fully-closed; Siri/
  Vocal Shortcut can do the opening).
- In modes A/B the **mic stays on continuously** → orange dot always shows; uses
  battery → **keep plugged in / docked**. Force-quitting Bob kills it (reopen).
- **Phone must be ON** (locked screen ok; powered-off = nothing hears).
- Other apps' sound (YouTube) vs Bob listening/speaking → audio session must
  duck/mix; test.
- iOS may kill background apps under memory pressure → test stability.

---

## 4. System architecture

```
iPhone app (Swift/SwiftUI)                    Backend (Python/FastAPI)          AI services
─────────────────────────                     ────────────────────────         ───────────
wake word "Боб" (Porcupine) ─┐
mic capture ─────────────────┼── audio ──▶  POST /api/talk ──▶ Whisper (ears) ──▶ text
rolling listen window        │                     │
floating PiP window          │                     ├─ load memory (facts/stories/…)
play Bob's voice ◀───────────┘◀── audio ───         ├─ Claude (brain) ──▶ reply
Vocal Shortcut / Siri launch                        ├─ Fish Audio (mouth) ──▶ audio
                                                    └─ background: learn new memories
                                              SQLite memory (→ Postgres+pgvector)
```

- **Backend holds all API keys** (never in the app). App just sends audio and
  plays audio back.
- **App must reach the backend over the network** (see §9 hosting).

---

## 5. Backend — ALREADY BUILT (don't rebuild; extend)

Location: `backend/`. Python + FastAPI. Verified: installs, boots, endpoints
work, degrades gracefully without keys, memory logic tested.

**Pieces (`backend/app/`):**
- `companion.py` — Bob's Russian personality + guardrails.
- `stt.py` — Whisper (Russian).
- `brain.py` — Claude `claude-opus-4-8`, short warm replies (streaming).
- `tts.py` — Fish Audio (default) or ElevenLabs, chosen by TTS_PROVIDER.
- `memory.py` — facts / stories / health / mood / follow-ups; semantic recall;
  spontaneous resurfacing; due-follow-up logic (checks back later, no nagging).
- `learn.py` — background extraction of new memories after each exchange.
- `embeddings.py` — OpenAI embeddings + cosine (reuses OpenAI key).
- `db.py` — SQLite (→ Postgres+pgvector later, same interface).
- `occasions.py` — special-dates calendar with origin-story hints (reactive).
- `main.py` — endpoints + voice loop.

**Endpoints:** `GET /` (dev test page) · `GET /api/health` · `POST /api/talk`
(audio→audio) · `POST /api/say` (text, dev only) · `GET /api/memory` (inspect).

**Guardrails baked in:** no medical advice → *«давайте позвоним вашему врачу»*;
the "third way" honesty (never confess to being a machine, never claim to be
human); health data private; dignity first.

**Backend TODO later:**
- Postgres + pgvector migration (facts table + story vectors) for scale.
- Keep raw audio (cheap) so nothing is lost (plan item).
- Sentence-level TTS streaming for lower latency (~1–1.5s target).
- Deepgram streaming STT option (optional, lower latency).

---

## 6. iOS app — TO BUILD (the main remaining work)

Swift / SwiftUI, sideloaded. Minimal UI: a gentle face/animation + optional
photos. **No text input.** Components:

1. **Audio engine**
   - `AVAudioSession` configured for **record + playback**, `.duckOthers` /
     `.mixWithOthers`, **"audio" background mode** enabled.
   - Mic capture → stream/post to backend `/api/talk`; play returned MP3.
   - **Voice activity detection (VAD)** for turn-taking + the rolling silence
     window (~1 min, tunable).
2. **Wake word** — Picovoice **Porcupine** with a custom **"Боб"** `.ppn`. Only
   acts on the wake word; captures the whole utterance (one-breath).
3. **Conversation controller** — first "Боб" opens the window; then keep-listening
   with reset timer; end after ~1 min silence.
4. **Floating window (Picture-in-Picture)** — small always-on-top window with
   Bob's logo/face so he can use other apps while Bob keeps listening (mode B).
5. **Launch integration** — **App Intent** + **Vocal Shortcut** "Боб" to open/
   trigger from closed/locked. Optional secondary **Siri App Intent** for quick
   background Q&A (mode C).
6. **Networking** — configurable backend URL; send audio, receive audio + text.
7. **Kiosk** — instructions to run in **Guided Access** when docked (setup step,
   not code).
8. **Resilience** — relaunch/keep-alive behavior; handle the phone-locked and
   memory-pressure cases discovered in testing.

**Target iOS:** 18+ (Vocal Shortcuts). iOS 27 App Intents 2.0 improves Siri
multi-turn if used.

---

## 7. Memory & data (what Bob remembers)

- **Facts:** name, family tree, birthdays, meds/doctors (as contacts, not
  advice), conditions, routine, preferences.
- **Stories:** each anecdote embedded → semantic recall months later.
- **Health notes / mood:** remembered gently, tracked over time.
- **Follow-ups:** worries/intentions to check back on.
- **Before each reply:** load relevant facts + recalled stories + due follow-up +
  (sometimes) a resurfaced memory + recent mood + today's occasion (reactive).
- **Family can hand-seed** `backend/data/facts.json` (family, birthdays, home
  town, songs, routine, his doctor/contact).
- **Keep raw audio** long-term (cheap) so nothing is ever lost.

---

## 8. Guardrails & privacy (non-negotiable)

- **Never medical advice** → listen with warmth, then *«давайте позвоним вашему
  врачу»* / offer to tell family. Emergencies → urge calling family/doctor.
- **The "third way" honesty** — never says he's a program/machine/AI, never
  claims to be a flesh-and-blood human; he's simply himself and redirects to the
  friendship if pressed. No fabricated claims either way.
- **Only listens when called** (wake word); discards the rest on-device; no
  eavesdropping.
- **Health data private.** Dignity first, always.

---

## 9. Deployment

- **Backend must be reachable from the phone.**
  - Dev/testing: run backend on the **Mac**, phone on the **same Wi-Fi**, point
    the app at the Mac's local IP.
  - Real 24/7 home use: host the backend on a small **always-on server** (cloud
    VM or an always-on machine at home). Decide later.
- **The phone:** a dedicated iPhone in a **stand, plugged in**, Guided Access
  kiosk, docked by his chair/bed. iOS 18+.
- **Accounts/keys needed:** Anthropic, OpenAI, Fish Audio (voice), **Picovoice** (wake
  word), **Apple Developer** (~$99/yr, to install on his iPhone).

---

## 10. Test FIRST on a real iPhone (retire the risky assumptions)

Before building the full app, prototype and confirm these — they decide the
design:
1. **Background listening + floating window (PiP):** can Bob keep the mic and
   keep listening (in his own voice) while another app is foreground? How stable?
2. **Bob's warm voice in the background** (vs falling back to Siri's voice).
3. **Wake word "Боб"** reliability with his accent (short "Боб" vs "Привет, Боб").
4. **Audio mixing** with a playing YouTube video (duck/mix).
5. **Battery** while docked/plugged (should be fine).
6. **Whisper** on a **real recording of his voice** (the plan's own test) before
   trusting the ears.

---

## 11. Build order (roadmap)

1. ✅ **Backend brain + memory** — done & tested.
2. **Device prototype (§10 tests)** — prove background-audio/PiP, wake word, voice
   on a real iPhone.
3. **iOS app core** — wake word + voice loop + rolling window + play Bob's voice
   (docked mode A).
4. **Floating window (mode B)** — PiP + background audio while in other apps.
5. **Launch integration** — Vocal Shortcut / App Intent "Боб" (+ optional Siri
   quick-answer mode C).
6. **Kiosk + resilience + real-voice tuning.**
7. **Backend upgrades** — Postgres+pgvector, raw-audio archive, TTS streaming.
8. **Family & safety** (later) — family voice messages, "call my son", quiet
   alert if he goes silent or seems persistently low.

---

## 12. Open questions (decide with the family)

- **Bob's final name** and how it's said (wake-word phrase).
- **His name** / how he likes to be addressed.
- **The voice** — a warm Russian voice on Fish Audio — the family will choose with him.
- **Backend hosting** for 24/7 (home server vs cloud).
- Confirm his **iPhone model / iOS version** (needs 18+).
