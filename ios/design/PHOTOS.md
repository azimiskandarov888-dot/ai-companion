# The photos — what to find, and where

**No AI. Real photographs only.** Five beautiful landscapes from a free stock site, used
full-screen behind the interface. Later, replace any of them with your own photography —
nothing in the app has to change, the files just get swapped.

**Where:** [pexels.com](https://pexels.com) and [unsplash.com](https://unsplash.com) —
free, commercial use allowed. Always download the **largest size offered**.

---

## What every photo needs

- **Vertical**, and at least **1290 × 2796 px** (a whole phone screen). Landscape-format
  shots crop badly — filter for portrait/vertical.
- **A quiet area** where text or a panel will sit. This is the one rule people forget: a
  photo that's beautiful corner-to-corner is unusable, because the words land on top of it.
- **Calm and ordinary** beats epic. A plain hillside at a good hour reads as *real*; a
  dramatic mountain reads as a wallpaper.
- **No people, no buildings, no roads, no signs.** Nothing to identify a place or a person.
- **Soft, natural light.** Morning, overcast, or late afternoon. Avoid harsh midday sun,
  heavy HDR edits, and anything oversaturated.
- Colours that suit the palette: **green, moss, dry gold grass, warm shadow.** Avoid strong
  blues, purples, autumn orange, and snow.

---

## Chosen — and which screen each one is for

| Screen | Photo | File name for the grader |
|---|---|---|
| 1 · Sign in | **aleksio** — golden hills, ploughed field | `1-signin.jpg` |
| 2 · Take care of him | **hilalbulbul** — alpine peaks, autumn trees | `2-payment.jpg` |
| 3 · Tell your story | **zak** — moody meadow with pines | `3-scroll.jpg` |
| 4 · Who you'd like to meet | **zak** again, different crop | *(same file)* |
| 5 · Companion | **yunustung** — green field, lone tree | `6-companion.jpg` |
| 6 · His Diary | **samuel** — alpine meadow, spruces, peak | `7-diary.jpg` |
| 7 · Account | **aleksio** again, blurred | *(same file)* |
| 8 · Settings | **yunustung** again, blurred and darker | *(same file)* |

Five photographs cover eight screens — 7 and 8 are blurred past recognition, so a
sixth photo would add weight and change nothing you can see.

## Grade them — `ios/design/grade/`

Don't hand-grade these. Put them in `grade/in/` with the names above and run:

```bash
cd ios/design/grade
pip3 install pillow numpy
python3 grade.py --preview --report
```

It measures each photo, pulls it toward one shared destination — same warmth,
brightness, contrast, black point and colour intensity — then applies the same
house look to all of them. Output lands in `grade/out/`, already cropped to
1290 × 2796. Full explanation in `grade/README.md`.

**Watch the `spread` row in the report.** The smaller those numbers, the more the
photos belong together.

## What to look for, if you ever replace one

- **1 · Sign in** — the most important. Quiet, open, hopeful; empty sky above, calm ground
  below for the buttons. `green hills morning`, `meadow golden hour`, `foggy field sunrise`
- **2 · Take care of him** — quieter than the hero; mostly shadow with one band of light.
  `valley dusk`, `evening field`, `twilight meadow`
- **3 / 4 · The writing screens** — the scroll covers half the screen, so the middle and
  lower half must be **uncluttered**. `open green field sky`, `simple meadow`, `misty meadow`
- **5 · Companion** — he lives here, and it's darkened toward night. Simple shapes, a quiet
  centre. `lone tree meadow`, `single tree field`, `oak tree hillside`
- **6 · Diary** — a settled, sheltered place to read in; the foreground carries the book.
  `forest clearing light`, `alpine meadow`, `quiet woodland`

## After you've chosen them

**1 · Check each one.** Shrink it to phone size: does it read in one glance, with room for
words? Then look at full size for anything distracting — a fence post, a rooftop, a person
in the distance.

**2 · Grade them together** with `grade/grade.py` (above). This matters more than which
photos you pick: five good photos with different colour casts look like a mood board; the
same five graded together look like one place on one day — which is the whole feeling of
the app. The tool exports at 1290 × 2796 already.

**4 · Keep a `credits.txt`** beside the files: photo name, photographer, source URL, and
licence. You'll want it once the app is on sale.

---

## Licence check (quick, but do it)

Pexels and Unsplash both allow commercial use and modification with no attribution
required — but check the individual photo page anyway, and avoid any shot with a
recognisable person, a private house, or a trademarked landmark in it.

---

## Later — when you shoot your own

Everything above is the brief for your own camera too. The short version:

- Shoot **vertical**, in **morning or late-afternoon** light, or under soft overcast.
- Leave **empty space** in the frame where the words will go — resist filling it.
- Keep it **plain**. The place doesn't need to be spectacular; it needs to be calm.
- For the **companion screen**, find a tree with open ground beside it, shot from a low
  angle so the ground reads as a place he could be standing in.
- If you ever want the writing scene as a real photograph: a **flat rock**, a real scroll on
  it, shot from **seated height with a wide lens about half a metre away**, so the scroll
  fills the lower half of the frame. That is a real photo you can take in an afternoon —
  and it's the one thing no stock library or AI could give us.
