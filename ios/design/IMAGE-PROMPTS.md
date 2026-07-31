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

**You are sitting on the ground, writing on an open scroll that lies on a flat rock right
in front of you.** The scroll fills about **half the frame**. The landscape is just
background — what matters is that you can clearly see the page you are writing on. No
hands, no person in shot.

---

### 🚫 Why editing a real photo CANNOT work for this one

This isn't a prompt problem — it's geometry, and no wording gets around it.

Your meadow photo was taken **standing up, with a long lens, focused hundreds of metres
away**. What we need is an object **half a metre from the lens, filling half the frame**.
Those are two completely different cameras.

To put a near object into a far frame, the model has to rebuild the perspective, the
scale, and the depth of field of the entire picture — which is exactly what it did when it
"regenerated the scenery." It wasn't disobeying you. You asked it for something that can
only exist in a different photograph.

**So: generate this one from scratch.** You were right.

**Keep your meadow photo** — it's beautiful and it works perfectly as the **Sign-in** image
or the **Living scene**, where nothing has to sit close to the camera.

---

### The method: generate a new frame, using your photo as the look

Don't just generate blind — **attach your meadow photo as a colour/light reference** so the
new scene belongs to the same world as the rest of the set.

- **Google Gemini (Nano Banana Pro):** attach your photo, then paste the prompt below, and
  add at the end: *"Match the colour, light, mood and grain of the attached photograph."*
- **Midjourney:** paste your photo's URL at the start of the prompt as an image prompt (or
  use `--sref <url>`), then the text, then the parameters.
- Whichever you use: ask for the **highest resolution available** (4K).

---

### The prompt (precise — every number matters)

```
A photograph taken from the point of view of a person sitting on the ground and writing.

CAMERA: full-frame camera held at seated eye level, about 100 cm above the ground, tilted
downward roughly 40 degrees toward a flat rock directly in front of the viewer. 24 mm wide
lens, f/5.6, focused on the centre of the scroll, which is about 50 cm from the lens.
Vertical portrait frame.

FRAMING, EXACTLY: the rock and the open scroll fill the LOWER HALF of the picture — about
55 % of the frame height. The scroll is so close that its near edge is cut off by the
bottom edge of the frame, and it extends past both the left and right edges. Above the
rock: a band of green grass, then low green hills, then a narrow strip of sky in the top
tenth. The horizon sits about four fifths of the way up the frame. The scroll is the
subject; the landscape is only background.

THE SCROLL, ORIENTATION: it lies open and FLAT on the rock, SQUARE to the viewer — its
long axis runs horizontally, parallel to the bottom edge of the frame, with one wooden
roller at the left and one at the right. It is NOT turned sideways, NOT rotated, NOT
diagonal, NOT seen from its end. It faces the viewer exactly as a sheet of paper faces
someone about to write on it. Because the camera looks down at it from close range, it is
strongly foreshortened: the near edge is wide and low in the frame, the far edge clearly
narrower.

THE SCROLL, DETAIL: a fine scroll wound on two turned wooden rollers, one at each end, the
open sheet held flat between them; the rods are dark polished wood with small aged brass
end-caps, and the far roller still has a little of the scroll wound around it. A thin
leather cord lies loose beside it. The parchment is soft grey-cream, thick, with visible
fibres, faint age spots and a gentle curl at the edges — elegant and well kept, not burnt,
not torn, not crumpled. It is large and clearly visible, filling most of the lower half of
the frame. ABSOLUTELY NOTHING is written, drawn, printed or marked on it — the surface is
completely blank.

THE ROCK: one low granite boulder with a broad, roughly flat top being used as a desk.
Grey-brown stone, worn rounded edges, patches of lichen, a few natural cracks, dry dust in
the hollows. Its surface is visible around the scroll, and it sits heavily in the ground
with grass pressed down and darker where it meets the stone.

ALSO ON THE ROCK: a white goose feather quill with a slim dark metal nib lying to the
RIGHT of the scroll, angled naturally as if just set down, and a small heavy glass ink
bottle with dark ink and a worn cork standing on the stone beside it, small enough to fit
in a palm. Each object casts a small soft dark contact shadow where it touches the stone.

NO PEOPLE: absolutely no person, no hands, no arms, no fingers, no body, no legs, no feet
anywhere in the image. The viewer's hands are out of frame.

DEPTH OF FIELD: the scroll and the rock are sharp and clearly detailed. The grass just
beyond falls gently out of focus, and the hills and sky are soft — as a 24 mm lens at f/5.6
focused at half a metre really renders them.

LIGHT: soft, diffuse, overcast midday light with no direct sun — no hard cast shadows
anywhere, only gentle ambient shading and soft contact shadows underneath each object. No
sunlit edges, no bright specular highlights. Cool, muted, low-contrast colour with a slight
atmospheric haze. The parchment is a soft grey-cream at the same muted exposure as the rest
of the frame, never bright white.

Shot on 35 mm film, natural colour, fine grain. Quiet, ordinary, understated — an
unremarkable real photograph, not a product shot.
```

**Midjourney parameters** to add on the end:

```
--ar 9:19 --style raw --no HDR, oversaturated, glowing, bloom, haze, lens flare, god rays,
symmetrical, plastic, waxy, glossy, hyperdetailed, fantasy, magical, glowing particles,
text, letters, writing, watermark, logo, heavy vignette, tilt-shift, oversharpened,
cartoon, 3d render, cgi, illustration, people, hands, fingers
```

*(`9:19` is the closest ratio Midjourney accepts to a phone screen; crop to 1290 × 2796 after.)*

---

### Judging the results

Make **4**, then check in this order:

1. **Is the scroll square to you?** Rollers left and right, long axis flat across the
   frame, page facing you like paper on a desk. If it's turned, angled, or seen end-on —
   that's the "someone photographed it" look. Reject.
2. **Does it fill about half the frame,** with its near edge cut off at the bottom? If it's
   small or sitting in the middle distance, reject.
3. **Can you see the parchment clearly** — texture, fibres, enough room that you could
   write a paragraph on it? That's the whole point of the screen.
4. **No hands, no people.** Regenerate if any appear; never try to fix hands.
5. **Nothing written on it.** These models love inventing letters. Zoom in.
6. **Contact shadows** under the scroll, rollers, quill and bottle — or everything floats.
7. **Is the parchment glowing white?** In a muted frame that's the biggest tell.

### Fixing without starting over

Re-run with the same seed / "keep this image but…" and one instruction:

> Keep everything exactly as it is. Only turn the scroll so it lies square to the viewer,
> its long axis horizontal, one roller at the left and one at the right, facing me like a
> sheet of paper I am about to write on.

> Keep everything exactly as it is. Only move the rock and scroll closer to the camera and
> make them larger, so the scroll fills the lower half of the frame and its near edge runs
> off the bottom edge.

> Keep everything exactly as it is. Only remove all writing from the parchment so it is
> completely blank.

---

# 4 · The second scene

The **same seated writing view**, in a clearly different place — cooler, shadier, quieter.
Also generated, not edited, for the same reason.

Use the **whole prompt from scene 3**, with two paragraphs swapped:

```
THE ROCK: one low flat mossy stone with a broad flat top being used as a desk. Damp grey
stone with green moss creeping over its edges, worn and old. It sits heavily in the
undergrowth, with leaves and moss pressed against its base.
```

```
FRAMING, EXACTLY: … Above the rock: a band of forest floor and low undergrowth, then the
pale trunks of birch trees, then soft grey-green light between them. No open sky.
```

Keep the light paragraph as written — forest light is already soft and shadowless.

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
