# Always-On Listening — the platform reality (READ THIS)

**The goal:** he speaks to the phone anytime, and the companion answers — with
**nothing to open, nothing to press, nothing to read.** Always available, like
Siri.

## The hard truth about iPhone

**Apple does not let any third-party app listen always, system-wide, when the
app is closed.** That privilege is reserved for Siri alone. A normal iOS app
loses microphone access the moment it's backgrounded or the phone is locked —
iOS suspends it. Even a privately sideloaded app (no App Store review) cannot
beat this; the OS still suspends background apps and cuts the mic.

> PLAN.md already flagged this: *"An iPhone cannot listen when the app is closed —
> only Siri is allowed to do that."*

So: **true "Siri-like, phone-closed, always-on" is not possible for our app on
iPhone.** We should not promise it or build toward it.

## How we actually deliver the experience ("just talk, it answers")

### 1. At home — the main use — a docked "kiosk" device
A dedicated phone/tablet, plugged in, in a stand by his chair or bed, with the
app **always open and pinned to just that one app** (iOS **Guided Access** /
Android screen-pinning or a kiosk launcher). Because the app stays foregrounded,
it **listens all day** — he just speaks, it answers. No opening, no buttons,
nothing to touch. Set up once; it stays on.

This **fully meets the requirement.** The only tradeoff: it's a dedicated,
always-on device sitting with him.

### 2. Away from home (iPhone) — Siri launch
The only Apple-allowed hands-free entry when the app isn't open is a Siri phrase:
*«Привет, Siri… [companion]»*, which launches straight into the conversation.
One Siri phrase, then he just talks.

## Platform choice (the decision that shapes the build)

| | iPhone (plan's locked choice) | Dedicated Android device |
|---|---|---|
| Always-on, no touching | ✅ **only** via docked Guided Access kiosk | ✅ **native** — foreground service, auto-start on boot, can even be the default assistant |
| Robustness | App must stay pinned/foregrounded; re-pin after a reboot | More robust for this exact use-case |
| On-the-go hands-free | «Привет, Siri, [companion]» to launch | Custom wake word possible |
| Build machine | Mac (Xcode) — already have it | Any OS (Android Studio) |

**Recommendation:** a dedicated, always-docked device by him is the real answer
either way. If the seamless always-on-with-no-touching experience is the top
priority (it is), a **dedicated Android phone** is the most robust fit. If we
stay on iPhone, the **docked Guided Access kiosk** is the way, and it does work.

Either way, the backend we've already built (brain + memory, voice in → voice
out) is the same and is ready.

---

## The Siri route (refined plan — since Android is out)

Android isn't an option, so **Siri is the way in** — it's the only thing on
iPhone that can hear him across apps. Good instinct. Here's what it really allows.

### Wake word: it must be "Hey Siri, Bob" (not "Hey Bob")
Apple reserves the wake word for Siri; we can't register "Bob" as a global
trigger. We name the Shortcut / App Intent **"Bob"**, so he says
*«Эй, Siri, Боб…»* — one "Hey Siri" in front, then he talks. That's the closest
iOS permits.

### Two modes

**Mode A — open & talk (full warm Bob voice).**
*«Эй Siri, Боб»* launches the app; then a continuous, flowing conversation in
Bob's warm ElevenLabs Russian voice, with full memory. Best when he's giving it
attention (resting, or docked in a stand). The rich experience.

**Mode B — quick answer *without leaving* his current app (Telegram, a movie).**
*«Эй Siri, Боб, что это за машина?»* runs a Siri **App Intent** that answers
**without opening the app**; Siri speaks the reply as an overlay and he stays in
Telegram / the film.

### What research confirms (as of 2026)
- Siri **can trigger the app to run in the background without opening it**
  (App Intent with `openAppWhenRun = false`, "supports background execution"). ✓
- **Background audio is a permitted task**, so the app *can* speak while in the
  background. ✓ — but starting audio playback specifically *from a
  background-launched intent* has known reliability quirks; **must test on a real
  device.**
- **iOS 27 App Intents 2.0 supports multi-turn conversation** — Siri can keep a
  back-and-forth going with the app in the background, not just one-shot. ✓

### Honest catches (settle these on the Mac + a real iPhone)
- He must say **"Hey Siri" first** — Apple reserves the wake word; "Hey Bob"
  alone is impossible.
- **Voice is the open question.** The reliable answer speaks in **Siri's Russian
  voice.** Getting **Bob's warm ElevenLabs voice** to play from a background
  intent is *possible in principle* (background audio is allowed) but finicky —
  prove it on a real device before relying on it.
- The **phone must be on.** Locked screen = fine; fully powered-off = nothing
  hears (not even Siri).
- Locked-phone background-intent behavior has documented edge cases — test it.
- Siri is always the "ear"; the app never listens on its own. (Exactly the plan.)

### Net shape
Siri wakes Bob → Bob **runs and speaks in the background**, no app on screen, and
(on iOS 27) can hold a back-and-forth. The one thing to settle by testing is
**whose voice** the background answers use — Bob's warm voice (hoped) vs Siri's
(the sure thing).

---

## The wake word: can it be just "Bob" (not "Hey Siri, Bob")?

**Yes — this is the good news.** "Hey Siri, Bob" was only the most basic option.

### Two ways to say just "Боб"

1. **iOS 18 "Vocal Shortcuts"** (Settings → Accessibility → Vocal Shortcuts).
   Record a custom word in his own voice (e.g. **"Боб"**) → it runs a Shortcut →
   triggers Bob. **No "Hey Siri" first. Works even when the phone is locked.**
   Runs **on-device.** This is the system-wide way to drop "Hey Siri".
2. **Our own wake word when the app is open** (Picovoice Porcupine, on-device):
   while the app runs (docked kiosk), it listens for **"Боб"** itself. He just
   says *"Боб, как дела?"* and Bob answers — no Siri at all.

### Privacy (his concern) — it does NOT listen to everything
None of these record or eavesdrop. Wake-word tech (Siri / Vocal Shortcuts /
Porcupine) only listens *for the trigger word* on-device and **discards the
rest** — exactly like "Hey Siri". So Bob answers **only when called by name**;
it will **not** butt into his conversation with his wife.

### Honest catches
- **Battery:** always-listening uses battery → keep the phone plugged in / docked
  (already the plan). Apple suggests turning Vocal Shortcuts off when unused.
- **iOS 18+** for Vocal Shortcuts.
- "Боб" is a *trigger*. Smoothest full conversation: **"Боб" → app opens → talk
  freely** in Bob's warm voice, continuously, no Siri. A stay-inside-Telegram
  fully-background chat is prototype-able via the Shortcuts app but fiddlier.
- Recognition trains on **his** voice (good for his accent); a slightly longer,
  distinct phrase (e.g. *"Привет, Боб"*) reduces false triggers.

### Cleanest setup (combines everything)
- **Docked at home (main use):** app open, listening for its own wake word "Боб"
  → *"Боб, …"* → warm-voice conversation, continuous, no Siri, ignores everything
  that isn't addressed to "Боб".
- **Locked / inside another app:** Vocal Shortcut "Боб" → triggers Bob, no
  "Hey Siri".

---

## Conversation flow (how it should FEEL)

His two rules: (1) say the name and the message **together**; (2) **don't repeat
the name every sentence** — a generous pause is okay (he's old and slow).

In the **docked / app-open** mode we control the microphone, so all of this is
ours to build exactly as he wants:

- **One breath:** *"Боб, как дела?"* → the app hears the whole sentence, wakes on
  "Боб", **and answers the question.** Not two steps.
- **Rolling listen window (~1 min, tunable):** after that, the app keeps
  listening. Whatever he says goes straight to Bob — **no "Боб" needed.** Every
  time he *or* Bob speaks, the 1-minute timer resets, so ~10-second pauses are
  fine. Only after ~1 minute of real silence does it sleep and need "Боб" again.

**Works like this:**
> «Боб, доброе утро.» — «Доброе утро! Хороший денёк, правда?» — «да, а ты как?»
> — «Хорошо, а вы?» — «прекрасно…» *(пауза 10 сек)* «а как прошёл твой вчерашний
> день?»  ← no "Боб" after the first one.

In the **locked / other-app (Siri)** mode Siri owns the mic and its window is
only seconds, so there he re-triggers more often and the one-breath capture is
less clean. **The smooth flowing version lives in the docked setup** — which is
the main way he'll use it anyway.
