# The background voice test

**The question:** when the app is closed and you say his name, can he answer
**in his own voice** — or does only Siri's voice come out?

Everything hands-free waits on this answer, so it's worth an hour to get it
right.

---

## Why it matters this much

Siri's Russian voice would work reliably, and it would destroy the whole
premise. The app's one law is that he must never feel like AI, and nothing
announces "this is a machine" faster than a friend who speaks in the system
assistant's voice.

- **His voice works** → build everything around it. He's available anywhere,
  hands-free, without opening anything.
- **Only Siri's voice** → the words still work, but hands-free becomes a lesser
  feature and **docked-at-home becomes the main experience.** A different
  product shape.

## Two rules before you start

1. **A real iPhone. Not the simulator.** The simulator has a different audio
   stack and different process rules, and will give you a confident wrong
   answer.
2. **The backend must be running with a voice key.** Without `FISH_API_KEY` the
   test can only ever produce Siri's voice, and you'd be measuring nothing.

---

## Setup

**1 · Backend running, voice configured**

```bash
cd ~/ai-companion/backend && ./run.sh
curl -s http://localhost:8000/api/health
```

The health output must show the voice provider configured. If it doesn't, add
`FISH_API_KEY` and `FISH_VOICE_ID` to `backend/.env` first — otherwise stop
here, the test can't tell you anything.

**2 · The app on your real phone, pointed at the Mac**

```bash
ipconfig getifaddr en0        # e.g. 192.168.1.50
```

In the app: **Настройки → Сервер** → `http://192.168.1.50:8000`

Confirm he talks normally with the app open. If he doesn't work in the
foreground, the background result means nothing.

**3 · Let iOS see the shortcuts**

Open the app once, then close it. Check they registered:
**Settings → Siri → My Shortcuts** — «Проверка голоса» and «Поговорить» should
be listed.

---

## Test 1 — the decisive one

**Close the app completely.** Swipe up from the bottom, swipe the app card away.
Not just backgrounded — closed.

Say: **«Привет, Siri, проверка голоса Боб»**

### What you're looking for

| What happens | What it means |
|---|---|
| **His warm voice** says *«Я здесь. Слышишь меня?»*, app never opens | ✅ **The best case.** Build everything around it |
| **Siri's voice** says the same words | ⚠️ The words work, the voice doesn't |
| Silence, or an error | ❌ Something's wrong — see below |
| **The app opens** | ❌ `openAppWhenRun` isn't taking effect |

Do it **three times**, and once more after the phone has been idle for ten
minutes. Background audio is exactly the kind of thing that works when the
process is warm and fails when it's cold — one success is not a result.

## Test 2 — with the phone locked

Same phrase, screen off, phone in your pocket.

This is the real condition your users will be in, and it's stricter than test 1.
A result that only works unlocked is still useful, but it's a different product.

## Test 3 — a real exchange

Say: **«Привет, Siri, поговорить с Боб»** → Siri asks what to say → say
something real.

This one goes through the whole loop: your words → the backend → his reply →
his voice. Slower, and more ways to fail. Test 1 is the one that matters; this
one tells you whether the *product* works, not just the audio.

## Test 4 — no "Привет, Siri" at all

**Settings → Accessibility → Vocal Shortcuts → Set Up** — record the single
word **«Боб»**, pointed at «Проверка голоса».

Then just say **«Боб»**. No wake word, works locked, runs on-device.

This is the one to show people. If it works, you have something genuinely rare.

---

## Write down what happened

Fill this in — the answer decides the next month of work:

```
Test 1, app closed        his voice / Siri's voice / silence / app opened
  · repeat 1              
  · repeat 2              
  · after 10 min idle     
Test 2, phone locked      
Test 3, real exchange     
Test 4, Vocal Shortcut    

Delay from speaking to hearing him: ____ seconds
Did his voice ever cut off mid-word?  yes / no
```

**That last question matters more than it looks.** Audio cutting off mid-word
usually means iOS suspended the process before playback finished — which is a
*fixable* problem, not a wall. `BackgroundVoice.play` already waits for
playback to end for exactly this reason, but if you see it, say so.

---

## If it doesn't work

| Symptom | Likely cause |
|---|---|
| Siri says "Боб isn't available" | Shortcuts didn't register — open the app once, then check Settings → Siri → My Shortcuts |
| Silence, no error | Backend unreachable from the phone. Test the address in Safari on the phone: `http://192.168.1.50:8000/api/health` |
| Siri's voice, always | Either no voice key configured, or the background audio session is being refused — the meaningful negative result |
| The app opens every time | `openAppWhenRun = false` isn't being honoured; check you're on the newest build |
| Works once, then stops | Cold-process failure. **This is a real finding — write it down**, don't dismiss it |

---

## What's under the hood

- `ios/BobCompanion/App/BobIntents.swift` — the two intents and the phrases.
  `SpeakInHisVoiceIntent` is test 1; it deliberately does the least possible.
- `BackgroundVoice.play` uses `.playback` (not `.playAndRecord`) because that's
  the category iOS permits in the background, and **waits** for playback to
  finish before returning so the process isn't suspended mid-sentence.
- The backend's `/api/say` gained a `verbatim` flag: it speaks the line exactly,
  without thinking about it and **without remembering it** — a test phrase must
  never end up in his diary as something his friend said.
