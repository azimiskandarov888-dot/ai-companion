# Bob — the iPhone app (docked voice companion)

This is the app your great-grandad actually talks to. It runs on an iPhone in a
stand by his chair, plugged in, this one screen always open. He speaks; Bob
answers in his warm voice. **No typing, no reading, no buttons.**

> **You need a Mac with Xcode to build this.** It cannot be built on Windows or
> Linux. That's why this part waited until you were on your MacBook.

## What this app does (and doesn't, yet)

**Built now — the core loop (mode A, "docked", the main way he'll use it):**

```
👂 records what he says  →  ☁️ sends it to the backend  →  🗣️ plays Bob's reply  →  listens again
```

- A calm full-screen face that breathes and changes color as it listens / thinks / speaks.
- Voice-activity detection: it starts recording when he talks and stops when he
  pauses (tunable — he's old and slow, so pauses are generous).
- Sends his voice to the backend, plays Bob's reply, then listens again — a real
  back-and-forth, hands-free.
- A hidden settings screen (long-press the face) to set the backend address.

**Next layers (designed, not yet coded — see below and `docs/BUILD-PLAN.md`):**

- **Wake word "Боб"** (so Bob only answers when called, and ignores the rest of
  the room) — see [`docs/WAKE-WORD.md`](docs/WAKE-WORD.md).
- **Floating window** so Bob keeps listening while he uses other apps.
- **"Say Боб to launch"** from a locked phone (iOS Vocal Shortcut).

These three need a **real iPhone to test** — our own research (`docs/ALWAYS-ON.md`)
says background audio, the floating window, and wake-word accuracy must be proven
on the device, not guessed. The core loop above is the honest, testable
foundation everything else builds on.

---

## Before you build

1. **A Mac with Xcode** (free from the Mac App Store). iOS **18+** on his iPhone.
2. **The backend running** somewhere the phone can reach. For testing, run it on
   the same Mac (`cd backend && ./run.sh`) and note the Mac's Wi-Fi IP address
   (System Settings → Wi-Fi → Details → IP Address, e.g. `192.168.1.50`).
3. **An Apple Developer account** ($99/year) to install the app on his real
   iPhone. (A free Apple ID works for 7-day test builds; the paid account makes
   it permanent.)

---

## Make the Xcode project — two ways

### Option A — by hand in Xcode (no extra tools)

1. Open Xcode → **File → New → Project… → iOS → App**.
2. Product Name: **BobCompanion**. Interface: **SwiftUI**. Language: **Swift**.
   Set the Deployment Target to **iOS 18.0**.
3. Delete the auto-created `ContentView.swift` and the sample `App` file.
4. Drag the `BobCompanion/` folder from here into the project navigator
   (**Copy items if needed**, **Create groups**). That brings in `App/`,
   `Config/`, `Audio/`, `Net/`, `Conversation/`, `UI/`.
5. In the target's **Info** tab, merge in the keys from `BobCompanion/App/Info.plist`
   (microphone + local-network usage strings, Background Modes → **Audio**, and
   the dev ATS keys). Or set the target's Info.plist file to that one.
6. In **Signing & Capabilities**, pick your Team, and add the **Background Modes**
   capability with **Audio, AirPlay, and Picture in Picture** ticked.

### Option B — XcodeGen (one command)

```bash
brew install xcodegen      # once
cd ios
xcodegen generate          # creates BobCompanion.xcodeproj from project.yml
open BobCompanion.xcodeproj
```

Then set your Development Team in **Signing & Capabilities** (or uncomment
`DEVELOPMENT_TEAM` in `project.yml`).

---

## Run it on his iPhone

1. Plug the iPhone into the Mac, unlock it, and trust the computer.
2. In Xcode's device menu (top bar), pick his iPhone.
3. Press **▶︎ Run**. First time: on the phone, **Settings → General → VPN & Device
   Management** → trust your developer certificate.
4. When the app opens, **long-press the face** → set the backend address to your
   Mac's IP (e.g. `http://192.168.1.50:8000`) → **Готово**.
5. Say something in Russian. Watch the face turn green (listening) → amber
   (thinking) → blue (speaking), and hear Bob answer.

> While testing, the screen shows what Bob heard and said (DEBUG only) so you can
> follow along. That text disappears in a real (Release) build — he never sees it.

---

## Make it a real "kiosk" by his chair

Once it works:

- Put the iPhone in a **stand, plugged in**, near him.
- **Settings → Accessibility → Guided Access → On.** Open Bob, then triple-click
  the side button to lock the phone to just this app. Now it can't be closed by
  accident and stays listening all day.
- Turn on **Settings → Display & Brightness → Auto-Lock → Never** while docked.

---

## How it fits together

```
This app (Swift/SwiftUI)            Backend (Python, already built)      Paid AI services
────────────────────────            ──────────────────────────────      ────────────────
records his voice ───── audio ────▶ POST /api/talk ─▶ Whisper  (ears) ─▶ text
plays Bob's reply ◀──── audio ─────           │        Claude  (brain) ─▶ reply (as Bob)
                                              └─────── ElevenLabs (mouth) ─▶ voice
```

- **The app holds no secrets.** Every API key lives on the backend
  (`backend/app/config.py`). The phone just sends audio and plays audio.
- Bob's personality is **not** set inside any AI's website — it lives in our
  backend (`backend/data/persona.json`) and is sent to Claude on every reply. See
  the backend README and `docs/BOB-PERSONA.md`.

## File map

```
ios/
  project.yml                      # optional XcodeGen spec
  BobCompanion/
    App/
      BobCompanionApp.swift        # entry point; starts/stops the loop with the screen
      Info.plist                   # mic + background-audio + local-network permissions
    Config/AppConfig.swift         # backend address + conversation "feel" (no secrets)
    Audio/
      AudioSessionManager.swift    # record+playback session, mic permission
      SpeechRecorder.swift         # records one utterance, detects when he's done
      AudioPlayer.swift            # plays Bob's returned voice
    Net/BackendClient.swift        # POST /api/talk (multipart), decodes reply+audio
    Conversation/
      ConversationController.swift  # the listen → think → speak loop
    UI/
      CompanionView.swift          # the one screen (a face, no buttons)
      BreathingFace.swift          # the living presence
      SettingsView.swift           # hidden setup (backend address)
  docs/WAKE-WORD.md                # how to add the "Боб" wake word next
```
