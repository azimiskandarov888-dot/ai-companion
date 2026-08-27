# How the art is made

Everything visible is generated. Nothing visible is drawn by code.

That was tried the other way round first — terrain, trees and rocks drawn from
formulas — and it failed for one reason that no amount of tuning fixes: **code
solves the engineering problem, not the art problem.** A tree made of triangles
is correct and lifeless. This document is the version that survived.

---

## The split

| code owns | generation owns |
|---|---|
| where each thing stands, in metres | the tree |
| its distance, and therefore its size on screen | the rock, the bush |
| who is in front of whom | the chair |
| the walkable region, and walking | the ground surface |
| camera, wind, light direction | the distant panorama |
| the shadow cast under each object | the sky |

Every visible thing is a **PNG with an alpha channel**. Code places it at
`(x, z)`, scales it by `F / (z - camZ)`, and draws it in depth order.

### Why this keeps every rule we already set

- **Scale is real.** Each asset carries its height in metres in a manifest. An
  11 m pine is eleven metres because the manifest says so, not because a number
  in the renderer was nudged until it looked right.
- **He walks around things in all four directions.** Objects are points in the
  world, not layers. Walk behind a tree and the tree occludes him; walk in front
  and he occludes it. Depth sorting, nothing else.
- **The ground stays authored.** Unchanged from `WHERE-HE-LIVES.md`. He still
  cannot stand on water, because the walkable region is code and the water is
  paint.
- **A bad asset costs a cent.** Regenerate one tree without touching anything
  else. That is the property hand-drawing never had.

### The one real limitation

A flat sprite does not rotate. For vegetation and rocks this does not matter —
a pine looks the same from every side, which is exactly why sprites are the
standard for vegetation in 3D games. For anything with a clear front, generate
**three angles** (facing left, facing away, facing right) and let code pick by
the angle between the object's facing and the camera. Currently that means the
chair, and nothing else.

---

## Finding the style

A style cannot be described into existence and it does not have to be drawn.
**Generate twenty candidates of one subject and pick.**

```
a single pine tree, isolated, plain flat background, [STYLE],
muted cool green and blue-grey palette, one warm light from the
upper right, no ground, no shadow, no text
```

`[STYLE]` cycles through: gouache painting · stylised game concept art · soft
painterly illustration · cel-shaded with painted texture · screen-printed
poster · hard-edged watercolour · Ghibli background painting · flat vector with
brush texture · airbrushed paperback sci-fi · simplified matte painting.

The chosen image becomes the **anchor**, attached to every asset generated
afterwards — as a style reference (`--sref`, multi-reference) or as the seed of
a small LoRA once there are enough approved assets to train on.

### The zone

| | |
|---|---|
| too minimal | flat shapes, one colour per form, no texture. Correct, dead |
| too realistic | individual leaves, photographic detail |
| **the target** | **painterly stylised** — visible texture, simplified forms, no small detail, strong coloured light |

References: Ghibli background paintings, Eyvind Earle, *GRIS*, *Ori*, *Sable*,
the Firewatch **paintings** rather than the poster.

**The steering note that matters most:** what worked in every test so far was
never shape complexity — it was **coloured atmospheric light and haze**. The
style has to carry light. Detail is optional.

---

## Two kinds of image, and they get opposite prompts

Confusing these is the easiest mistake to make, because one of them is supposed
to look bad.

**Parts** — a tree, a rock, a chair. Nobody ever sees this image. It is a
component, like a Lego brick: dead centre, whole, evenly lit, on nothing. It
should look posed and boring, and if it doesn't, it can't be placed.

**Scenes** — the panorama, the sky, the ground. This is what a person actually
looks at. It must feel cut out of somewhere real: off-centre, things running out
of frame, nothing arranged.

**The life comes from the assembly, not from the parts.** Code scatters trees at
irregular positions, some so close only an edge shows, some half off the screen,
overlapping at different sizes. Boring parts make a living world. The reverse
does not work: a tree already cropped inside its own file can never be placed in
the middle of the screen.

### Prompt for parts

```
[object], side view, no perspective, centred, standing on the bottom
edge of the frame, transparent background, light from the upper right,
no shadow, no ground, nothing else
```

| rule | what breaks without it |
|---|---|
| side view, no perspective | the sprite is only correct at the distance it was drawn for |
| standing on the bottom edge | placement on the ground is eyeballed instead of exact |
| no shadow | code cannot match the shadow to the scene's sun, and everything looks glued on |
| **light from the upper right — for the whole app, forever** | the single biggest thing separating a set of pictures from a world |
| transparent (or flat pure magenta, keyed out) | halos on every edge |

### Prompt for scenes

```
[place], wide view, eye level, natural off-centre composition, things
running out of the frame at the edges, nothing posed, coloured light and
haze, empty ground across the bottom of the image, [STYLE]
```

The last clause is the layout contract from `WHERE-HE-LIVES.md` surviving into
the generated art: whatever the picture is, the bottom band stays clear, because
that is where he walks.

### Manifest

Every asset ships with:

```json
{ "file":"pine-11m.png", "kind":"pine", "height_m":11.0,
  "base_px":  982,        // the pixel row the object stands on
  "angles":  ["side"],    // or ["left","away","right"]
  "seat_m":   null }      // [x, y, z] offset for anything sittable
```

---

## What to generate, in order

Roughly twenty files make three real places. At a cent or two each, under a
dollar total.

**Summit — 7.** small pine 3 m · bush 0.6 m · rock 0.5 m · rock 1.2 m · deck
chair 1.7 m in three angles · one wide painted mountain panorama · one tileable
patch of alpine ground.

**Forest — 5.** pine 11 m · pine 9 m · leafy 8 m · leafy 6 m · undergrowth 0.8 m.

**Beach — 4.** palm 6 m · umbrella 2.3 m · driftwood · grass tuft.

The panorama and the ground texture are the two that are *not* transparent
cut-outs, and they are where generation is strongest and code was weakest.

---

## Which generator

Two tools, one for each phase. Nothing does both well.

**Finding the look — Midjourney v7.** Nothing beats it on raw beauty for
painterly work, and that is the entire job of step 1. Once an image is chosen,
`--sref` carries its mood — colour, texture, lighting, medium — onto every later
prompt without dragging its composition along; v7 made that transfer markedly
more stable. `--sw` (0–1000, default 100) sets how hard the style is pushed.
Note the June 2025 rewrite: `--sref` codes from older libraries need `--sv 4` to
behave as they used to. ~$10/mo.

**Producing the assets — Scenario.** Once ~15 images are approved, train them
into a private model (about 20 minutes) and generate the rest from it. Purpose-
built for holding one style across hundreds of game assets, exports transparent
PNG, commercial rights included, ~$15/mo. Style then lives in the weights rather
than in a reference image, which is what holds it over hundreds of files.

**Not Nano Banana Pro for either** — its strength is surgical editing ("same
tree, shorter, move the branch"), so it is the right tool for repairing one
asset and the wrong one for establishing a style.

Midjourney has no clean alpha channel. Generate parts on flat pure magenta and
key them out — trivial in this style, since there are no soft photographic
edges. Panoramas and ground textures need no alpha at all.

## Sequence

1. Run the twenty style plates. **Pick one.** This is the only blocking step.
2. Generate three or four assets with the anchor attached.
3. Wire them into the engine and look at real art in the real world before
   generating the other sixteen.
4. Approve, then fill out the rest of the manifest.

Step 3 before step 4, always. Sixteen assets in a style that turns out wrong in
motion is sixteen assets wasted; three is not.
