# His world, built the way games build it (research, 2026-10-19)

The owner: "have them as separate things, so the code can change colour, wind,
etc. — like in a real game." A video can't do that; a game world can. Two ways
games build a scene like ours, and what each means for an iPhone app.

---

## How games do it (Ghost of Tsushima, and 2D games like Ori)

- **Grass is not a picture.** Ghost of Tsushima generates every blade on the GPU,
  each with its own look and motion, millions of them, animated by shaders
  (Sucker Punch's GDC 2021 talk *Procedural Grass in Ghost of Tsushima*).
- **One wind for everything.** A separate GDC 2021 talk (*Blowing from the West*)
  describes one wind system driving grass, foliage, particles and cloth — the
  same idea as our "one wind": every thing reads the same wind, by its own
  stiffness.
- **2D games do the same with pieces of art.** Each plant/branch is its own
  sprite; a shader sways it **around a pivot at its base**, more at the top
  than at the bottom, with noise so pieces don't move in lockstep; background
  layers move slower than foreground ones for depth (parallax).
- **Time of day and mood** are light and colour, not new art: a sky gradient,
  the sun's colour and angle, a colour grade over everything, fog, particles
  (mist in the morning, fireflies at night). The place stays the same.

---

## Way 1 — 2.5D: our picture, cut into game pieces (recommended)

**What it is.** Keep the beautiful Midjourney picture, but cut it into the
pieces a 2D game would have:

| Piece | How it moves |
|---|---|
| Sky | still; its colours follow the hour and his mood |
| Far field (a band) | barely — distance |
| Middle field | gentle waves |
| **Near grass — each plume its own piece** | sways around **its own base**, strongest; parts around him and your finger |
| **Trunk** | doesn't move |
| **Crown — 3 to 5 big masses** | each sways around where it joins the trunk, a little; its leaves flutter |
| Falling leaves | born on the crown when a gust hits it, carried by the same wind |
| Light layers | morning mist, evening glow, night fireflies |

**How the pieces are made.** SAM 3 cuts every near plume out by itself ("pampas
grass plume"); SAM 3 or Qwen-Image-Layered cuts the trunk, the crown masses and
the field bands; an inpainting step fills what was behind each piece so nothing
shows a hole when it moves.

**Where it runs.** Natively in the app, with Apple's own 2D tools (SpriteKit,
or Metal shaders in SwiftUI). Light on the battery — which matters, because
this screen is on while people talk.

**Why it's the right first way:** it keeps the **exact look you chose** (a real
2D game title screen), and **everything is controlled by code**: wind strength
from his mood, colour from the hour, touch. It's cheap per change (free).

---

## Way 2 — real 3D, like Ghost of Tsushima itself

**What it is.** A real 3D field: GPU grass, 3D trees with wind (SpeedTree-style),
real lighting and a day–night cycle. The camera could even move.

**Engines that can live inside our SwiftUI app:**

| Engine | Notes |
|---|---|
| **Unity** — "Unity as a Library" | Officially supported embedding in an iOS app; huge asset store (mobile grass and tree packs with wind for $5–15); adds app size and battery use |
| **Godot** — SwiftGodotKit | Free and open; can be shown as a view inside SwiftUI; lighter than Unity; fewer ready-made assets |
| Apple RealityKit / Metal | Native; the most work. SceneKit was put in maintenance mode at WWDC 2025 |

**The catch:** it looks like a **game render**, not your photograph, and it
needs artist-made assets (bought packs) plus a lot more work and battery. Our own
code-drawn 3D test looked crude for exactly that reason.

---

## Recommendation

1. **Way 1.** Cut the picture into game pieces and run them in the app with one
   wind, colour by hour and mood, and touch.
2. **First as a browser prototype on your real pieces** (like `wind.html`, but
   with separate pieces instead of one bent picture) — you judge it on your
   iPhone — then the same in the app.
3. **What it needs:** the cutting tools (SAM 3, Qwen-Image-Layered) run on
   **Replicate** — an account with a card, paid by an adult; runs cost cents.
   (The Gemini key can cut too, but rougher.)
4. **Way 2 later**, only if we ever want a moving camera or a walkable world.

---

**Sources:** Ghost of Tsushima — [Procedural Grass (GDC 2021)](https://gdcvault.com/play/1027214/Advanced-Graphics-Summit-Procedural-Grass),
[Blowing from the West (wind, GDC 2021)](https://gdcvault.com/play/1027350/Blowing-from-the-West-Simulating),
[Guiding Wind](https://gdconf.com/news/see-how-ghost-tsushima’s-guiding-wind-came-life-gdc-2021),
[Godot reimplementation](https://github.com/2Retr0/GodotGrass) ·
2D wind sway — [base-pivot shader](https://godotshaders.com/shader/2d-wind-sway-tree-grass-motion-shader-2/),
[foliage wind](https://godotshaders.com/shader/foliage-wind-shader/) ·
Engines — [Unity as a Library](https://docs.unity.com/en-us/engine/6000.0/manual/platform-specific/cross-platform-features/unityasa-library.md),
[Unity in SwiftUI](https://medium.com/@mominaman/unity-as-a-library-swiftui-ios-786c4f58f1d7),
[Godot in iOS apps](https://christianselig.com/2025/05/godot-ios-interop/),
[SceneKit → RealityKit](https://developer.apple.com/documentation/realitykit/bringing-your-scenekit-projects-to-realitykit.md) ·
Assets — [Mobile Tree Bundle](https://marketplace.unity.com/packages/3d/vegetation/trees/mobile-tree-bundle-254384),
[Realistic Grass and Bush Pack](https://assetstore.unity.com/packages/3d/vegetation/plants/realistic-grass-and-bush-pack1-45278) ·
Cutting — [SAM 3](https://github.com/facebookresearch/sam3), [Qwen-Image-Layered](https://github.com/QwenLM/Qwen-Image-Layered)
