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

## The rules every generated asset obeys

Non-negotiable, and they are what make separate images behave as one world:

```
side view, orthographic, camera level with the middle of the object,
no perspective distortion, whole object visible, base of the object
exactly at the bottom edge of the frame, centred horizontally,
transparent background, lit by ONE warm light from the upper right at
about 30 degrees, cool shadow side, no cast shadow, no ground, no
grass, nothing else in frame, no text, no watermark, no border
```

| rule | what breaks without it |
|---|---|
| orthographic, no perspective | the sprite is only correct at the distance it was drawn for |
| base exactly at the bottom edge | placement on the ground is eyeballed instead of exact |
| no cast shadow | code cannot match the shadow to the scene's sun, and everything looks glued on |
| **one light direction, for the whole app, forever** | the single biggest thing separating a set of pictures from a world |
| transparent (or flat pure magenta, keyed out) | halos on every edge |

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

## Sequence

1. Run the twenty style plates. **Pick one.** This is the only blocking step.
2. Generate three or four assets with the anchor attached.
3. Wire them into the engine and look at real art in the real world before
   generating the other sixteen.
4. Approve, then fill out the rest of the manifest.

Step 3 before step 4, always. Sixteen assets in a style that turns out wrong in
motion is sixteen assets wasted; three is not.
