# Grading the photos into one world

Your five photos are beautiful, but they were taken by five different people in
five different lights. Side by side they read as a mood board, not an app. This
fixes that.

## Run it

```bash
cd ios/design/grade
pip3 install pillow numpy        # once
```

Put your originals in `in/`, named for the screen they belong to:

```
in/1-signin.jpg       ← aleksio      (golden hills, ploughed field)
in/2-payment.jpg      ← hilalbulbul  (alpine, snowy peaks, autumn trees)
in/3-scroll.jpg       ← zak          (moody meadow with pines)
in/6-companion.jpg    ← yunustung    (green field, lone tree)
in/7-diary.jpg        ← samuel       (alpine meadow, spruces, peak)
```

Then:

```bash
python3 grade.py --preview --report
```

Graded files land in `out/`, already cropped to **1290 × 2796** (a whole phone
screen). `--preview` writes before/after strips; `--report` prints the numbers.

## How it works — and why it's two stages

**Stage 1 · Match.** Each photo is measured and pulled toward the same
destination: the same warmth, brightness, contrast, black point, and colour
intensity. This part is *automatic and different for every photo*, because every
photo starts somewhere different. That's the part that makes them siblings — and
it means **any new photo you drop in will join the family**, without you tuning
anything.

**Stage 2 · Look.** Then the same house character goes on all of them: greens
pulled toward olive, skies calmed and warmed, warm light and warm shade, a
filmic curve, a whisper of grain.

Stage 1 makes them match. Stage 2 gives them character. Neither works alone —
one preset on five different photos just makes five differently-wrong photos.

## The destination — "the golden medium"

- **Warm and sunlit**, but never orange
- **Real black in every frame** — this is what reads as expensive rather than flat
- **Medium-high contrast** — deliberately *not* the muted, washed-out
  "cinematic" look
- **Greens toward olive and gold**, away from emerald and lime
- **Skies desaturated and warmed** — no postcard blue
- **Warm highlights, warm-green shadows** — nothing in this app is cold

## Tuning it

Everything worth changing is at the top of `grade.py`:

| Want it… | Change |
|---|---|
| warmer / cooler overall | `TARGET_BALANCE` — the R : G : B ratio |
| brighter / darker | `TARGET_LUMA_MEAN` |
| more / less punch | `TARGET_LUMA_STD`, and `contrast` in `LOOK` |
| richer / calmer colour | `TARGET_SAT`, and `vibrance` / `saturation` in `LOOK` |
| deeper blacks | `BLACK_POINT` (lower = deeper) |
| the photos more individual | `MATCH_STRENGTH` (lower = more of their own character) |
| one photo only | add to `TASTE` — small nudges, the matching does the rest |

Change one thing at a time and re-run with `--report`. The **spread** row is the
thing to watch: the smaller those numbers, the more the photos belong together.

## When you shoot your own

Drop them in the same folder with the same names and re-run. They'll be graded
into the same world automatically — no re-tuning.
