# How to make the 6 pictures — simple steps

Two different AIs do two different jobs. Don't mix them up:

| Job | Who does it |
|-----|-------------|
| Design the **screens** (layout, buttons, text) | **Claude design** |
| Make the **6 pictures** (landscapes, the rock scene) | **an image AI** (below) |

Claude design does not make photos. It draws the screens and leaves a grey box
where each picture goes. You fill those boxes with the pictures you make here.

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

### 2. Add the scroll to the rock photo

Open the rock photo in Photoshop (or Gemini). Select the top of the rock. Paste this:

> Add an old parchment scroll lying unrolled flat on this rock, with a goose feather
> quill and a small glass ink bottle beside it. Match the light already in the photo:
> same sun direction, same shadow length, same softness. Same grain and sharpness as the
> rest of the photo. Nothing written on the scroll. Photorealistic, natural, slightly
> worn and dusty.

Make 4 versions. Keep the one where **the shadow goes the same way as the other
shadows** in the photo. Then zoom to 100% and check the feather and the ink jar are not
melted.

Do the same for the second scene photo.

### 3. Only if you can't find a good photo — make one

Paste this into Midjourney (change the place for each picture):

> Photograph of a quiet green hillside meadow with a few scattered trees, early morning,
> low side light from the left, long soft shadows across dry gold grass. Shot on 35 mm
> film, 50 mm lens, f/8, natural color, fine grain. Warm muted palette of mossy green
> and pale gold. Empty sky in the upper half. No people, no buildings. Vertical.

And always add this at the end so it doesn't look fake:

> --no HDR, oversaturated, glowing, bloom, lens flare, god rays, symmetrical, plastic,
> glossy, hyperdetailed, fantasy, magical, glowing particles, text, watermark, cartoon,
> 3d render, cgi, illustration

More ready-made prompts for each picture are in `IMAGERY-BRIEF.md`.

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

Send everything to Claude design **now** — you don't need the pictures yet. While it
works, collect the real photos from step 1. When the designs come back you'll know the
exact shape and crop each picture needs, and then you do steps 2–6.
