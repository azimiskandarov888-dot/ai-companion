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
