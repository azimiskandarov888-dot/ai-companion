# The paintings — brief for the artist

*Send this to whoever paints the landscapes (or use it as the standard if you paint
them yourself). Everything here is the art side only; the screen layouts live in
`product-spec.html` and the colors in `palette.html`.*

---

## What the app is

A voice-friend app: you talk out loud, and a warm friend answers. The whole product is
built on one promise — **it must never feel like an AI product**. It should feel
natural, alive, and human.

Your paintings *are* that promise. They are the first thing anyone sees and the world
everything else sits inside.

## The one rule

**Real paintings. Hand-made. Not AI-generated, and not photorealistic.**

A generated or photographic-looking image breaks the app's entire premise on the first
screen. If in doubt, paint it looser, not tighter.

## The feeling

Quiet 19th-century landscape painting — **Levitan, Shishkin, Kuindzhi, Corot, the
Hudson River School**. Warm, unhurried, a little lonely in a good way. Somewhere you'd
sit down and write a letter.

**Do**
- Let the brush show. Painted edges, not traced ones.
- Vary the attention: some passages sharp, most loose and suggested.
- Keep few colors, visibly mixed — like paint on a palette, not values off a slider.
- One honest light source; real shadow direction.
- Leave air. Empty sky, empty grass, room to breathe (the UI needs it).
- Let it be imperfect — uneven sky, asymmetric framing, a horizon that isn't dead level.

**Never**
- Photorealism, HDR, lens flare, bokeh, "cinematic" glow, plastic light.
- Hyper-detail everywhere at once, or smeared/nonsensical small detail.
- Fantasy kitsch: glowing mushrooms, impossible moons, magic particles.
- A style that drifts between pieces — **one hand across the whole set**, or the world
  falls apart.

## Palette

Follow `palette.html` — the app's colors are drawn *from* these paintings, so they must
agree:

- **Greens (the world):** `#1F2818` `#37452A` `#4A5C36` `#5E7442` `#7B9455` `#9DB477`
- **Golds (the light):** `#7E5A14` `#A87C22` `#C9982F` `#E3B75A` `#F2D188`
- **Warm shadow / near-black:** `#0E1210` `#141813`
- Nothing cold — no blue-gray, no purple shadows. Shadows are warm and green-brown.
- Sunlight is the accent, not the subject: mostly shade, with light breaking through.

Dawn, midday, or dusk are all welcome — pick per piece, but keep the family resemblance.

## The pieces

| # | Piece | Format | Notes |
|---|-------|--------|-------|
| 1 | **Sign-in hero** | full-bleed portrait | The app's first breath. Text sits over the bottom third — keep it calm and uncluttered there. |
| 2 | **Payment backdrop** | portrait, upper band | Quieter than the hero. May be a crop or variant of #1. |
| 3 | **Story scene** | full-bleed portrait | Must contain a **flat rock like a table**, with an empty area where a parchment scroll will sit. Quill and ink beside it. |
| 4 | **Second scene** | full-bleed portrait | A clearly **different place** (different season/time/terrain), same rock-table idea. |
| 5 | **Profile landscape** | wide band | A calm strip across the top of a screen. |
| 6 | **The living scene** | **layered** (see below) | The friend lives here all day. The most important piece. |

### #6 — the living scene, in layers

The orb (a glowing presence, painted separately by the owner) **moves inside this
scene**: it sits on the rock, rests behind the tree, drifts while speaking. So this one
cannot be a flat image.

Deliver as **separate transparent PNGs on one shared canvas**, back to front:

1. `sky` — sky and light
2. `far` — distant hills / treeline
3. `tree` — the tree the orb can pass **behind**
4. `rock` — the rock it can **sit on** (its top edge readable as a surface)
5. `fore` — foreground grass the orb can pass **behind**

Leave usable open space in the middle ground for it to move through. Gentle parallax
will be applied to these layers, so avoid detail that would look wrong when it shifts a
few pixels.

*Optional, later, and lovely:* morning / day / dusk / night versions of this same scene,
so it follows the real time of day.

## Files

- **1290 × 2796 px minimum** (iPhone Pro Max @3x); more is fine, we downscale.
- **sRGB**, PNG. Layers: transparent PNGs, all on the identical canvas size.
- Please also send a flattened preview of #6 so we can check the composition.
- Original working files (PSD / Procreate) welcome if you're willing.

## Rights

We need full commercial use in the app, in perpetuity — ideally a buy-out or an
exclusive license. Say what you prefer and we'll put it in writing. You keep credit:
the app's About screen names the painter.

---

### If you're sourcing instead of commissioning

Public-domain landscape masters are a genuinely beautiful (and free) alternative for
pieces 1–5: **Levitan, Shishkin, Kuindzhi, Vasilyev, Corot** — all long out of
copyright, with high-resolution museum scans on Wikimedia Commons, Google Arts &
Culture, the Rijksmuseum, and the Met's Open Access collection. Check each specific
scan's terms before shipping it.

Two caveats: you can't control the composition (piece #3 and #4 need that rock-table
and empty space for the scroll), and **piece #6 cannot be sourced this way** — the
layered living scene has to be made for us.
