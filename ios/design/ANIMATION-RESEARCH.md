# Making his field move — what can actually do it (research, 2026-10-18)

The problem with every video AI so far (Veo, Midjourney): it **redraws** each
frame from imagination, with no physics — plumes move separately (good) but in
random directions, leaves appear from nowhere, the tree stands still. Two real
ways out:

- **A. A video AI where *you* tell each part how to move** (direction, what stays still).
- **B. Split the picture into separate pieces** (grass clumps, branches, crown,
  sky) and move them ourselves in the app, with one wind.

---

## A. Video AIs with real motion control

| Tool | Control | Verdict |
|---|---|---|
| **Kling (3.0)** — Motion Brush | Paint up to **6 regions**, draw an **arrow** for each (its direction and length = where it ends up), and a **Static Brush** that freezes areas (trunk, sky). Start/end frames. | **The one to test.** It is exactly "the grass goes right, the branches a little right, the trunk stays". A free tier with daily credits is reported. |
| Runway | Motion Brush **no longer exists** — it was Gen-2 only, removed in 2025; newer models are prompt-only. | ✗ |
| Luma (Ray 3.x) | Start/end keyframes, loop. No region control. | ~ like Veo |
| Veo 3.1, Omni Flash, Midjourney, Seedance, Hailuo, PixVerse | Text only. | Same lottery as before |
| **Wan-Move** (Alibaba, open source, NeurIPS 2025) | Point **trajectories** you draw on the image; claims control on par with Kling's Motion Brush. 832×480, 5 s. | Free, but needs a strong GPU / ComfyUI — a later option |
| Cinemagraph apps (Motionleap etc.) | Arrows + anchors, but they **warp** the picture | ✗ — the "rubber" look we already saw |

**How to use Kling's Motion Brush on our picture** (image-to-video):
1. Upload our picture (the leaf-free one, `wind/base.jpg`, or the new Midjourney one).
2. **Static Brush** over the trunk and the open sky — they must not move.
3. Motion brush **1–3: grass**, one connected patch each (near, middle, far); arrow **short, to the right** — longer for the near patch.
4. Motion brush **4: the crown**; arrow **very short, to the right**.
5. **Don't brush any leaves.** (Falling leaves come later, from code, starting on the crown.)
6. Prompt: `steady gentle wind from the left, the grass and the branches lean to the right`
7. If there is an end frame option, put the same picture there → a loop.

**Limit of all of A:** it is still a **video** — it can't react to touch or to
him walking through the grass, and every change of mood or time is a new paid clip.

---

## B. Split the picture, animate the pieces ourselves

### B1. AIs that split one picture into pieces

| Tool | What it gives | Notes |
|---|---|---|
| **Qwen-Image-Layered** (Alibaba, Dec 2025, open, Apache 2.0) | The picture as **2–8 separate RGBA layers** (sky, tree, field…) — and any layer can be split again | On Replicate/fal (pay per run, cents) or ComfyUI locally |
| **SAM 3** (Meta, Nov 2025, open) | Type a phrase — "grass plume" — and it cuts out **every** matching instance | Each near plume as its own cut-out piece. Runs locally or on Replicate/fal |
| Inpainting (Photoshop Generative Fill, Midjourney Editor, Nano Banana) | Fills what was **behind** a cut-out piece | Needed once, so moving pieces never reveal holes |
| Image → 3D tree | Nothing good: no AI turns a photo into a wind-ready 3D tree | Real 3D trees come from artists (SpeedTree) |

### B2. Moving the pieces

| Tool | How | For us |
|---|---|---|
| **Our own code in the app** (SpriteKit / Metal shaders, Apple, free) | Each plume rotates around **its own base**; each branch around its joint; one wind drives all; touch parts the grass; leaves fall from the crown | **Recommended** — full logic, interactive, $0 per change, the same maths as `wind.html` but on real separate pieces |
| Rive (has an iOS runtime) | Bones + mesh deformation + a state machine with inputs (wind strength, touch) | Good if a designer rigs it by hand |
| Spine 4.2 | Bones + mesh + **physics constraints** (wind and gravity are settable from code) | Powerful; Pro licence needed for meshes |

**Why B fixes what failed before:** the rubber look came from bending *one*
flat picture. With separate pieces, each plume and branch has its own pivot, so
it can sway on its own — in the **same** direction as the wind, with the **same**
gusts, and react to him.

---

## Recommendation

1. **Now, free:** test **Kling's Motion Brush** with the steps above — the fastest
   way to see directed, logical motion on our exact picture.
2. **For the app:** **B** — split with **Qwen-Image-Layered** (sky, crown,
   trunk, far field, near field) plus **SAM 3** for the near plumes one by one,
   fill behind them, then animate the pieces **in our own code** (one wind,
   touch, leaves from the crown). It's the only way it stays logical,
   interactive and free per change.
3. **What B needs from you:** an account on **Replicate** (or fal.ai) with a card,
   paid by an adult — runs cost cents. (Or I set the models up to run on your
   Mac, which means downloading several GB — I'd ask first.)

---

**Sources:** Kling Motion Brush — [kling.ai quickstart](https://kling.ai/quickstart/how-to-animate-image-parts),
[Kling 3.0 review](https://www.atlascloud.ai/blog/kling-3.0-review-features-pricing-ai-alternatives) ·
Runway — [Gen-2 deprecation (Motion Brush removed)](https://help.runwayml.com/hc/en-us/articles/41072248471187-Gen-2-Deprecation),
[Gen-4.5](https://runway.com/research/introducing-runway-gen-4.5) ·
Luma — [Ray3.2 guide](https://runware.ai/docs/models/luma-ray3-2/guides/generating-video) ·
Wan-Move — [paper](https://arxiv.org/html/2512.08765v1), [ComfyUI](https://docs.comfy.org/tutorials/video/wan/wan-move) ·
Qwen-Image-Layered — [GitHub](https://github.com/QwenLM/Qwen-Image-Layered), [Replicate](https://replicate.com/qwen/qwen-image-layered), [paper](https://arxiv.org/pdf/2512.15603) ·
SAM 3 — [GitHub](https://github.com/facebookresearch/sam3), [Ultralytics docs](https://docs.ultralytics.com/models/sam-3) ·
Rive — [Apple runtime](https://rive.app/docs/runtimes/apple) ·
Spine — [4.2 physics](https://us.esotericsoftware.com/blog/Spine-4.2-The-physics-revolution),
[wind/gravity from code](https://de.esotericsoftware.com/forum/d/25363-spine-42-physics-general-questions/19) ·
SpeedTree — [wind workflow](https://docs.unity3d.com/speedtree-modeler/manual/whats-new.html)
