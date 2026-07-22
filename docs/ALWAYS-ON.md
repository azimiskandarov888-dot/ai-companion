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
