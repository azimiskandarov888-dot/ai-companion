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

## Framing test — frame-6 (Midjourney): Ghost of Tsushima grass, rocks instead of the tree (owner: "the grass is super thin, like hair; I want it beautiful, like in Ghost of Tsushima; the tree is too big and fluffy, and alone again — maybe a rock, but not alone")

Ghost of Tsushima's fields: mostly susuki (Japanese silver grass) — thick clumps, broad arching blades, feathery
silver-gold plumes — and whole fields of flowers (red spider lilies, white and pink). Stylize raised 100 → 200.

`cinematic wide shot, 35mm lens, standing eye level about forty metres away, landscape in the style of Ghost of Tsushima, a flat open field of lush Japanese silver grass in thick clumps with broad arching blades and soft feathery silver-gold plumes, drifts of red spider lilies and small white wildflowers in patches through the grass, long waves of wind moving across the field, a natural cluster of weathered granite boulders on the left third of the frame, one larger rock with smaller ones half sunk into the ground beside it, moss and lichen on the stone, grass and flowers growing between the rocks, more scattered rocks and a few low trees in the middle distance, an uneven tree line along the far edge of the field, low flat horizon a little below the middle, layered far hills fading into haze, open calm sky on the right, late afternoon warm back light, rim light on the plumes and petals, a few petals and seeds drifting in the wind, only the very bottom edge softly out of focus, natural and unstaged, rich but muted colours, gentle film grain --ar 9:16 --style raw --stylize 200 --chaos 10 --no house, path, fence, people, animals, sun, text, watermark, statue, shrine`
- Gemini: the same frame from Nano Banana Pro, frame-4 as the reference for framing and light —
  `framing/frame-6.prompt.txt` → `framing/frame-6.jpg`. Came out rich (susuki, spider lilies, mossy rocks
  among more rocks and low trees), but the horizon is higher than asked and a blurred stone lies along the
  bottom edge.

## Framing test — frame-9 (Midjourney only): low camera looking UP, the tree closer (owner: "the camera is still looking down, I want it to look upward; the tree looks way further than it needs to be; overall beautiful")

`cinematic film still, low-angle shot, camera 30 cm above the ground tilted upward, looking up through tall Japanese silver grass with soft white glowing plumes, nearest plumes out of focus in the foreground rising into the frame, an old tree with an irregular amber-gold crown about 8 metres away on the left third, its branches reaching across the upper left against the sky, a few shrubs and small trees beside it, low horizon near the bottom third, wide open calm sky, late afternoon backlight, rim light on the plumes and leaves, a few leaves drifting, photorealistic, shot on ARRI Alexa, 35mm, natural colour, film grain --ar 9:16 --style raw --stylize 200 --chaos 10 --no house, people, animals, sun, text`

## Framing test — frame-10 (Midjourney only): camera at waist height, slightly up, the TREE in focus (owner: "super, super low; the closest grass is in focus and the tree is out of focus")

`cinematic film still, camera at waist height about 1 metre above the ground, tilted slightly upward, 35mm lens at f/8, sharp focus on the tree, an old tree with an irregular amber-gold crown about 8 metres away on the left third, crisp detailed leaves and bark, a field of Japanese silver grass with soft white glowing plumes around it, only the very nearest plumes at the bottom edge gently soft, a few shrubs and small trees beside the tree, low horizon, wide open calm sky, late afternoon backlight, rim light on the plumes and leaves, a few leaves drifting, photorealistic, shot on ARRI Alexa, natural colour, film grain --ar 9:16 --style raw --stylize 200 --chaos 10 --no house, people, animals, sun, text, macro, bokeh foreground`

## Framing test — frame-11 (Midjourney only): tree off-centre and closer, one continuous field (owner: "the tree is centered and still too far; the foreground grass is made differently from the middle and background, with an empty space in between")

`cinematic film still, asymmetrical off-center composition, an old tree with an irregular amber-gold crown stands on the left side of the frame about 4 metres from the camera, its crown cropped by the top left edge, the right two thirds of the frame open sky and grass, camera at waist height tilted slightly upward, 35mm lens at f/8, sharp focus on the tree, one continuous dense field of the same Japanese silver grass with soft white glowing plumes running unbroken from the bottom edge to the tree and on to the horizon, low horizon, calm sky, late afternoon backlight, rim light on the plumes and leaves, a few leaves drifting, photorealistic, shot on ARRI Alexa, natural colour, film grain --ar 9:16 --style raw --stylize 200 --chaos 10 --no house, people, animals, sun, text, centered composition, symmetry, gap, empty foreground, macro`

## Midjourney result — mj-11 (owner: "almost perfect; the tree is still too far and needs to be closer; the camera a little, just a little bit up")

`framing/mj-11.webp` — huge old amber tree on the left, a field of white silver-grass plumes, deep blue sky, low green hills.

Next prompt (with mj-11 dragged in as an Image prompt):
`cinematic film still, an enormous old tree with an amber-gold autumn crown about 3 metres from the camera, its thick gnarled trunk large on the left edge of the frame, the crown spreading across the top of the frame, falling leaves drifting right, camera at chest height about 1.3 metres tilted slightly upward, sharp focus on the tree, one continuous field of white silver grass plumes running to low green hills, deep blue clear sky on the right, warm low sunlight, photorealistic, shot on ARRI Alexa, 35mm, natural colour, film grain --ar 9:16 --style raw --stylize 200 --iw 1.5 --no house, people, animals, sun, text, centered composition, gap`

## Midjourney — mj-12 prompt: split with `::` so colours don't leak (owner: "the grass is blurred, the tree is still too far, and the orange leaves made the grass orange")

`::` makes Midjourney treat each part separately, so "amber leaves" stays on the tree. No blur words at all.

`cinematic film still, photorealistic, shot on ARRI Alexa, 35mm, camera at chest height, deep focus, everything sharp:: a field of pure white silver grass plumes with green stems, crisp and detailed, filling the bottom half of the frame::2 an enormous old tree two metres from the camera on the left edge, thick gnarled trunk, crown of amber autumn leaves cropped by the top of the frame::1.5 clear deep blue sky and low green hills on the right::1 --ar 9:16 --style raw --stylize 150 --no orange grass, blur, bokeh, shallow depth of field, centered composition, house, people, text`
