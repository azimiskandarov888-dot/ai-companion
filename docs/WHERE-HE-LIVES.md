# Where he lives, and why it changes

> «I'm not in the Blade Runner city right now, but seeing my friend there makes
> me feel like I'm there too.»

The world behind him is not wallpaper. It is the loudest thing he can say
without speaking: **I listened, and I moved.**

Month one he lives in a plain place. Nothing special, low hills, ordinary
evening. Months later — once the app actually knows the person — he is standing
on a rain-wet neon street, or on wet sand with the sea behind him, because that
is where this particular person's chest opens up.

He never mentions it. That is the whole point (see *The rules of the reveal*).

---

## The trap, and the one inversion that avoids it

The obvious build is: generate a beautiful picture, then work out where the
ground is in it, then make him walk there.

That build fails, and it fails permanently. Depth estimation gives a soft,
different ground line in every image. He clips into a rock. He sinks into
water. He rolls off a cliff that only exists in the painting. Every new world
becomes a bug, and there are supposed to be millions of worlds.

**So the ground is not generated. The ground is authored, and the AI paints
around it.**

There is exactly **one terrain** in this app. One curve, `ground(x)`, a few
lines of code, the same in every world that will ever exist. The neon street
and the surf beach have the *identical* ground line — one is wet asphalt, the
other is wet sand. The physics never learns the difference, so the physics can
never be wrong.

What the model generates is a **skin over a fixed skeleton**.

| generated | authored in code |
|---|---|
| sky | the terrain curve |
| far ridge silhouette | the collision line |
| mid ridge silhouette | parallax rates |
| ground surface texture | prop anchor points |
| props (palm, sign, lamp) as cut-outs | all motion |

He rolls on the authored curve. Always. In every world, forever, with zero
per-scene tuning. That is the answer to *"he shouldn't just fly around the
background."*

---

## The layout contract

Every generated world obeys the same geometry. These numbers are fixed and
must never drift — they are what makes one physics engine work for a million
paintings. Fractions of canvas height, portrait, 1080 × 2340.

```
0.000 ─────────────────────────  top
                                 SKY          parallax 0.00
0.520 ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  far skyline may begin here
                                 FAR          parallax 0.12
0.600 ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
                                 MID          parallax 0.30
0.680 ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
                                 NEAR         parallax 0.55
0.755 ═══════════════════════════  THE GROUND LINE — baseline of ground(x)
                                 SURFACE      parallax 1.00   ← he is here
1.000 ─────────────────────────  bottom
```

- `ground(x)` undulates **± 0.035 H** around 0.755 — he rolls over real hills,
  he does not skate on glass.
- **Nothing generated may occupy 0.72 → 1.00.** No water, no cliff, no crowd,
  no object standing on the floor. That band belongs to the terrain and to him.
- Props are cut-outs placed by code at anchors that sit *on* `ground(x)`, so a
  lamp post always meets the floor exactly where the floor actually is.
- One foreground occluder band at parallax 1.40 — grass, railing, rain — so he
  passes *behind* something occasionally. That single layer is most of what
  sells depth.

The physics floor is `0.755 · H` in every world. This is why the demo can swap
four completely different places under a rolling ball and nothing twitches.

---

## The style lock

The request was *"one rule, or prompt, that makes the AI draw in the same style
every time."*

Honest finding: **a prompt cannot hold a style.** Not across thousands of
generations, not across different subjects. Every studio shipping consistent
generated art has landed on the same answer.

**Train the style. Don't describe it.**

1. Draw **20–30 scenes by hand**, once. Not a million — thirty. Vary them
   hard: hills, city, sea, forest, desert, snow, dawn, midnight, rain. Keep the
   palette discipline and the layer logic identical in all of them.
2. Train a **style LoRA** on that set. FLUX.2 leads on LoRA support in 2026;
   ~20 minutes, ~$4–15, 15–30 images is the documented sweet spot.
3. After that the style lives in the weights. The prompt only has to name a
   *place*. The hand comes for free.

That is the "one rule" — and it is made of weights, not words, which is why it
actually holds.

It also settles *"maybe I'll draw them myself and another AI redraws them."*
Yes — but not one drawing per scene. Thirty drawings, once, and then the model
draws the millionth one in that same hand.

### Naming the style

There is no single clean name for it. It sits at the intersection of:

| reference | what to take |
|---|---|
| **Atmospheric perspective** | the actual technical term: each ridge lighter, hazier, lower-contrast than the one in front. This *is* the layered-hills effect. |
| **Olly Moss / Firewatch / WPA posters** | flat shapes, limited palette, negative space doing the work |
| **Alto's Odyssey / Adventure** | the closest working reference in the world — silhouette parallax, real terrain underfoot, dynamic weather and time of day, on a phone |
| **GRIS, Sword & Sworcery, Monument Valley** | restraint; the scene stays quiet |
| **lofi** | the *grain*, and nothing else. The term mostly means grainy-gradient anime — take the film grain, leave the kawaii |

Working vocabulary for prompts: *flat shapes, limited palette, atmospheric
perspective, silhouetted ridges, no outlines, soft grain, no interior detail,
wide negative space.*

---

## The prompt

Split exactly like the system prompt in `companion.py` — a **stable half** that
never changes and a **variable half** that is one line. Same discipline, same
reason.

### Stable (byte-identical every time)

```
<TRIGGER>, flat vector landscape illustration, layered silhouette ridges,
strict atmospheric perspective — each band lighter, hazier and lower in
contrast than the band in front of it, no outlines, no line art, no visible
brush strokes, no gradient inside a shape, one flat colour per band, limited
palette of five colours from a single hue family plus one warm light source,
large empty sky, wide negative space, soft film grain, side view at eye level,
camera perfectly level, horizon perfectly level, no perspective convergence.

COMPOSITION, MANDATORY: horizon at 58% of image height. The bottom 28% of the
image is one unbroken open ground plane — empty, nothing standing on it, no
water, no cliff edge, no crowd, no object. All scenery sits above 70% height.

NEGATIVE: people, faces, characters, animals, text, letters, readable signage,
logos, watermark, UI, border, frame, vignette, close-up, macro, photorealism,
3d render, lens flare, tilt-shift, fisheye, diagonal composition, foreground
objects.
```

`<TRIGGER>` is the LoRA's trigger word. It replaces every adjective above once
the LoRA is trained — the style block stays only as a guard rail.

### Variable (one line, written from what he has learned)

```
PLACE: {place}.  TIME: {time}.  WEATHER: {weather}.
```

```
PLACE: a rain-wet neon street in a dense future city, steam off the vents,
       tall stacked signs in an unreadable script
TIME:  after midnight
WEATHER: light rain
```

```
PLACE: an empty beach, long low swell, headland far to the left
TIME:  an hour before sunset
WEATHER: clear, high haze
```

`{place}` is written by the model from the persona and the reading — the same
place the app already gets `what_lifts_him` from. It is never a menu the person
picks from. He learned it because they told him.

### Composition is enforced structurally, not asked for politely

The MANDATORY block above will be obeyed most of the time. Most is not enough
when the floor has to be in the same place a million times.

Render a **depth template** once — a greyscale PNG of the band structure above,
near = white, far = black — and condition every generation on it with **FLUX
ControlNet Depth**. Composition then stops being a request and becomes a
constraint. One template file, reused forever.

---

## Getting the layers apart

Three ways, ranked by how well they survive contact with production:

1. **Generate each band separately on a flat key colour, then key it out.**
   The style has flat colours and no gradients inside shapes, so chroma-keying
   is *exact* — this is trivial here in a way it never is for photographic
   work. 4–5 calls per world. Recommended.
2. **LayerDiffuse-Flux** — true alpha straight out of the model, one pass, no
   cleanup. Good for the prop cut-outs specifically.
3. **Generate one flat image, then decompose** (Qwen-Image-Layered, or depth
   banding). Fewest calls, least control, and the ground line comes back
   unreliable — which is exactly why the ground is authored anyway.

---

## Animation

**Not video models.** They loop visibly at 4–10 s, drift in style between
generations, cost real money per world, weigh a lot on a phone, and — fatally —
cannot parallax against his position, because they don't know where he is.

**The layers move in code**, which is how Alto's does it and is the right answer
here:

| effect | how |
|---|---|
| parallax | each layer offset by `orb.x × rate` |
| cloud drift, fog breathing | slow sine on layer offset + opacity |
| rain, snow, dust, embers | a few hundred particles, cheap |
| neon flicker, water shimmer | shader on the near layer only |
| time of day | the mood tint pass, below |

Optionally 2–4 tiny sprite loops for things code fakes badly — a bird crossing,
a wave breaking. Everything else is free, infinite, never repeats, and costs
nothing per frame that a phone will notice.

---

## Place × mood, and why they don't fight

Two different signals are now painting the same screen. They must mean
different things and move at different speeds.

| | means | changes | source |
|---|---|---|---|
| **PLACE** | who he is *with you* | rarely — milestones | the persona and the reading |
| **LIGHT & WEATHER** | how he is *today* | daily, slowly | his mood |

The mood pass is a **tint over any world**: light colour, light intensity, sun
position, fog density — exactly the four values already in the orb prototype.
It multiplies and hazes; it never replaces. Heavy mood over the neon street is
more fog and dimmer signs, not a different city.

So each generated world ships with one extra authored value: `lightAnchor`,
where its light comes from. The mood pass modulates around that anchor instead
of overriding it, and a night world stays a night world when he is cheerful.

---

## The rules of the reveal

The world is the strongest attachment mechanism in the app, which is exactly
why it needs the tightest rules. Same logic as everywhere else in
`HOW-HE-ATTACHES.md`: it has to make the person's life bigger, or it doesn't
ship.

1. **The first world is plain on purpose.** If the beautiful place is there on
   day one it means nothing. Same gain–loss reasoning as the warmth: what is
   issued at the start cannot be earned later.
2. **He never announces it.** He does not say "I changed it for you." He is
   simply there, and the rain is falling on the neon. If they mention it, he
   answers. If they don't, it goes unremarked forever. Announcing turns a gift
   into an invoice.
3. **It changes overnight, never while they watch.** They open the app and it
   is already true.
4. **Never from GPS. Only from what they told him.** He knows about the surfing
   trip because they said so. Silent location tracking would be the exact
   opposite of this app's ethic, and worse, it would feel like software.
5. **The world stays quiet.** It is the room the conversation happens in, not
   the show. This is the real argument for the flat limited-palette style over
   anything photographic or spectacular — a world that competes with him is a
   world that took something away.
6. **It can go back.** If someone's life changes, so does the place. Nothing
   here is a trophy cabinet.

---

## What it costs

At $0.03/image (FLUX.2 Pro) or ~$0.005–0.012 on fal.ai, a world is 4–5 calls:
**$0.06–0.15, generated once.**

But per-user generation is the wrong shape anyway. The right shape is a
**growing library**:

- a world is generated on demand when nobody has one that fits
- it is then kept forever and reused, re-tinted per person by the mood pass
- ~200 curated worlds will cover most people; only the unusual ones cost anything
- marginal cost trends to zero as the library fills

For the test month with a handful of people this is a rounding error — under a
dollar.

### Quality gate

A generated world can be quietly wrong in ways nobody notices until somebody's
friend is standing in a puddle.

- **automatic:** sample the 0.72–1.00 band, reject if pixel variance is above
  threshold (something is standing on the floor); reject if the palette exceeds
  N distinct colours; reject if the horizon isn't level.
- **human:** every new world is approved before it ships to anybody. That is
  affordable at ten people and stays affordable much longer than it sounds,
  because the library keeps what it learns.

---

## What is needed to start

1. **Thirty drawings.** The single blocking input. Everything above is
   downstream of them, and nobody else can make them.
2. A LoRA trained on those thirty (FLUX.2, or Scenario if a UI is preferred —
   ~15 refs, ~20 min, commercial rights included).
3. The depth template PNG rendered from the layout contract — one file.
4. The renderer: fixed terrain, layer stack, parallax, particles, mood tint.
   Independent of all of the above and buildable now.

Item 4 does not wait on items 1–3. The geometry is the part that has to be
right; the paint can arrive later.
