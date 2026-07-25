# Adding the "Боб" wake word (the next layer)

The core app listens to whatever is said and answers. That's perfect for testing
and for a dedicated docked device that only has Bob on it. But the design goal is
that **Bob only answers when called by name** — so he never butts into the elder's
conversation with his wife, and so the phone isn't sending every stray sentence to
the backend. That's what a wake word gives us.

This is written down so it's ready to build once the core loop is proven on a real
iPhone. It is **not** wired in yet — on purpose, because wake-word accuracy has to
be tuned on *his* voice and *his* room (see `docs/ALWAYS-ON.md`).

## Two pieces (from `docs/BUILD-PLAN.md` §3)

1. **In-app wake word** — while Bob is open and docked, listen on-device for the
   word **"Боб"** and only then start capturing an utterance. Everything else is
   discarded on the phone and never sent anywhere.
2. **System-wide launch** — **iOS 18 Vocal Shortcuts** (Settings → Accessibility →
   Vocal Shortcuts): record "Боб" → run a Shortcut that opens Bob. This lets him
   say "Боб" to wake the app when it's closed or the phone is locked, with no "Hey
   Siri" first. No code — it's a setup step on the device.

## In-app wake word: Picovoice Porcupine

Porcupine does on-device wake-word detection (nothing leaves the phone) and lets
you train a custom **"Боб"** word.

**Steps when we build it:**

1. Make a free account at the [Picovoice Console](https://console.picovoice.ai),
   train a custom keyword **"Боб"** (Russian), and download:
   - the `.ppn` keyword file (his word), and
   - your **AccessKey**.
2. Add the **Porcupine iOS** package in Xcode
   (Swift Package Manager: `https://github.com/Picovoice/porcupine`).
3. Add a `WakeWordManager` alongside the audio code:
   - On start (when docked), run `PorcupineManager` listening for the `.ppn`.
   - On detection, call into `ConversationController` to begin capturing the
     utterance — the same `SpeechRecorder` path we already have.
4. Change the loop's shape slightly: **sleep** after ~1 minute of real silence and
   wait for "Боб" again, instead of listening continuously (the rolling-window
   design in `docs/ALWAYS-ON.md`).

The one-breath goal — *"Боб, как дела?"* waking Bob **and** answering in one
sentence — works because Porcupine detects "Боб" at the start of the buffer while
`SpeechRecorder` captures the whole utterance; the backend just gets the sentence.

## Keep it honest

- The `.ppn` and AccessKey are Picovoice assets — they don't ship in this repo.
- Recognition should be trained/tuned on **his** voice; a slightly longer phrase
  (e.g. *"Привет, Боб"*) cuts false triggers. Tune on the real device.
- Battery: always-listening wants the phone **plugged in / docked** — already the
  plan.
