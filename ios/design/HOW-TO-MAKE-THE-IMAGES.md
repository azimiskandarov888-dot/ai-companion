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
| Story scene | *(generated — see step 2; no stock photo)* |
| Second scene | *(generated — see step 2; no stock photo)* |
| Profile | `treeline field`, `open meadow sky` |
| Living scene | `clearing tree rock`, `lone tree meadow` |

Pick calm, plain, real places. Not dramatic mountains. Make sure there is **empty
space** where text will go.

### 2. Build the two writing scenes — GENERATE these, don't edit

The writing scenes (3 and 4) are the exception: **they must be generated whole.**

A real landscape photo is taken standing up, looking far away. The writing scene needs the
scroll **half a metre from the lens, filling half the frame**. That's a different camera —
so editing a landscape photo can never produce it. The model has to rebuild the whole
picture, and that's why it kept "regenerating the scenery."

So: **attach your landscape photo as a colour and light reference**, and generate a new
frame from the prompt in **`IMAGE-PROMPTS.md`**. Ask for 4K.

Judge them in this order:
1. **Scroll square to you** — rollers left and right, page facing you like paper on a desk.
   Turned or angled = it looks like someone photographed it. Reject.
2. **Fills about half the frame**, near edge cut off by the bottom of the picture.
3. **No hands, no people.**
4. **Nothing written on the parchment.**
5. **Contact shadows** under the scroll, quill and bottle.

If one thing is wrong, don't start over — re-run with a single "keep everything, only
change X" instruction.

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

1. Collect the 4 real photos (step 1) — free, today.
2. Generate the two writing scenes (step 2), using one of those photos as the look reference.
3. Grade all six the same (step 4) and check them (step 5).
4. **Then** send Claude design: the prompt, `product-spec.html`, `palette.html`, **and
   your six pictures**. It will design the screens on top of the real images.
