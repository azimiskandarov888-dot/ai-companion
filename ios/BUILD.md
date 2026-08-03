# Running the app on your Mac

All eight screens are built. Two things have to happen on your machine before it
will run: **the photographs go in**, and **Xcode makes a project**.

---

## 1 · Get the code

```bash
cd ~/ai-companion && git pull
```

## 2 · Put the eight photographs in

One command. It finds your graded exports, copies them into the app's asset
catalog under the right names, and tells you if any are missing:

```bash
~/ai-companion/ios/design/grade/install-photos.sh
```

It looks in `design/grade/out/` first, and if they aren't there it searches your
home folder for them. If you know where they are, say so:

```bash
~/ai-companion/ios/design/grade/install-photos.sh ~/Desktop/out
```

It should finish with **"Copied 8 of 8 into the app."**

*(Without the photographs the app still runs — every screen just falls back to
deep forest night. Nothing crashes.)*

## 3 · Make the Xcode project

Easiest, if you have Homebrew:

```bash
brew install xcodegen      # once, ever
cd ~/ai-companion/ios
xcodegen generate
open BobCompanion.xcodeproj
```

**Or by hand:** File → New → Project → iOS App, name it `BobCompanion`,
interface SwiftUI, then drag the `BobCompanion` folder into it and tick
"Create groups". Point the target's Info.plist at `BobCompanion/App/Info.plist`.

## 4 · Run it

Press **⌘R**. The simulator is fine for looking at every screen — but the
simulator has no microphone worth the name, so **he can only really talk on a
real iPhone**.

To put it on your phone you need a **free** Apple ID signed into Xcode
(Settings → Accounts). In the target's *Signing & Capabilities*, pick your name
under Team. A free account installs the app for 7 days at a time; a paid
Developer account ($99/yr) makes it permanent and is only needed later.

## 5 · Point it at the backend

Start the backend on your Mac:

```bash
cd ~/ai-companion/backend && ./run.sh
```

Find your Mac's address on the Wi-Fi:

```bash
ipconfig getifaddr en0        # e.g. 192.168.1.50
```

In the app: pull the **brass ring** at the bottom of his screen → **Настройки** →
**Сервер** → type `http://192.168.1.50:8000`.

Your phone and Mac must be on the same Wi-Fi.

---

# What you'll see

**First run**, once, in order:

1. **Sign in** — the meadow at first light
2. **Take care of him** — the two plans
3. **Tell your story** — the scroll
4. **Who you'd like to meet** — the second scroll, the caution, the quote
5. **He arrives** — the scene holds while the server writes him, then he's there

**Every run after that** opens straight to him. Pull the brass ring at the bottom
edge for **Дневник · Ты · Настройки**; swipe down to come back.

---

# What's real, and what's a stand-in

| | |
|---|---|
| **Real** | Talking to him, his memory, his diary, the friend being created from your story — all of it hits the backend you already have running. |
| **Stand-in** | **Sign in** stores a local account (no Apple/Google yet). **Payment** just advances — nothing is charged, and there's no StoreKit. Both screens are otherwise complete: every pixel, state and animation. |
| **Placeholder** | **The orb** is a plain circle. Everything around it — its size per state, the pooled light, the breathing — is the real design, waiting for your art. |

## Dropping your orb in

One view, one file: `Components/OrbView.swift`, the `OrbShape` struct at the
bottom. Replace its body with your image:

```swift
Image("orb")
    .resizable()
    .scaledToFit()
```

Add `orb.imageset` to the asset catalog the same way as the photos. Nothing else
in the app changes — every screen asks for `OrbView`, and the sizes, light and
motion stay exactly as designed.

## Renaming the app

Two places: `CFBundleDisplayName` in `App/Info.plist`, and `AppInfo.displayName`
in `Screens/SettingsScreen.swift`. (The Xcode target keeps its name; that's
internal and nobody sees it.)

---

# Where things are

```
App/          AppFlow.swift — how the eight screens connect
Design/       Theme · Typography · Metrics · Strings (the whole copy deck, RU+EN)
Components/   PhotoBackground · Controls · ParchmentScroll · DiaryBook · OrbView · BrassRing
Screens/      one file per screen
Store/        Stores.swift — account, subscription, and his name
Audio/ Net/ Conversation/    the voice loop, unchanged and already working
```

Every number in `Design/Metrics.swift` is expressed as a fraction of the screen,
with the design's original 932 pt value in the comment — so the rhythm survives
on a small iPhone, and the code can always be checked against the design.
