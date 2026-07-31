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

### Best way — build it in two steps on a real landscape photo (recommended)

**You will almost never find a photo of a table-like rock. Don't hunt for one — add the
rock yourself.** Keep the *landscape* real (grass, trees, depth and light are the hardest
things to fake) and let AI make only the rock and the objects. A rock is the safest thing
to generate: it has no "correct" shape, so nobody can say it's wrong.

**Do it as two separate edits, not one.** Asking for rock + scroll + quill + ink in a
single prompt produces mush. Add the rock, check it, *then* add the objects.

---

#### Step A — add the rock

1. Download a real photo: an **open meadow or field shot from a low angle**, with grass in
   the foreground and trees/hills/sky behind. (unsplash / pexels: `meadow low angle`,
   `grass field close up horizon`, `wild grass hillside`)
2. Select an area in the **lower part of the frame**, close to the camera. Let it run off
   the **bottom edge** — a rock cropped by the frame reads as near and real, and there's
   less of it to get wrong.
3. Paste this:

```
Add a large flat weathered rock here in the foreground, close to the camera, its broad
flat top facing up like a low natural table. Rough grey-brown granite with lichen
patches, worn rounded edges, a few natural cracks and dry dust. It sits solidly and
heavily in the grass, with the grass pressed down and darker where it meets the stone.
Match the photograph exactly: same sun direction, same shadow length and softness, same
grain, same focus. Photorealistic, plain and unremarkable — not sculpted, not polished,
not symmetrical, not a monument.
```

4. **Check the rock before going on:** does its shadow point the same way as the other
   shadows? Is there a dark contact shadow where it meets the grass? Does grass overlap
   its base, rather than the rock sitting on top like a sticker? Is it a bit rough and
   dirty (good) rather than smooth and clean (bad)?

*If the AI struggles, try again on a simpler photo — plain grass with a soft background is
much easier for it than a busy scene.*

---

#### Step B — add the scroll, quill, and ink

Now select the **flat top of your new rock** and paste this:

```
Add an old parchment scroll lying unrolled flat on the top of this rock, its far end
still loosely rolled. Beside it, a fine white goose feather quill with a slim polished
metal nib resting across the stone, and a small heavy glass ink bottle with dark ink and
a worn cork. The parchment is soft cream, thick and slightly translucent at the edges,
with gentle natural curl, fine fibres, faint age spots and a few soft creases — clean
and elegant, not burnt, not torn, not crumpled. Nothing is written on it. Everything sits
flat and stable on the stone with real weight and contact shadows. Match the photograph
exactly: same sun direction, same shadow length and softness, same grain, same focus
falloff. Photorealistic, natural, slightly dusty, understated.
```

Generate 4 versions. **Keep the one whose shadows fall the same way as the rock's own
shadow.** Then zoom to 100 % and check the feather barbs, the nib, and the rim of the
ink bottle are not melted.

---

#### If you'd still rather find a real rock

These search words work better than "flat rock" (which mostly returns big round
boulders): `stone slab`, `rock ledge`, `flat rocks river`, `slate shore`, `stepping
stone`, `granite outcrop`, `dolmen` (a natural stone table), `stone bench garden`. Photos
of people sitting on flat rocks work too — crop the people out.

But don't spend hours on it. Adding the rock takes ten minutes and gives you exactly the
shape and angle you want.

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

Same two steps. Start from a real photo of the **edge of a birch wood or a shady
clearing** (`birch forest floor`, `woodland clearing light`, `mossy forest ground`), then
add the rock with this variation:

```
Add a low flat mossy stone here in the foreground, close to the camera, its broad flat
top facing up like a low natural table. Damp grey stone with green moss creeping over its
edges, worn and old. It sits heavily in the undergrowth, with leaves and moss pressed
against its base and a soft dark contact shadow. Match the photograph exactly: same light
direction, same soft shadows, same grain, same focus. Photorealistic, plain, unremarkable.
```

Then add the scroll, quill, and ink with the **same prompt as step B above**.

Fallback:

```
Photograph from a low seated angle at a flat mossy stone at the edge of a birch wood,
camera near stone level so the trees and soft grey-green light open up behind. On the
stone lies an unrolled parchment scroll with a fine white feather quill and a small glass
ink bottle beside it. Soft overcast light, gentle shadows, damp green moss, cool and
quiet. Shot on 35 mm film, 35 mm lens, f/5.6, natural colour, fine grain. Nothing written
on the parchment. Empty space above. Vertical, --ar 9:19.5
```

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
