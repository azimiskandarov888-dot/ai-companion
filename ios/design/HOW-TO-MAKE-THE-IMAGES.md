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

**For adding things onto a real photo** (this is the main job — putting the scroll,
quill, and ink onto a rock):

- **Best: Photoshop + Generative Fill.** It is made exactly for this. You open a real
  photo, brush over an area, type what to add. Adobe lets you use the result
  commercially. About $10–25 a month.
- **Cheaper / no Photoshop: Google Gemini image editing.** Upload the photo, type what
  to add. Very good now, and there's a free tier to try.

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
| Story scene | `flat rock meadow`, `boulder grass field` |
| Second scene | `birch forest moss`, `stone woodland` |
| Profile | `treeline field`, `open meadow sky` |
| Living scene | `clearing tree rock`, `lone tree meadow` |

Pick calm, plain, real places. Not dramatic mountains. Make sure there is **empty
space** where text will go.

### 2. Add the scroll, quill, and ink to the rock photo

Open the rock photo in Photoshop (or Gemini), select the flat top of the rock, and paste
the edit prompt from **`IMAGE-PROMPTS.md`**.

Make 4 versions. Keep the one where **the shadows go the same way as the other shadows**
in the photo. Then zoom to 100 % and check the feather, the nib, and the ink bottle rim
are not melted.

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
