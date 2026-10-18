# Midjourney — how to get exactly the picture you want

From Midjourney's own documentation (read 2026-10-18; the current version is
**V8.2**, the default since 24 July 2026). Sources at the end.

---

## 1. How to write a prompt

**Describe the finished picture, like a caption under a film still.** Don't give
instructions ("make the tree closer") — except in the Edit Model (section 4).

**The order that works** (it is how the reference prompt you found is built):

1. **Mood** — "Quiet, vast calm at the edge of the world"
2. **Camera** — "Shot on 12mm ultra-wide lens", "low angle", "eye level", "wide shot", "close-up"
3. **What stays empty** — said as a *thing you want*: "completely clear, open foreground", "the entire sky unobstructed"
4. **The subject, with scale words** — "a small, sparse twisted red maple tree far in the midground"
5. **The ground and the season** — "a misty meadow of silver grass and fallen crimson leaves under morning frost"
6. **One bold shape** — "a colossal smooth white cliff cuts the frame diagonally"
7. **One tiny anchor** — "a tiny warm light, like a distant ember, is the only anchor"
8. **Air** — "swallowed by heavy autumn atmospheric perspective"
9. **One closing feeling** — "a calm, sacred, timeless realm"

**Rules that matter:**

- **Short and clear beats long lists.** Long lists and detailed instructions confuse it. V8.1 and V8.2 hold on to small details better, but a sentence still beats a list.
- **Say what you want, never what you don't.** "No cake" makes a cake appear. Unwanted things go after `--no`: `--no house, people, text`.
- **Strong, specific words.** "Colossal", "enormous", "tiny", "microscopically small" — not "big" and "small". Numbers: "three trees", not "trees".
- **Scale words, not metres.** "Far in the midground", "towering over", "a tiny figure" work; "8 metres away" mostly doesn't.
- **Colour sits next to its thing.** "Crimson leaves", "white grass". A colour said loosely leaks onto everything (that is how the grass went orange).
- **No `::` in V8.** Multi-prompts don't exist in V7 or V8 any more.

---

## 2. The settings (at the end of the prompt, or in ⚙ Settings)

| Setting | What it does | For our main screen |
|---|---|---|
| `--ar 9:16` | shape of the picture | phone screen |
| `--raw` | less of Midjourney's own "prettifying", more of your words | **on** |
| `--stylize 0–1000` | how much of its own taste it adds | **150–300** |
| `--chaos 0–100` | how different the four results are | **5–10** when you know what you want, 30+ to explore |
| `--hd` | 2K picture, no upscale needed (costs 1.3 GPU min instead of 0.8) | for the final one |
| `--no a, b` | things to keep out | `--no house, people, text` |
| `--seed 123` | same randomness → almost the same picture again (99 % in V8) | to make a small change and compare |
| `--weird` | strange, unusual results | **0** |
| Personalize `--p` | your own taste profile | **off**, so the look is the reference's, not yours |

---

## 3. Using pictures: the five slots

Click the **image icon** in the Imagine bar, upload your picture, then drag it
into one of these sections:

| Slot | What it takes from your picture | Use it when |
|---|---|---|
| **Image Prompt** | content, composition, colours — as *inspiration* | "something like this". Then write **the whole scene** in text. Strength: `--iw 0–3` (default 1) |
| **Style Reference** | only the *look*: colours, light, texture, medium — **not** the objects | to make every screen of the app look the same. Strength: `--sw 0–1000` (default 100). The text says only *what* is in the picture |
| **Attach to prompt** (Edit Model) | the actual picture, to change it — or up to 4 things to combine | "bring the tree closer", "make the grass white" — here you **write instructions** |
| **Animate** (Starting Frame) | the first frame of a video | video (section 5) |
| **Describe** — drop the picture *on the bar itself* | Midjourney writes 4 prompts for your picture | to learn the words for a look you love |

**The golden rule:** with Image Prompt and Style Reference, the text describes
the final picture — "detailed portrait of a dog", never "this style but a dog".

---

## 4. Fix a picture instead of re-rolling it — the Edit Model

New in V8.1/V8.2, and it replaced Omni Reference, Character Reference and Retexture.

- Open your picture → under **Creation Actions** click **Quick Edit** → it lands in the Imagine bar → type an **instruction**:
  `move the camera closer to the tree, keep everything else exactly the same --raw`
- **Open Editor** → paint over one area to change only that (inpainting), or extend the picture beyond its edges (outpainting).
- `--raw` makes it follow your words more precisely.
- It keeps the shape of the first picture; add `--ar 9:16` if you want another.

This is what we needed for "the tree is too far": an edit of the good
picture, not a new prompt.

---

## 5. Video

- Open a picture → **Animate Image**: **Auto** (it invents the motion), **Animate Manually** (you write it), **Loop** (ends where it starts).
- Your own picture: drag it into **Animate / Starting Frame**. A **Loop** checkbox and an **Ending Frame** slot appear.
- **Motion prompt: one simple, physical motion.** "A gentle steady wind from the left; the grass and the branches lean to the right." Short.
- `--motion low` — calm, realistic (default). `--motion high` — big camera moves, often glitchy.
- `--raw` — follows your text more, invents less.
- `--loop` — first frame = last frame. `--end` — a different last frame.
- Length: 5 s, extend by 4 s up to 21 s.
- Cost: four videos = 8 GPU minutes (SD). **`--bs 1`** makes just one = 2 minutes.
- HD (720p) needs Standard, Pro or Mega, in Fast mode.
- **Remove from the starting picture whatever shouldn't move** (like the flying leaves) — the video carries on what it sees.

---

## 6. Copying a look you love

1. On **Explore**, open the picture → **Use Prompt** copies its exact prompt; **Use Style** applies its look.
2. Or drop it on the Imagine bar → **Describe** → four prompts.
3. Change only the **content** words. Keep its camera, light, mood and settings.
4. Add the picture as a **Style Reference** to hold the look.

---

## 7. Our recipe for the main screen

1. **Prompt** in the order of section 1, ending with
   `--ar 9:16 --raw --stylize 250 --chaos 5 --hd`
2. **Fix** the best one with **Quick Edit** (Edit Model) — instructions, not a new prompt.
3. **Make every other screen match:** the best picture as a **Style Reference**.
4. **Animate** it: Manual, Low motion, `--raw --loop --bs 1`, one simple motion sentence.

---

**Sources:** [Prompt Basics](https://docs.midjourney.com/hc/en-us/articles/32023408776205-Prompt-Basics) ·
[Image Prompts](https://docs.midjourney.com/hc/en-us/articles/32040250122381-Image-Prompts) ·
[Style Reference](https://docs.midjourney.com/hc/en-us/articles/32180011136653-Style-Reference) ·
[Edit Model](https://docs.midjourney.com/hc/en-us/articles/48495453462797-Edit-Model) ·
[Video](https://docs.midjourney.com/hc/en-us/articles/37460773864589-Video) ·
[Describe](https://docs.midjourney.com/hc/en-us/articles/32497889043981-Describe) ·
[Version](https://docs.midjourney.com/hc/en-us/articles/32199405667853-Version)
