# How to make the 6 pictures — simple steps

Two different AIs do two different jobs. Don't mix them up:

| Job | Who does it |
|-----|-------------|
| Design the **screens** (layout, buttons, text) | **Claude design** |
| Make the **6 pictures** (landscapes, the rock scene) | **an image AI** (below) |

Claude design does not make photos.

**Order changed — make the pictures FIRST.** Then send them to Claude design with the
spec, so it designs the screens directly on your real photographs instead of on grey
boxes. The result will be far better.

**Every picture covers the whole phone screen.** Not a small picture at the top with a
dark background below — the photo is the screen, and the text sits on top of it.

---

## Which image AI to use

**For adding things onto a real photo** (this is the main job — putting the rock, scroll,
quill, and ink into a meadow photo):

- **Best: Google Gemini image editing.** Upload the photo, paste the prompt. It's the best
  at "change only this, keep everything else," needs no skills, and is free to try.
- **Also good: Photoshop + Generative Fill.** You brush exactly where the rock goes and can
  fix the seam by hand. Safest licence for a paid app. About $10–25 a month.
- **Avoid for this: ChatGPT image generation** — it tends to redraw the whole picture, so
  your real photo stops being a real photo.

**For making a whole scene from nothing** (only if you can't find a real photo):

- **Midjourney** — the best-looking landscapes. About $10 a month.

*Tools change fast — check the current price and that your plan allows commercial use.*

---

## Step by step

### 1. Get real photos first (free)

Go to **unsplash.com** or **pexels.com** and download big versions of:

| For | Search words |
|-----|--------------|
| Sign-in | `green hillside morning`, `meadow golden hour` |
| Payment | `valley dusk`, `hills sunset calm` |
| Story scene | `meadow low angle`, `grass field close up horizon` — **no rock needed, we add it** |
| Second scene | `birch forest floor`, `woodland clearing light` — **no rock needed** |
| Profile | `treeline field`, `open meadow sky` |
| Living scene | `clearing tree rock`, `lone tree meadow` |

Pick calm, plain, real places. Not dramatic mountains. Make sure there is **empty
space** where text will go.

### 2. Build the rock scene — one prompt, everything at once

**You won't find a photo of a table-like rock. Don't look for one — add it with AI.** Keep
the landscape real (grass and trees are the hard part to fake); the rock is the easy part,
because no shape is "wrong."

Ask for the **rock, scroll, quill, and ink together in one prompt**, so the AI knows the
rock's job is to be a table. The full prompt is in **`IMAGE-PROMPTS.md`** — before pasting
it, look at your photo and fill in **which side the sun comes from**.

Make 4 versions and judge them in this order:
1. **Shadow direction** — do the new shadows fall the same way as the real ones?
2. **Contact shadows** — a dark line where the rock meets the ground, small shadows under
   the scroll and bottle.
3. **Grass over the base** — a few blades crossing in front, or it looks like a sticker.
4. **Sharpness** — the new things must be exactly as sharp as real things that far away.

If one object comes out bad, don't start over — run a small second edit on just that spot.

Do the same for the second scene photo.

### 3. Only if you can't find a good photo — make the whole thing

Every prompt you need is in **`IMAGE-PROMPTS.md`**, one per picture, ready to paste,
with the "don't make it fake" list to add at the end.

### 4. Make all 6 look like one place

Put the same color filter on all six: a bit greener in the shadows, a bit warmer in the
light, same brightness, same grain. This is the step that makes them feel like one
world. Photoshop, Lightroom, or even one preset is enough.

### 5. Check every picture before using it

Zoom to 100% and throw it away if you see: shadows going different ways · no real dark
anywhere · melted feather or ink jar · repeating grass or clouds · everything shiny and
too clean. (Full list in `IMAGERY-BRIEF.md`.)

### 6. Save them

- **1290 × 2796 pixels or bigger**, PNG.
- The living scene needs **5 separate pictures** with transparent backgrounds:
  sky, far hills, tree, rock, front grass. (Cut each one out, then use generative fill to
  paint what was behind it.)
- Keep a `credits.txt` saying where each photo came from.

---

## What to do first

1. Collect the 6 real photos (step 1) — free, today.
2. Add the scroll, quill, and ink to the two rock photos (step 2).
3. Grade all six the same (step 4) and check them (step 5).
4. **Then** send Claude design: the prompt, `product-spec.html`, `palette.html`, **and
   your six pictures**. It will design the screens on top of the real images.
