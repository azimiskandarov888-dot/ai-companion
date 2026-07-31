# The 6 image prompts — copy and paste

**Make these images first.** Then send them to Claude design together with the spec, so
it designs the screens on top of your real photographs instead of grey boxes.

## Rules that apply to all six

- **Vertical**, made for a whole phone screen: **1290 × 2796 px minimum** (9:19.5).
  In Midjourney add `--ar 9:19.5`.
- **The photo fills the entire screen.** It is not a header, not a strip, not a card.
- **Leave a quiet area** where text will go — usually the lower third, sometimes the top.
- **One sun, one shadow direction**, and real darkness somewhere in frame.
- **No people. No text, letters, or writing** anywhere in the image.
- After you have all six, put the **same color grade + grain** on all of them, so they
  look like one place on one day.

**Add this negative to every prompt** (Midjourney: put it after `--no`):

```
HDR, oversaturated, glowing, bloom, haze, lens flare, god rays, symmetrical, centered,
plastic, waxy, glossy, hyperdetailed, ultra sharp, fantasy, magical, glowing particles,
text, letters, writing, watermark, logo, heavy vignette, tilt-shift, oversharpened,
cartoon, 3d render, cgi, illustration, people, hands
```

---

# ⭐ 3 · The story scene — the important one

**A first-person view: you are sitting on the ground, using a flat rock as your desk, and
the open scroll is right there in front of you — with the landscape beyond it.** Not a
photo of a scroll standing somewhere. *Your* view, as if you look down and start writing.

### Which AI to use for this

| | Tool | Why |
|---|------|-----|
| **1st choice** | **Google Gemini image editing** — the model nicknamed **"Nano Banana"**. In the Gemini app, upload the photo and paste the prompt; pick the **newest / Pro image model** offered. | Best at "change only this, keep everything else." No masking, no skills needed. Free to try. |
| **2nd choice** | **Photoshop → Generative Fill** (Adobe Firefly) | Replaces only the area you select, leaving the rest of your file untouched at full resolution. Safest licence for a paid app. Keep the prompt short — its box is small. |
| **Avoid here** | ChatGPT image generation | It tends to redraw the *whole* picture, so your real photo stops being a real photo. |

*Tools move fast — check current pricing and that your plan allows commercial use.*

---

### 🚨 First: why it came back low quality (and how to stop it)

**This is the tool, not you.** These editors don't hand your photo back — they *re-render
the whole frame* at their own output size, usually around 1024 px. So a gorgeous 4000 px
photo returns as a small, soft, mushy one. No prompt fixes that.

Three fixes, best first:

**1 · Ask for the biggest output the tool offers.**
Nano Banana **Pro** can output at **2K and 4K** — pick the highest resolution setting
available, or add to the end of your prompt: *"Output at maximum resolution, 4K."* The
plain/fast model can't, so make sure you're on the Pro image model.

**2 · Edit a CROP, then paste it back.** ⭐ *This is the real answer.*
- Open your original photo at full size and **crop out just the area** where the rock and
  scroll will go (roughly the lower half). Save that crop at its **full original pixels**.
- Run the prompt on **only that crop**.
- Open the original again in Photoshop — or **photopea.com**, which is free in the browser
  — paste the returned crop on top, scale it to line up exactly, and soften its edges.
- Your sky, hills, tree and far grass stay **100 % untouched original quality**. Only the
  small area you actually changed is AI.

**3 · Or use Photoshop Generative Fill**, which only ever replaces the selection. Keep the
selection modest — the bigger the area, the more the generated pixels get stretched and
softened.

**One extra touch:** the returned patch is usually *too clean* compared to the real photo.
Add a little noise/grain to it so it matches the original's texture. Without this, the
patch looks subtly plastic even when everything else is right.

---

### The prompt — POV, seated, fancy scroll, soft light

Your photo has soft overcast light, so this version has **no hard shadows** in it. If you
later use a sunny photo, swap the light paragraph for the sunny one further below.

```
Edit this photograph into a first-person point of view: I am sitting on the ground in this
field, using a flat rock in front of me as a writing desk, looking down at an open scroll
on it.

THE VIEW: the camera is at the eye level of a person sitting on the ground — low, close to
the rock, tilted slightly downward toward the scroll, but the field, the hills and the sky
are still clearly visible in the upper part of the frame, exactly as they are now. It must
feel like my own eyes, not like a photograph of a scene. Absolutely NO person, NO hands, NO
arms, NO body, NO feet anywhere in the image.

THE ROCK: directly in front of me, close to the camera, filling the lower part of the frame
and running off the bottom edge. One low granite boulder with a broad, roughly flat top
being used as a desk. Grey-brown stone, worn rounded edges, patches of lichen, a few natural
cracks, dry dust in the hollows. It sits heavily in the ground — the grass around its base
is pressed down and darker, and blades of grass overlap its bottom edge.

THE SCROLL: lying open across the rock, seen in perspective from where I sit — the near
edge wider and lower, the far edge narrower, foreshortened naturally. It is a fine scroll
wound on two turned wooden rollers, one at each end, so the open sheet is held between
them; the rods are dark polished wood with small aged brass end-caps, and the far rod
still has a little of the scroll wound around it. A thin leather cord lies loose beside it.
The parchment between the rods is soft grey-cream, thick, with fine fibres, faint age
spots and a gentle curl — elegant and well kept, not burnt, not torn, not crumpled.
Absolutely nothing written, drawn, or printed on it — the surface is completely blank.

ALSO ON THE ROCK: a white goose feather quill with a slim dark metal nib resting across
the stone beside the scroll, and a small heavy glass ink bottle with dark ink and a worn
cork, small enough to fit in a palm. Each object casts a small soft dark contact shadow
where it touches the stone, so everything clearly has weight and truly rests on it.

MATCH THE PHOTOGRAPH EXACTLY: the light is soft, diffuse, overcast midday light with no
direct sun — there are NO hard cast shadows anywhere in this image and there must be none
on the new objects either. Light everything evenly and softly from above, with only gentle
ambient shading and soft contact shadows underneath. No long shadows, no sunlit edges, no
bright specular highlights. Match the existing cool, muted, low-contrast colour, the slight
atmospheric haze, the film grain and the lens softness. The parchment must sit at the same
muted exposure as the rest of the photo — never bright white. Keep the scroll and rock
sharp, and let the far landscape stay exactly as soft as it already is.

DO NOT change anything else: keep the existing grass, trees, hills, sky, horizon, colours,
brightness and grain exactly as they are. Do not re-render, re-light, or sharpen the rest
of the image.

Photorealistic, ordinary, understated — as if I simply sat down here and took this with my
own eyes. No glow, no rim light, no added highlights, no HDR, no extra sharpening, no text,
no watermark; nothing polished, sculpted, or symmetrical.

Output at maximum resolution, 4K.
```

**Short version** (for Photoshop's Generative Fill box, after masking the lower foreground):

```
first person seated view of a flat granite rock used as a desk, an open scroll on it wound
on two turned wooden rollers with brass end-caps, seen in perspective, blank parchment, a
white feather quill and small glass ink bottle beside it, soft contact shadows, grass
overlapping the rock base, soft overcast light, no hard shadows, matching the photo's grain
and focus, photorealistic, no hands, nothing written
```

---

### If you use a sunny photo instead

Replace the light paragraph with:

```
MATCH THE PHOTOGRAPH EXACTLY: the sunlight comes from [THE LEFT / THE RIGHT / BEHIND THE
CAMERA] — every new shadow must fall the same way, with the same length and the same
softness as the shadows already in the picture. Match the existing colour temperature,
exposure, contrast, film grain, noise and lens softness.
```

---

### After it generates — the things that give it away

Make **4 versions**, then judge them on this, in order:

1. **Is it really POV?** The scroll should feel like it's an arm's length in front of *you*
   — near edge close and wide, far edge smaller, horizon still visible above. If it looks
   like a photo of a rock taken from a few steps back, say so and regenerate:
   *"Closer. Sit lower. The scroll should fill the bottom half of the frame in perspective."*
2. **No hands, no people.** If any appear, regenerate — never try to fix hands.
3. **Contact shadows.** Dark line where the rock meets the ground; small soft shadows under
   the scroll, rods, quill and bottle. Without those, everything floats.
4. **Grass over the base.** A few blades crossing in front of the stone, or it reads as a sticker.
5. **The parchment isn't glowing white.** In a muted photo, a bright scroll is the single
   biggest tell.
6. **Nothing written on it.** These models love to invent letters. Zoom in and check.
7. **Sharpness and grain match** the real parts of the photo at that distance.

### Fixing without starting over

If it's 90 % right, don't re-roll — run a small second pass:

> Keep everything exactly as it is. Only [make the parchment darker and softer / replace
> the quill with a clean white goose feather with a slim dark nib / remove the writing from
> the parchment so it is completely blank], same position, same shadow, same light.

---

#### If you'd still rather find a real rock

These search words work better than "flat rock" (which mostly returns big round
boulders): `stone slab`, `rock ledge`, `flat rocks river`, `slate shore`, `stepping
stone`, `granite outcrop`, `dolmen` (a natural stone table), `stone bench garden`. Photos
of people sitting on flat rocks work too — crop the people out.

But don't spend hours on it. Adding the rock gives you exactly the shape and angle you
want.

---

### Fallback — generate the whole scene

```
First-person point of view of someone sitting on the ground in an open green meadow, using
a large flat weathered rock in front of them as a writing desk. The camera is at seated eye
level, low and close, tilted slightly down toward the rock, with the field, soft hills and
sky still visible in the upper part of the frame. No person, no hands, no body visible.
On the rock lies an open scroll wound on two turned dark wooden rollers with small aged
brass end-caps, seen in perspective — near edge wider, far edge narrower. The parchment is
soft grey-cream, thick, gently curled, completely blank with nothing written on it. A white
goose feather quill with a slim dark metal nib rests beside it, and a small heavy glass ink
bottle with a worn cork. Soft diffuse overcast light, no hard shadows, only gentle contact
shadows under each object. Shot on 35 mm film, 28 mm lens, f/5.6, scroll sharp and the
landscape softening behind, cool muted low-contrast colour, fine grain. Quiet and
uncluttered. Vertical, --ar 9:19.5
```

# 4 · The second scene

Same first-person view, clearly a **different place** — cooler, quieter, shadier.

Start from a real photo of the **edge of a birch wood or a shady clearing**
(`birch forest floor`, `woodland clearing light`, `mossy forest ground`), and use the
**same POV prompt as scene 3**, with the rock paragraph swapped for this:

```
THE ROCK: directly in front of me, close to the camera, filling the lower part of the frame
and running off the bottom edge. One low flat mossy stone with a broad flat top being used
as a desk. Damp grey stone with green moss creeping over its edges, worn and old. It sits
heavily in the undergrowth, with leaves and moss pressed against its base and a soft dark
contact shadow beneath it.
```

Keep everything else the same. The forest light is already soft, so the overcast light
paragraph fits as written.

# 1 · Sign in

```
Photograph of a quiet green hillside meadow with a few scattered trees, early morning,
low side light from the left, long soft shadows across dry gold grass. Shot on 35 mm
film, 50 mm lens, f/8, natural colour, fine grain. Warm muted palette of mossy green and
pale gold. Wide empty sky filling the upper half, calm uncluttered ground in the lower
third for text. No people, no buildings, no paths. Vertical, --ar 9:19.5
```

Search words for a real photo: `green hillside morning`, `meadow golden hour`,
`rolling hills soft light`.

---

# 2 · Payment

```
Photograph of a wide calm valley at dusk, warm low sun behind distant hills, deep green
shadow across the foreground. Shot on 35 mm film, 85 mm lens, f/5.6, soft natural
contrast, fine grain. Mostly shadow with one quiet band of warm light near the horizon.
Muted, still, unspectacular. Large calm area in the lower half for text. No people, no
buildings. Vertical, --ar 9:19.5
```

Search words: `valley dusk`, `hills sunset calm`, `evening field soft light`.

---

# 5 · Account / Profile

```
Photograph of a calm treeline above an open field under a soft sky, midday, gentle even
light, no drama. Shot on 35 mm film, 50 mm lens, f/8, natural colour, fine grain. Simple
and uncluttered, with a large quiet area across the middle and lower frame. No people, no
buildings. Vertical, --ar 9:19.5
```

This one gets **blurred and darkened** in the app, so simple is better than interesting.

Search words: `treeline field`, `open meadow sky`, `quiet countryside`.

---

# 6 · The living scene (he lives here)

Generate the full frame first, then cut it into layers.

```
Photograph of a small quiet clearing: a large old tree standing on the left, a flat
sitting rock in the middle distance, open grass between them, gentle hills and soft sky
behind. Late afternoon light from the left, long shadows across the grass. Shot on 35 mm
film, 35 mm lens, f/8, deep focus, natural colour, fine grain. Calm and uncluttered, with
generous open ground in the centre of the frame. No people, no paths, no buildings.
Vertical, --ar 9:19.5
```

Also make a **night version** of the same clearing (for the "Quiet" mode) — same
composition, moonlit and deeply dark:

```
…the same clearing at night, faint moonlight from the left, deep shadow, almost
monochrome dark green, a little starlight in the sky, very quiet…
```

### Then cut it into 5 layers

Save each as a **transparent PNG on the same canvas size**, back to front:

1. `sky` — sky and light
2. `far` — distant hills / treeline
3. `tree` — the tree the orb passes **behind**
4. `rock` — the rock it **sits on** (top edge must read as a surface)
5. `fore` — foreground grass the orb passes **behind**

Cut each one out, then use generative fill to paint what was hidden behind it. Keep
detail modest near the cuts — parallax moves these a few pixels and over-detail gives the
cut away.

---

## Before you use any image

Zoom to **100 %** and reject it if you see: shadows going different ways · no true black
anywhere · melted feather, nib, or bottle rim · repeating grass or clouds · plastic shine
· dead-centred symmetry · anything that looks written on. Full checklist in
`IMAGERY-BRIEF.md`.
