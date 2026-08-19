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
Bob's warm Russian voice, with full memory. Best when he's giving it
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
  voice.** Getting **Bob's warm voice** to play from a background
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

### How long can the pause be? (researched)
- **Docked / app-open (our mic):** anything we want — **30s, 60s, more.** We set
  the rolling window in our own code. This is where patient, slow, pause-filled
  conversation lives.
- **Locked / other-app (Siri's mic):** Apple's only lever is
  Settings → Accessibility → Siri → **Siri Pause Time**: Default ≈2s, Longer ≈3s,
  **Longest ≈4s**. So the max is ~**4 seconds** — there is **no way** to reach 30s
  or a minute in Siri mode. Set it to Longest so Siri doesn't cut him off
  mid-sentence, but this mode stays for **quick questions**, not slow chats.

---

## The floating-window idea (his PiP idea — a real upgrade + a correction)

His idea: like YouTube's little floating window that keeps playing after you
leave the app — run Bob as a small always-on-top window that keeps listening
while he uses other apps.

**A version of this genuinely works — and it beats the Siri path.** It also
**corrects** an earlier oversimplification ("in the background only Siri can
hear"): that's only true when Bob is *fully closed*. If Bob is **already running
and keeps an audio session alive**, it can keep listening in the background.

### How (researched)
- iOS lets an app **keep recording (microphone) in the background** if it started
  the mic **in the foreground** and has the **"audio" background mode**. It then
  keeps listening even after he switches to Telegram / YouTube.
- **Picture-in-Picture (PiP)** keeps the app alive with a small visible window
  (the mini-screen/logo he pictured). PiP is officially for video, so using it
  for a companion is a *trick* — fine for our **sideloaded private app** (no App
  Store review).
- Result: open Bob once → it keeps listening in its **own** logic (wake word
  "Боб", 1-minute window, Bob's **warm voice**) → he can use other apps with
  Bob's little window on top. Siri no longer needed while another app is open.

### Honest catches (must test on a real iPhone)
- Bob must be **opened once** to start the mic (can't cold-start from fully
  closed). After that it persists. Reopen if the phone reboots or he force-quits
  it from the app switcher.
- The **mic stays on continuously** (orange dot always shows; uses battery) →
  keep it **plugged in / docked**. It can't sleep-then-wake the mic in the
  background.
- **Other apps' sound** (a YouTube video) vs Bob listening/speaking needs careful
  audio handling (duck/mix) — testable.
- iOS may kill background apps under memory pressure → verify stability on the
  real phone.

### Net
**Yes — Bob can float in a small window and keep listening while he uses other
apps, in his own warm voice.** Conditions: keep it plugged in/docked, and open
it once. This is the **best answer yet** for "use Bob during Telegram or a
movie" — and it leans on our own app, not Siri's limits.

---

## Tapping something WITHOUT opening the app — what's actually possible

Asked directly, and worth writing down because the answer is a hard platform
limit rather than a design choice.

### The wall

**iOS will not let an app start recording while it is in the background.** The
system refuses it outright:

> Client is in the background and doesn't have the entitlement to start
> recording in the background.

There is no entitlement a normal app can request for this. It is not about
sideloading, provisioning, or App Store review — the OS says no.

Note the asymmetry, because it decides everything below:

| | in the background |
|---|---|
| **Speaking** | ✅ allowed (`audio` background mode) — this is what the two test intents exercise |
| **Listening** | ❌ refused, always |

So no widget, control, button or sticker can start a conversation *without*
the app coming forward. What they CAN do is bring it forward already
listening, so there is no hunting for an icon and no second tap.

### The surfaces, best first for an old pair of hands

All of them run a Shortcut, and the Shortcut runs `StartTalkingIntent`
(BobIntents.swift), which opens the app with him already switched on.

1. **Back Tap** — double-tap the BACK of the phone. Nothing to find, nothing
   to aim at, works through a case, on any iPhone 8 or newer.
   *Настройки → Универсальный доступ → Касание → Касание задней панели.*
   **This is the one to set up first.**
2. **The Action button** (iPhone 15 Pro and later) — one physical press.
   *Настройки → Кнопка «Действие».*
3. **An NFC sticker** on the table beside his chair — touch the phone to it.
   Set up in the Shortcuts app under Автоматизация. Lovely for a docked
   setup: the "button" can be a coaster.
4. **Control Centre, and the Lock Screen** — see below. Reachable without
   unlocking the phone.
5. **A Home Screen widget** — a far bigger target than an app icon.

### Control Centre and the Lock Screen, in detail

These are the two that need explaining, because iOS 18 changed what they are.

**Control Centre** is the panel that comes down from the top-right corner. In
iOS 18 it stopped being a fixed set of Apple's own toggles: tap the **+** at
the top and any app's *controls* can be added from a gallery, moved, and
**resized**. A control stretched to a big square is a far kinder target than
an app icon, and it is reachable from anywhere — including over a locked
screen, without unlocking first.

Two ways to get him in there:

- **No code, works today.** The Shortcuts app supplies a generic **Быстрая
  команда** control. Add it, point it at «Поговорить», done. This is what
  the app tells people to do (`CallHimSheet`), because it needs nothing
  shipped and nothing rebuilt.
- **A control of his own** (nicer: his name and face in the gallery instead of
  a generic shortcut glyph). This needs a `ControlWidgetButton` inside a
  **widget-extension target** — a second target in `project.yml`, new
  `.swift` files, and iOS 18 as the floor. That means `xcodegen generate`,
  which throws away the hand-set `DEVELOPMENT_TEAM`. Worth doing once the app
  is on the App Store; not worth doing mid-way through getting it onto a
  phone. **Not built.**

**The Lock Screen** now draws from the same pool. The torch and camera buttons
in the bottom corners are Control Centre controls, and either can be swapped
for another one: press and hold the Lock Screen → **Настроить** → **Экран
блокировки** → tap the button → pick. So one setup puts him in both places.

(Separately, iOS 16-17 have Lock Screen *widgets* — the small row under the
clock. The Shortcuts app offers one of those too. Same effect, older phones,
and it needs a Face ID unlock on the way through.)

### And with no tap at all

- **«Привет, Siri, поговорить с Боб»** — **needs nothing set up at all.** The
  phrases live in `BobShortcuts` (BobIntents.swift) and work from the moment
  the app is installed. Siri speaks Russian. This is why the setup robot
  teaches it FIRST: for a lot of people it will be the only one that ever
  gets used, because everything else on this page requires somebody to go
  into Settings and stay there.
- **Vocal Shortcuts** — *Настройки → Универсальный доступ → Голосовые
  команды.* Record a phrase three times and it triggers the intent. The only
  way to drop "Привет, Siri" entirely: works with the phone locked, recognised
  on-device. **iOS 18+, and untested by us for a Russian phrase** — Apple
  gates the feature by device language and does not publish the list clearly.
  Two minutes on a real phone settles it.

Neither needs hands. Both still bring the app forward to listen.

### Why none of this can be a pop-up, and what we do instead

The obvious wish is the one the local-network prompt grants: a sheet appears,
they tap «Разрешить», done. It is not available here, and the reason is a
category difference rather than a missing feature.

**A permission prompt is the system interrupting the user on the app's
behalf**, because the app just tried to do something — reach the local
network, open the microphone. The app never draws it, and never chooses when
it appears.

**Vocal Shortcuts and Back Tap are not permissions.** They are the user
configuring their own phone, in an Accessibility pane the app has no part in.
There is no API to create one, no API to prompt for one, and no public URL
that opens that pane — the `App-Prefs:` URLs that do are private, and using
them gets apps rejected. `UIApplication.openSettingsURLString` opens **this
app's own** Settings page and nothing else.

Two things that ARE in-app, and why neither is the answer:

- **`INUIAddVoiceShortcutViewController`** ("Add to Siri") — a real sheet,
  inside the app, no Settings. But since iOS 14 it asks the user to **type** a
  phrase rather than record one, it only ever sets a *Siri* phrase (so
  "Привет, Siri" is still required), and SiriKit was formally deprecated at
  WWDC 2026 in favour of App Intents. It would be work spent on a retiring
  framework to reach a worse result than the App Shortcuts we already ship.
- **`ShortcutsLink`** — opens the Shortcuts app at ours. A link, not a prompt.

So the honest shape is: **make the zero-setup path the headline** («Привет,
Siri, Боб, поговорим» — nothing to configure, works today), and for the ones
that genuinely need Settings, have the robot read the path out one step at a
time, with a button that at least launches the Settings app so nobody has to
find the grey cog. That is as close to a pop-up as iOS allows.

### Which leaves the docked kiosk as the real answer at home

Everything above is for *away* from the chair. Sitting with him, the app
stays open and pinned (Guided Access) and there is nothing to press at all —
which is still the design this is all built around.
