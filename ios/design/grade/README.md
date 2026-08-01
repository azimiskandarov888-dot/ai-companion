# Grading the photos into one world

Your five photos are beautiful, but they were taken by five different people in
five different lights. Side by side they read as a mood board, not an app.

This turns **five photographs into all eight screens**, graded so they look like
one place on one day.

---

# Step by step (Mac)

## 1 · Open Terminal

Press **⌘ + Space**, type `Terminal`, press **Enter**.

## 2 · Go to the project and get the latest

Paste this and press Enter (change the path if your folder is somewhere else):

```bash
cd ~/ai-companion && git pull
```

If it says *"No such file or directory"*, find your project folder in Finder,
type `cd ` in Terminal (with a space), then **drag the folder onto the Terminal
window** and press Enter.

## 3 · Install the two things it needs — once, ever

```bash
pip3 install pillow numpy
```

If `pip3` isn't found, try `python3 -m pip install pillow numpy`.

## 4 · Put your five photos in the `in` folder

```bash
open ios/design/grade/in
```

A Finder window opens. **Drag your five photos into it.**

**You don't have to rename anything.** Each photo is recognised by the
photographer's name in the filename — `pexels-aleksio-8123456.jpg` is enough.
The names it looks for are:

| Looks for | Your photo |
|---|---|
| `aleksio` | golden hills, ploughed field |
| `hilalbulbul` | alpine peaks, autumn trees |
| `zak` | moody meadow with pines |
| `yunustung` | green field, lone tree |
| `samuel` | alpine meadow, spruces, peak |

*(If a file downloaded without the name in it, just rename it so the name is in
there somewhere — `zak.jpg` works fine.)*

## 5 · Run it

```bash
cd ios/design/grade
python3 grade.py --report
```

You'll see eight lines like `✓ pexels-aleksio-8123456.jpg → 1-signin.jpg`.

## 6 · Look at the results

```bash
open out
```

Eight finished screens, already **1290 × 2796** — the exact size the app needs.

**Select them all in Finder and press Space** to flip through. They should feel
like one place. If one jumps out as wrong, see *Tuning* below.

---

# What you get

Five photos → eight screens. Some are used twice, cropped or dimmed differently.

| File | Screen | What was done |
|---|---|---|
| `1-signin.jpg` | Sign in | aleksio, full brightness |
| `2-payment.jpg` | Take care of him | hilalbulbul, dusk-ward |
| `3-story.jpg` | Tell your story | zak |
| `4-meet.jpg` | Who you'd like to meet | zak again — lower crop, cooler, dimmer: the same place an hour later |
| `5-companion.jpg` | Companion | yunustung, **darkened well toward night** |
| `6-diary.jpg` | His Diary | samuel |
| `7-account.jpg` | Account | aleksio again, **blurred + darkened** |
| `8-settings.jpg` | Settings | yunustung again, **blurred + darkest** |

The blurring on 7 and 8 also happens live in the app; these files exist so the
designer has the real thing to lay a layout on.

---

# How it works — and why it's two stages

**Stage 1 · Match.** Each photo is measured and pulled toward the same
destination: the same warmth, brightness, contrast, black point and colour
intensity. This part is *automatic and different for every photo*, because every
photo starts somewhere different. That's what makes them siblings — and it means
**any new photo you drop in will join the family** without you tuning anything.

**Stage 2 · Look.** Then the same house character goes on all of them: greens
pulled toward olive, skies calmed and warmed, warm light and warm shade, a
filmic curve, a whisper of grain.

Stage 1 makes them match. Stage 2 gives them character. One preset on five
different photos just makes five differently-wrong photos.

## The destination — "the golden medium"

- **Warm and sunlit**, but never orange
- **Real black in every frame** — this is what reads as expensive rather than flat
- **Medium-high contrast** — deliberately *not* the muted, washed-out look
- **Greens toward olive and gold**, away from emerald and lime
- **Skies desaturated and warmed** — no postcard blue
- **Warm highlights, warm-green shadows** — nothing in this app is cold

---

# Tuning

Everything worth changing is at the top of `grade.py`.

| Want it… | Change |
|---|---|
| warmer / cooler overall | `TARGET_BALANCE` — the R : G : B ratio |
| brighter / darker | `TARGET_LUMA_MEAN` |
| more / less punch | `TARGET_LUMA_STD`, and `contrast` in `LOOK` |
| richer / calmer colour | `TARGET_SAT`, and `vibrance` / `saturation` in `LOOK` |
| deeper blacks | `BLACK_POINT` (lower = deeper) |
| photos to keep more of their own character | `MATCH_STRENGTH` (lower = more individual) |
| one screen only | its line in `SCREENS` — `exposure`, `crop_bias`, `darken`, `blur` |
| a different crop | `crop_bias` — 0 keeps the top of the frame, 1 keeps the bottom |

Change **one thing at a time** and re-run with `--report`.

Watch the **spread** row: the smaller those numbers, the more the photos belong
together. Screens dimmed on purpose (Companion, Account, Settings) are marked
and left out of that calculation.

Add `--preview` to also write before/after strips.

---

# Swapping a photo, or using your own

Drop the new file in `in/`, make sure the right keyword is in its name, and
re-run. It gets graded into the same world automatically — nothing to re-tune.
