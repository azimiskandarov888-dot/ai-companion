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

This is the scene from your reference, corrected: **on a rock, not a wooden table**,
**seen from a low angle so the landscape is visible**, with **a better scroll, a better
quill, and a better ink bottle**.

### Which AI to use for this

| | Tool | Why |
|---|------|-----|
| **1st choice** | **Google Gemini image editing** — the model nicknamed **"Nano Banana"**. In the Gemini app, upload the photo and paste the prompt; pick the **newest / Pro image model** offered. | Best at "change only this, keep everything else." No masking, no skills needed. Free to try. |
| **2nd choice** | **Photoshop → Generative Fill** (Adobe Firefly) | You paint exactly where the rock goes and can hand-fix the seam afterwards. Safest licence for a paid app. Keep the prompt short — its box is small. |
| **Avoid here** | ChatGPT image generation | It tends to redraw the *whole* picture, so your real photo stops being a real photo. |

*Tools move fast — check current pricing and that your plan allows commercial use.*

---

### The one-shot prompt (rock + scroll + quill + ink together)

Doing it in one go is the right instinct: the AI must know the rock's **job** — a table
for the scroll — or it gives you a nice domed boulder you can't put anything on.

**Start from:** a real photo of an **open meadow or field shot from a low angle**, with
grass in the foreground and trees/hills/sky behind. (unsplash / pexels: `meadow low
angle`, `grass field close up horizon`, `wild grass hillside`)

**Before you paste — look at your photo and fill in one thing:** which side the sunlight
comes from. Everything below depends on it.

```
In this photograph, add a large flat weathered rock in the foreground, close to the
camera, being used as a natural table — with an old parchment scroll unrolled across its
flat top.

THE ROCK: one low granite boulder with a broad, roughly flat top, tilted very slightly
toward the camera so the top surface is clearly visible and usable as a table. Grey-brown
stone, worn rounded edges, patches of lichen, a few natural cracks, dry dust in the
hollows. About knee height. It sits heavily in the ground — the grass around its base is
pressed down and darker, and blades of grass overlap the bottom edge of the stone. Let
the rock run off the bottom edge of the frame.

ON THE ROCK: an old parchment scroll lying unrolled flat across the stone, about the size
of a sheet of paper, its far end still loosely rolled. Soft cream parchment, thick, with
fine fibres, faint age spots, and a gentle natural curl at the corners — elegant and
clean, not burnt, not torn, not crumpled. Absolutely nothing written or drawn on it.
Beside it, a white goose feather quill with a slim dark metal nib lying across the stone,
and a small heavy glass ink bottle with dark ink and a worn cork, small enough to fit in
a palm. Each object casts a small, soft, dark contact shadow where it touches the stone,
so they clearly have weight and are truly resting on it.

MATCH THE PHOTOGRAPH EXACTLY: the sunlight comes from [THE LEFT / THE RIGHT / BEHIND THE
CAMERA] — every new shadow must fall the same way, with the same length and the same
softness as the shadows already in the picture. Match the existing colour temperature,
exposure, contrast, film grain, noise, and lens softness. The new objects must carry the
same amount of focus or blur as anything else at their distance in the original photo.

DO NOT change anything else: keep the existing grass, trees, sky, horizon, colours,
brightness, and grain exactly as they are. Do not re-render, re-light, or sharpen the
rest of the image.

Photorealistic, ordinary, understated — as if these objects were simply there when the
photo was taken. No glow, no rim light, no added highlights, no HDR, no extra sharpening,
no text, no watermark; nothing polished, sculpted, or symmetrical.
```

### ☁️ If your photo has soft, overcast, shadowless light

**This is easier, not harder.** Hard sunlight is the difficult case, because every new
shadow has to agree in direction *and* length. With soft light there are no hard shadows
to match — the danger flips: the AI will try to drop a **sunny** rock into your **cloudy**
scene, and that's what gives it away.

So swap the "MATCH THE PHOTOGRAPH" paragraph for this one:

```
MATCH THE PHOTOGRAPH EXACTLY: the light is soft, diffuse, overcast midday light with no
direct sun — so there are NO hard cast shadows anywhere in this image, and there must be
none on the new objects either. Light the rock and the objects evenly and softly from
above, with only gentle ambient shading: a soft dark contact shadow directly underneath
each object where it touches the stone, and a soft darkening in the grass right under the
rock. No long shadows, no sunlit edges, no bright specular highlights. Match the existing
cool, muted, low-contrast colour, the slight atmospheric haze, the film grain, and the
lens softness. The parchment must be a soft grey-cream at the same muted exposure as the
rest of the photo — never bright white. The new objects must carry the same amount of
focus or blur as anything else at their distance in the original photo.
```

**The single biggest tell in a muted photo is a bright white scroll.** Everything else in
the frame is soft and low-contrast; a clean white rectangle will look pasted on even if
the shape is perfect. If it comes out too bright, run a small second pass:
*"Keep everything exactly as it is. Only make the parchment darker and softer, matching
the muted exposure of the rest of the photo."*

---

**Short version** (for Photoshop's Generative Fill box, after masking the lower foreground):

```
large flat weathered granite rock used as a table, an unrolled parchment scroll lying on
its flat top, a white feather quill and a small glass ink bottle beside it, soft contact
shadows, grass overlapping its base, matching the photo's light direction, grain and
focus, photorealistic, nothing written
```

---

### After it generates — the 4 things that give it away

Make **4 versions**, then judge them on this, in order:

1. **Shadow direction.** Does the rock's shadow fall the same way as the shadows already
   in the photo? Wrong direction = delete, no matter how pretty it is.
2. **Contact shadow.** Is there a dark line where the rock meets the ground, and small
   soft shadows under the scroll, quill, and bottle? Without those, everything floats.
3. **Grass over the base.** Do a few blades cross in front of the stone? If the rock's
   outline is clean all the way round, it reads as a sticker.
4. **Sharpness.** Are the new objects exactly as sharp — or as soft — as the real things
   at that distance? AI likes to make its additions too crisp.

Then zoom to **100 %** and check the feather barbs, the nib, and the rim of the ink
bottle are not melted.

### If it comes out messy

- **The whole photo changed** (colours shifted, grass re-drawn) → wrong tool. Use Gemini
  or Photoshop, not a whole-image generator.
- **90 % right, one bad object** → don't start over. Run a second small edit on just that
  spot: *"Keep everything exactly as it is. Only replace the quill with a clean white
  goose feather with a slim dark metal nib, same position, same shadow."*
- **Still mush after several tries** → then split it: add the rock first (saying "broad
  flat top like a table"), check it, and add the objects in a second pass.

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
Photograph taken from a low seated angle at the edge of a large flat weathered rock in an
open meadow, camera close to the stone so the landscape opens up behind it — dry gold
grass, scattered trees, soft hills and sky filling the upper half of the frame. On the
rock lies an old parchment scroll, unrolled flat, its far end loosely rolled; beside it a
fine white goose feather quill with a slim polished metal nib, and a small heavy glass
ink bottle with dark ink and a worn cork. The parchment is soft cream, thick, gently
curled, with fine fibres and faint age marks — elegant and clean, not burnt or torn.
Nothing written on it. Late afternoon side light from the right, long soft shadows across
the stone. Shot on 35 mm film, 35 mm lens, f/5.6, focus on the scroll with the landscape
softening behind, natural colour, fine grain. Quiet, uncluttered, room above the rock.
Vertical, --ar 9:19.5
```

**Reference note:** your example photo is a *flat-lay on wood, shot from directly above*.
We want the opposite camera: **down at the rock's level, landscape behind**, so it feels
like you are sitting there — not looking down at a desk.

---

# 4 · The second scene

Same idea, clearly a **different place** — cooler, quieter, later.

Start from a real photo of the **edge of a birch wood or a shady clearing**
(`birch forest floor`, `woodland clearing light`, `mossy forest ground`), and use the
**same one-shot prompt as scene 3**, with the rock paragraph swapped for this:

```
THE ROCK: one low flat mossy stone with a broad flat top, usable as a low natural table.
Damp grey stone with green moss creeping over its edges, worn and old. It sits heavily in
the undergrowth, with leaves and moss pressed against its base and a soft dark contact
shadow. Let it run off the bottom edge of the frame.
```

Keep everything else in the prompt the same — and change the light line to match the
softer, shadowless forest light of your photo (say *"soft overcast light from above, very
soft shadows"*).

---

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
