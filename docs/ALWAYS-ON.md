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

### Honest tradeoffs on Mode B
- **One question → one answer** each time (not a continuous open mic; he re-says
  "Hey Siri, Bob" per turn).
- The reply will most likely be in **Siri's Russian voice, not Bob's warm
  ElevenLabs voice** — reliably playing our own audio over another foreground app
  from a background intent is not a supported iOS capability. We can *prototype*
  playing Bob's real voice there, but treat it as **uncertain until tested on the
  Mac**.
- Russian Siri quality/recognition applies in this mode.

### Not possible on iPhone
Our app itself listening in the background and answering over his movie in Bob's
voice, with no Siri involved. Only Siri crosses between apps.

### Net shape
Bob's **full warm voice** when he opens / docks it (Mode A); **quick
Siri-voiced answers** when he's mid-something-else (Mode B). Together these cover
both real scenarios (chatting while resting; quick questions during Telegram or a
movie).

**Build risk to retire early (on the Mac):** whether a background App Intent can
play ElevenLabs audio. If yes, Mode B gets Bob's voice too; if no, Mode B stays
Siri-voiced. Prototype this first before committing to Mode B's design.
