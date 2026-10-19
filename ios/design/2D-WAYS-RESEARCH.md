# Can his place be perfect and still be 2D? (research, 2026-10-19)

The owner, after the living scene (`scene.html`): "much better, but still horrible.
Maybe we can get the same exact visual effect with only 2D. Think of ways very
different from normal thinking."

---

## Why every 2D attempt so far hit a wall

A still picture has **no motion in it**. Every 2D trick — our pieces, sway masks,
flow maps, bones (the tools the best "living wallpaper" artists use too) —
**invents** the motion. Invented motion looks invented: stickers swinging, a field
bending like rubber. That is the wall, not our skill.

**The different thinking:** keep the two things apart.

- **The look** comes from his picture (mj-15), which he loves. It stays 2D.
- **The motion** has to come from **something that really moved**: a real
  physical motion, or a video model that has seen millions of real fields in
  wind. Then it gets applied to his picture.

Every way below is a different answer to "where does real motion come from, and
how does it reach his picture".

---

## The ways, side by side

| # | Way | Looks like his picture | Motion | Reacts to touch / mood | Runs on the phone as | Ready today |
|---|---|---|---|---|---|---|
| 1 | **AI re-render of our own motion draft** | yes (his picture pinned at start and end) | real-looking, and logical, because we direct it | mood: yes (clip sets); touch: overlay only | a video, the lightest thing a phone can play | **yes**, on his Replicate |
| 2 | **Motion learned from a video, put on the still** ("physics textures") | exactly, it *is* the still | real, taken from way 1's video | **yes**: wind strength, pokes from finger and Bob | a still picture plus a small shader | method public (Google, CVPR 2024 best paper); I'd build it |
| 3 | Real filmed footage | only if it's the same place | perfect (it's real) | no | video | footage exists, but not his place |
| 4 | Video AI that takes **wind as input** | yes | real-looking | yes | video | research only (NeurIPS 2025), no public model |
| 5 | Live AI painting (a server repaints every frame) | yes | real-looking | yes | a live stream | yes, but paid every second, needs internet, 720p |
| 6 | Better hand-made 2D (Wallpaper Engine, Live2D) | yes | invented | yes | shader | — this is the wall above |
| 7 | AI keyframes + in-betweens | yes | the whole field moves as one | no | video | yes, but stiff |
| 8 | Real 3D (the last proposal) | has to be rebuilt to match | real physics | yes | 3D engine | yes, lots of work |

---

## 1. AI re-render of our own motion draft — recommended first

**The idea.** We stop asking a video AI to *invent* the motion (Veo, Kling,
Midjourney video: random, illogical). Instead:

1. **Our engine makes a motion draft** of his exact picture. `scene.html` already
   does it: same composition; one wind; gusts travelling left to right; every plume
   on its own stem; the tree swaying from the trunk; leaves leaving the crown.
   The logic is all there. Only the look is fake: stickers, rubber.
2. **A video re-render AI repaints every frame** so the motion looks real, while
   keeping our motion. **His picture is pinned** as the first and the last frame,
   so the look can't drift. These models exist **on his Replicate account today**:

   | Model | Takes | Price |
   |---|---|---|
   | **Runway Aleph 2** (`runwayml/aleph-2`) | video (2–30 s) + up to **5 keyframe pictures** at first / last / any second | $0.336 / s |
   | **Wan 2.7 VideoEdit** (`wan-video/wan-2.7-videoedit`) | video (2–10 s) + a reference picture, up to 1080p | $0.10 / s |
   | **Luma Modify Video** (`luma/modify-video`) | video (≤ 30 s) + an edited first frame; "adhere" keeps the motion closest | ≈ $2 per 5 s at 720p |
   | Topaz / ByteDance upscalers | lift 1080p to the phone's full resolution | cents |

3. **Clips that join on his picture.** Each clip starts and ends at rest, exactly
   on mj-15. The app can then chain clips in any order with no visible cut: a lull,
   a gust, a big gust, a lull. It never plays the same loop twice in a row.
   - **Mood** picks which clips play: sad gets only the soft ones, restless the strong ones.
   - **Time of day:** the same clips re-rendered from relit versions of his picture (AI
     relighting is also on Replicate: IC-Light, Qwen relight), or toned in the app.
4. **On top, from our code:** falling leaves, light and fireflies. They are driven by
   the same wind numbers the draft used, so they always agree with the grass.

**Why it fits "perfect":** every frame is a photoreal repaint of his picture.
The motion is logical, because we directed it. And a video is the lightest thing
an iPhone can show: the video chip does the work, not the graphics chip.

**Limits, said honestly.**
- A finger can't really part grass inside a video. Touch would trigger a gust or
  leaves instead, or way 2 does it.
- About 10–15 MB per 10-second clip, so a full set of clips by light is big. Way 2 fixes that.
- The AI may still add some motion of its own or soften details. **That is what
  the test checks.**

## 2. Motion learned from a video, put on the still ("physics textures")

**The idea.** In 2015 MIT showed that from a short video of a bush or a plant, you
can measure **how every pixel vibrates**, as a few "modes", each with its own
rhythm. After that, the still picture can be made to sway, react to pokes and
settle, **with real physics, forever, never repeating**. In 2024 Google
(*Generative Image Dynamics*, CVPR 2024 best paper) did the same from a single
photo, for trees and flowers in wind. Their page has a **live demo: drag a branch
of a still photo, let go, and it swings back**.

**For us.**
1. Take way 1's best clip of his scene and measure the motion of every pixel
   (OpenCV optical flow, free, on the Mac).
2. Keep the main vibration modes: a few small images.
3. In the app, his still picture sways by those modes. Wind strength (his mood) sets
   how much they move; a finger or Bob passing pokes them nearby, and the grass there
   swings and settles.

**Why it's attractive:** the look is exactly his picture, at every hour (relit
stills share the same motion). The data is tiny, the motion never repeats, it's
interactive, and a tiny shader runs it.
**Limits:** it's best at swaying. A big bend near the camera can stretch a little,
because it is still a warp, though now one that follows each plume and branch.
Google has not released its model. The from-video method (MIT 2015) needs no model,
so I can build it.

## 3. Real filmed footage

Real susuki footage exists (NHK in Kochi, many 4K pampas clips). Its motion is
perfect, because it's real. But it is not his place. Mixing real near grass with
his painted far field tends to look pasted on. **Useful as a motion reference and
for the drafts, not as the scene.**

## 4. Video AI that takes wind as input (Force Prompting)

Brown University and Google DeepMind (NeurIPS 2025) trained a video model to accept
**a wind (strength and angle) or a poke at a point** next to the picture. That is
exactly our controls: mood becomes wind, a finger becomes a poke. **No public model
yet.** It's the future of way 1. Worth watching.

## 5. Live AI painting

Decart's Mirage/Lucy repaints a live video stream at about 20–24 frames a second.
The app would show a crude scene and the AI would repaint it live: fully
interactive, real-looking. Today it is **paid per second for as long as the
screen is on, needs internet, and runs at 720p or less**. Not for Bob's always-on
home yet. Maybe in a year or two, on the phone itself.

## 6. Better hand-made 2D

The best "living wallpaper" tools (Wallpaper Engine's foliage sway and flow maps,
Live2D, Spine bones) are the same family as what we built: motion painted by hand
onto a still. The ceiling is the wall described at the top.

## 7. AI keyframes + in-betweens

An image editor draws a few full-quality poses (grass leaning right, upright,
leaning back), and a frame-interpolation AI (FILM, on Replicate) fills the frames
in between. Every frame looks painted, but the whole field moves as one block,
with no wave running through it. Stiff.

## 8. Real 3D

Kept for comparison: full physics and interaction, but the look must be rebuilt to
match his picture. That is the riskiest part, and the most work.

---

## Recommendation

**Way 1 now, way 2 after it.** Way 1 gives the look and real motion immediately.
Way 2 later turns the same motion into something tiny, endless and touchable.

**The first test (needs his OK for the money):**
1. Render a 5-second motion draft of his scene from `scene.html`: a lull, then a
   gust, then a lull, starting and ending exactly on mj-15. Free, on the Mac.
2. Re-render it with **Wan 2.7** ($0.50) and **Runway Aleph 2** ($1.68), with
   his picture pinned first and last. **About $2.20 in total.**
3. Also apply the measured motion to the still (way 2), for free, to compare.
4. He watches the three side by side on his iPhone and picks.

If neither AI keeps the look and the logic, we have spent $2.20 and know way 1's
ceiling. Then real 3D is the honest answer.

---

**Sources:**
- Motion from video / physics from a photo: [Image-Space Modal Bases (MIT, SIGGRAPH Asia 2015)](https://dspace.mit.edu/handle/1721.1/137568), [Interactive Dynamic Video (article)](https://www.provideocoalition.com/pokemon-go-interactive-dynamic-video/), [Generative Image Dynamics: live demo](https://generative-dynamics.github.io/), [paper](https://arxiv.org/abs/2309.07906), [unofficial code (256 px)](https://github.com/fltwr/generative-image-dynamics)
- Re-render models on Replicate: [Runway Aleph 2](https://replicate.com/runwayml/aleph-2), [Wan 2.7 VideoEdit](https://replicate.com/wan-video/wan-2.7-videoedit), [Luma Modify Video](https://replicate.com/luma/modify-video), [Luma Modify Video guide](https://www.atlascloud.ai/blog/tips/luma-modify-video), [Aleph 2.0](https://runway.com/product/aleph-2)
- Motion transfer and wind as input: [Go-with-the-Flow (CVPR 2025)](https://github.com/Eyeline-Labs/Go-with-the-Flow), [Force Prompting (NeurIPS 2025)](https://arxiv.org/abs/2505.19386)
- Looping: [Video looping with progressive dynamism (Microsoft, patented: US9292956B2)](https://hhoppe.com/proj/videoloops/), [seamless AI loops](https://magichour.ai/blog/how-to-make-seamless-ai-video-loops)
- Live AI painting: [Decart MirageLSD](https://decart.ai/mirage-lsd)
- Hand-made 2D: [Wallpaper Engine foliage sway](https://docs.wallpaperengine.io/en/scene/effects/effect/sway.html)
- Real footage: [NHK susuki clip (Getty)](https://www.gettyimages.in/detail/video/pampas-grass-fluttering-in-the-wind-stock-video-footage/457743106)
- iOS depth from a 2D photo: [Spatial Scene API thread](https://developer.apple.com/forums/thread/787237)
- How Ghost of Tsushima did it: [PlayStation Blog VFX](https://blog.playstation.com/?p=345372)
