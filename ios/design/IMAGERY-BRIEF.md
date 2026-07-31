# The imagery — how to make it beautiful, and not AI slop

*Everything about the photographs and scenes. Screen layouts live in
`product-spec.html`; colors in `palette.html`.*

---

## The direction

The landscapes are **photographic and photorealistic**. Real photographs wherever
possible. **AI is allowed** — to build what photography can't hand us (a parchment
scroll and quill on a sunlit rock), to extend a frame, and to cut the living scene into
layers.

The bar is not "was AI involved." The bar is:

> **Does any part of it look generated?** If yes, it doesn't ship.

That's a craft problem with a known solution, and the rest of this document is that
solution.

---

## Method — work down this list, not up

Each step is riskier than the one before it. Start at 1 and only go further when you
must.

**1 · A real photograph as the base.**
Licensed stock of a real place. A real photo of an ordinary hillside at the right hour
beats anything generated, and carries zero slop risk. Sources below.

**2 · AI composited onto that photo** (generative fill / inpainting).
This is how the scroll, quill, and ink get onto the rock. Editing a real photograph
beats generating one from nothing, every single time — the light, grain, and lens are
already real, and the AI only has to match them.

*How to do it well:* mask a small area; describe only the object, not the scene; tell it
the light direction that's already in the photo; generate several; keep the one whose
shadow agrees with the rest of the frame. Then hand-fix the seam.

**3 · Full AI generation** — only when 1 and 2 can't get there.
Prompt like a photographer, never like a wallpaper: name the **lens, hour, light
direction, depth of field, and film stock**. Recipes below.

**4 · One grade over everything.**
Photos and AI frames get graded together into our palette — deep green shade, warm gold
light, matched contrast, matched grain. **This step is what makes a mixed set feel like
one world** instead of a mood board. Do not skip it. Same LUT, same grain, same black
point on all six images.

---

## The slop tells — reject on sight

Keep this list beside you. Most AI images fail two or three of these at once.

**Light**
- Shadows pointing in different directions in one frame
- Everything lit, no true black anywhere; flat HDR look
- A soft glow/haze/bloom laid over the whole image
- Light with no source you can point to

**Focus & detail**
- Maximum detail everywhere at once, with no focal point
- Sharpness that never falls off with distance — no real lens does this
- Over-sharpened halos around edges (usually from a bad upscale)

**Small things (zoom to 100 % — this is where slop hides)**
- Quill barbs melting into the feather shaft
- The ink jar's rim not closing, or its reflection making no sense
- Rock edges dissolving; branches that merge into each other
- Grass, leaves, clouds, or stone visibly **tiling / repeating**
- Any invented text, lettering, or symbols — delete them

**Surfaces**
- Plastic or waxy sheen; everything looks slightly wet
- Unnaturally clean: no dust, no wear, no dead grass

**Composition**
- Dead-centered and symmetrical; subject floating in the middle
- Horizon perfectly level *and* perfectly halfway
- Wrong scale — a scroll bigger than the rock, an arm-sized quill

**Vibe**
- Fantasy leakage: magic particles, glowing dust, impossible moons
- "Epic" everything — dramatic peaks, sunbeams, dramatic clouds, all at once

---

## What a good one has instead

- **One sun, one shadow direction**, and **real darkness** somewhere in the frame.
- A **focal point**, with everything else falling away — believable depth of field.
- **Imperfection**: dust, wear, a chipped rock, dry grass, an off-centre horizon.
- **Air** — quiet, empty space where the scroll and the words will sit.
- **Restraint**: a plain place at a good hour beats an epic place at every hour.
- Colors that agree with our palette: mossy greens, dry gold grass, warm shadow, no
  cold blue-gray.

---

## The 100 % check (run it on every image before it ships)

1. Zoom to **100 %** and pan the whole frame. Slop lives in the small stuff.
2. Pick three objects. Do their shadows agree on where the sun is? If not — reject.
3. Find the darkest pixel. Is there real black? If everything is mid-grey — reject.
4. Look for repeats: the same tuft of grass, the same cloud edge, the same stone twice.
5. Check every man-made object (scroll, quill, ink) at 100 %: does it close, sit, and
   cast a shadow like a real object with weight?
6. Flip it horizontally and look again — mistakes jump out in the mirror.
7. Shrink it to phone size. Does it still read in one glance, with space for text?
8. Put all six side by side. Do they look like one place, one camera, one day?

If an image needs an explanation to survive, it fails.

---

## Prompt recipes

Photographic language only. Generate several, keep one. Add the negative list to every
prompt.

**Universal negative:**
`HDR, oversaturated, glowing, bloom, haze, lens flare, sunbeams, god rays, symmetrical,
centered, plastic, waxy, glossy, hyperdetailed, ultra sharp, fantasy, magical, glowing
particles, text, letters, watermark, logo, heavy vignette, tilt-shift, oversharpened,
cartoon, 3d render, cgi, illustration`

**1 · Sign-in hero**
> Photograph of a quiet green hillside meadow with a few scattered trees, early morning,
> low side light from the left, long soft shadows across dry gold grass. Shot on 35 mm
> film, 50 mm lens, f/8, natural color, fine grain. Warm muted palette of mossy green
> and pale gold. Empty sky in the upper half. No people, no buildings. Vertical.

**2 · Payment backdrop**
> Photograph of a wide calm valley at dusk, warm low sun behind distant hills, deep
> green shadow in the foreground. 35 mm film, 85 mm lens, f/5.6, soft natural contrast,
> fine grain. Muted and quiet, mostly shadow with one band of warm light. Vertical, room
> at the bottom for text.

**3 · Story scene** *(best made by step 2 — inpaint onto a real photo of a rock)*
> Photograph of a weathered flat granite boulder in a sunlit meadow, an old parchment
> scroll unrolled across the stone, a goose-feather quill and a small glass ink bottle
> resting beside it. Late afternoon side light from the right, long soft shadows. 35 mm
> film, 50 mm lens, f/8, deep focus, natural color, fine grain. Dry gold grass, mossy
> green shade. Plenty of empty space above the rock. No people. Vertical.

**4 · Second scene** — same as #3, a clearly different place:
> …a low flat stone at the edge of a birch wood, soft overcast light, damp green moss,
> cooler and quieter than the meadow…

**5 · Profile band**
> Photograph of a calm treeline and open field under a soft sky, midday, gentle light.
> 35 mm film, 50 mm lens, f/8, fine grain. Simple, uncluttered, horizontal band
> composition with empty sky. No focal drama.

**6 · The living scene** *(generate the full frame first, then cut it into layers)*
> Photograph of a small clearing: a large old tree on the left, a flat sitting rock in
> the middle distance, open grass between them, gentle hills behind, late afternoon
> light from the left, long shadows. 35 mm film, 35 mm lens, f/8, deep focus, natural
> color, fine grain. Calm, uncluttered, generous empty ground in the centre. No people.
> Vertical.

Then separate it into **five transparent PNGs on one canvas**, back to front:
`sky` · `far` (distant hills/treeline) · `tree` (the orb passes behind it) · `rock` (the
orb sits on it — its top edge must read as a surface) · `fore` (grass the orb passes
behind). Use generative fill to paint what's *behind* each layer you lift out. Keep
detail modest near the seams — parallax moves these a few pixels, and over-detail
betrays the cut.

*Optional, later, and lovely:* morning / day / dusk / night versions of this same scene,
so it follows his real time of day.

---

## Where the real photos come from

- **Free, commercial use allowed:** Unsplash, Pexels, Wikimedia Commons (check each
  file's license — Commons is a mix).
- **Paid, higher quality and safer:** Adobe Stock, Stocksy, Getty, Shutterstock.
- Prefer **specific, ordinary, real places** over epic ones — they hold up better and
  look far less stock-y.

**License check before shipping any photo:** commercial use permitted, modification
permitted, no attribution obligation you can't meet, and no recognizable people or
private property that would need a release. Keep a small `credits.txt` beside the assets
recording where each image came from and under what license — you'll want it once the
app is on sale.

**On the AI side:** confirm your generator's terms grant commercial rights on your plan
(most paid tiers do; free tiers often don't). Also worth knowing, since this app takes
payment: in the US, purely AI-generated images generally **can't be copyrighted**, so
you couldn't stop someone reusing them. Compositing AI onto a photo you've licensed,
plus your own grading, puts you on much firmer ground — another reason method 2 beats
method 3.

---

## Files

- **1290 × 2796 px minimum** (iPhone Pro Max @3x); larger is fine, we downscale.
- **sRGB**, PNG. Layers: transparent PNGs, all on the identical canvas size.
- Ship a flattened preview of the living scene so the composition can be checked.
- Upscale gently — aggressive AI upscaling adds halos and micro-detail, which is itself
  a slop tell. Better to generate large than to enlarge small.
