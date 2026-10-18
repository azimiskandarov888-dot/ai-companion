# Bob — the world, in two versions

The owner's references (2026-10-18): **Ghost of Tsushima** and **The Last of Us**
main menus (realistic, cinematic nature: wind, light, fog), and **Studio Ghibli
backgrounds** (painted countryside). Not cartoon, not cute.

One place, four times of day, two styles. **He is not in the pictures.** The app
draws his light on top, so every frame leaves him room.

## The place (same in both versions)

A wide hillside meadow above a valley: tall grass and wildflowers moving in the
wind, one old tree on the right, hills and far mountains, a big sky. Far away,
a small wooden house with one window.

**Composition (portrait phone screen, 9:16):**
- Upper 40 %: mostly sky, quiet — the title text goes here.
- Middle: open meadow around the centre, a little below the middle — his light
  goes here, so keep it clear.
- Bottom 20 %: darker foreground grass — the buttons go here.
- No people, no animals in the foreground, no text, no logos.

## Times of day

| Scene | Used for | What changes |
|---|---|---|
| morning | sign-in | first light, low mist in the valley, dew, pale peach-blue sky |
| day | his screen | soft bright light, high clouds, wind in the grass, a few petals in the air |
| evening | his screen | golden hour, long shadows, warm light through the grass, falling leaves |
| night | his screen | moonlight, stars, fireflies over the grass, the far window glowing warm |

## Version 1 — Cinematic (Ghost of Tsushima, The Last of Us)

**Style:** a still from the main menu of a big open-world game. Photoreal with
painterly colour grading, volumetric light, atmospheric haze, shallow depth of
field, subtle 35 mm film grain, rich but muted colours. Quiet, grown-up,
beautiful.

## Version 2 — Painted (Ghibli-like)

**Style:** hand-painted background art from a classic Japanese animated film.
Gouache and watercolour, visible brush texture, lush greens, towering soft
cumulus clouds, warm nostalgic light, detailed but painterly.

---

## Midjourney (paste each line into midjourney.com)

Pick your favourite of each four, upscale it, download it, and send it to me
(or drop it into `ios/design/versions/mj/` with the name in brackets).

**Cinematic**

- (cinematic-morning) `cinematic still from an open-world video game main menu, wide hillside meadow above a misty valley at dawn, tall grass and wildflowers wet with dew, one old tree on the right, far mountains, pale peach and blue sky, low mist, volumetric morning light, atmospheric haze, shallow depth of field, photoreal with painterly colour grading, 35mm film grain, quiet and empty upper sky, no people, no text --ar 9:16 --style raw --s 200`
- (cinematic-day) `cinematic still from an open-world video game main menu, wide hillside meadow on a soft bright day, tall grass and wildflowers bending in the wind, a few petals in the air, one old tree on the right, hills and far mountains, high clouds, open meadow in the centre, photoreal with painterly colour grading, atmospheric haze, 35mm film grain, no people, no text --ar 9:16 --style raw --s 200`
- (cinematic-evening) `cinematic still from an open-world video game main menu, wide hillside meadow at golden hour, warm sunlight through tall pampas grass, long shadows, falling autumn leaves in the wind, one old tree on the right, far mountains, glowing sky, volumetric light, photoreal with painterly colour grading, 35mm film grain, no people, no text --ar 9:16 --style raw --s 200`
- (cinematic-night) `cinematic still from an open-world video game main menu, wide hillside meadow at night under a bright moon, stars, fireflies over the tall grass, one old tree on the right, far away a small wooden house with one warm glowing window, cool blue moonlight, atmospheric haze, photoreal with painterly colour grading, 35mm film grain, calm, no people, no text --ar 9:16 --style raw --s 200`

**Painted**

- (painted-morning) `hand-painted anime background art in the style of Studio Ghibli, wide green hillside meadow above a misty valley at dawn, dew on the grass and wildflowers, one old tree on the right, far mountains, pale peach and blue sky, gouache and watercolour, visible brush texture, warm nostalgic light, quiet open sky, no people, no text --ar 9:16 --s 400`
- (painted-day) `hand-painted anime background art in the style of Studio Ghibli, wide green hillside meadow on a summer day, tall grass and wildflowers in the wind, towering soft cumulus clouds, one old tree on the right, hills and far mountains, gouache and watercolour, visible brush texture, open meadow in the centre, no people, no text --ar 9:16 --s 400`
- (painted-evening) `hand-painted anime background art in the style of Studio Ghibli, wide hillside meadow at golden hour, warm orange light through the grass, long shadows, leaves drifting in the wind, one old tree on the right, glowing clouds, gouache and watercolour, visible brush texture, no people, no text --ar 9:16 --s 400`
- (painted-night) `hand-painted anime background art in the style of Studio Ghibli, hillside meadow at night under a big moon, stars, fireflies over the grass, one old tree on the right, far away a small wooden house with one warm glowing window, deep blue night, gouache and watercolour, visible brush texture, calm, no people, no text --ar 9:16 --s 400`

---

## Gemini (Nano Banana Pro) — run by `versions/make_versions.py`

The same scenes, written for Gemini, which follows plain descriptions better
than tags and is not asked to copy a named studio: see the script.

---

## Framing test — frame-1 (after the owner's corrections, 2026-10-18)

AI pictures look AI because they cram everything into one frame. Films and
games **frame**: one subject, cropped by the edges, the world going on beyond.
The place is made **once**; time of day and mood change only light and colour
in the app, and the near grass is live, so it moves with the wind and with him.

- Gemini (Nano Banana Pro): `framing/frame-1.prompt.txt` → `framing/frame-1.jpg`
- Midjourney: `cinematic film still, 50mm lens, eye level inside a field of tall pampas grass on a hillside, late afternoon warm side light, nearest blades soft and out of focus along the bottom edge, focus on the grass a few metres away, beyond the slope only haze and the faint line of far hills, open calm sky in the upper half, no sun in frame, no tree, no house, no flowers, no people, the field continues beyond the frame, restrained natural composition, muted colours, shallow depth of field, gentle film grain --ar 9:16 --style raw --s 100`

## Framing test — frame-2: a little further (owner: "the idea is perfect, but super close up")

- Gemini: the SAME picture (frame-1) pulled back a few steps by image editing, so the place stays the same —
  `framing/frame-2.prompt.txt` → `framing/frame-2.jpg`
- Midjourney: `cinematic film still, 35mm lens, standing eye level a few steps back from the edge of a field of tall pampas grass on a hillside, late afternoon warm side light, the grass fills the lower half of the frame, more of the slope and a hazy valley visible below, faint line of far hills, open calm sky in the upper half, no sun in frame, no tree, no house, no people, the field continues beyond the frame, restrained natural composition, muted colours, gentle film grain --ar 9:16 --style raw --s 100`

## Framing test — frame-3: a wide shot with a key subject (owner: "nothing on the screen, no key thing — like the katana in Ghost of Tsushima; further back; cinematography ratios")

- Gemini: a new composition with frame-2 as the reference for light, colour and film look —
  `framing/frame-3.prompt.txt` → `framing/frame-3.jpg`
- Midjourney: `cinematic wide shot, 35mm lens, standing eye level about thirty metres away, a single old wind-shaped tree with amber autumn leaves alone on the crest of a hillside of tall pampas grass, tree trunk on the right third line, crown near the upper right third intersection, branches leaning left in the wind, a few leaves drifting, the slope rising as a gentle diagonal from lower left to the tree, hazy valley and layered far hills behind, open calm sky in the upper left as negative space, late afternoon warm back light, rim light on the leaves and grass tips, no sun in frame, only the very bottom edge softly out of focus, no house, no path, no people, the hillside continues beyond the frame, restrained deliberate composition, muted natural colours, gentle film grain --ar 9:16 --style raw --s 100`

## Framing test — frame-4: flat ground, a full tree, on the left (owner: "it's good; try flat ground, a better tree — this one is naked — on the left")

- Gemini: a new composition with frame-3 as the reference for light, colour and film look —
  `framing/frame-4.prompt.txt` → `framing/frame-4.jpg`
- Midjourney: `cinematic wide shot, 35mm lens, standing eye level about forty metres away across a flat open field of tall pampas grass and meadow grass, a single magnificent old tree with a full broad rounded crown of dense amber and golden autumn leaves on a thick characterful trunk, tree on the left third line, crown around the upper left third intersection, a few leaves drifting to the right in the wind, low flat horizon a little below the middle, layered far hills fading into haze, open calm sky on the right as negative space, late afternoon warm back light, soft rim light on the leaves and grass tips, no sun in frame, only the very bottom edge softly out of focus, no house, no path, no people, the field continues beyond the frame, restrained deliberate composition, muted natural colours, gentle film grain --ar 9:16 --style raw --s 100`

## Framing test — frame-5 (Midjourney only): the tree belongs to the land (owner: "framing and distance all good; the tree looks super alone, like it was put there on purpose — uncanny in nature")

The tree is the closest and largest of several (smaller trees, shrubs, an uneven tree line), grass grows up to
its trunk, and the left edge of the frame cuts some of its branches. Negatives go in `--no`, never in the
prompt: Midjourney reads "no house" as "house".

`cinematic wide shot, 35mm lens, standing eye level about forty metres away, a flat open field of tall pampas grass and meadow grass in late autumn, a large old tree with a full broad crown of dense amber and golden leaves stands on the left third of the frame, some of its outer branches cut off by the left edge of the frame, tall grass growing right up to its trunk with fallen leaves among it, a few smaller trees and low shrubs scattered through the middle distance, a soft uneven tree line along the far edge of the field, the big tree is simply the closest and largest of them, low flat horizon a little below the middle, layered far hills fading into haze, open calm sky on the right, late afternoon warm back light, soft rim light on the leaves and grass tips, a few leaves drifting to the right in the wind, only the very bottom edge softly out of focus, natural and unstaged, muted natural colours, gentle film grain --ar 9:16 --style raw --stylize 100 --chaos 10 --no house, path, fence, people, animals, sun, text, watermark`

Settings: newest version · Raw · 9:16 · Stylization 100 · Variety 10 · Weirdness 0 · Personalize off · Fast.
Optional: `framing/frame-4.jpg` as a Style reference. Then Upscale (Subtle).
