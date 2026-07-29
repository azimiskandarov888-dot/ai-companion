# Bob — Visual & Motion Design Brief

A brief for designing the look and motion of **Bob**, a voice companion app.
Send this to the designer (or Claude design) together with the prompt in
`CLAUDE-DESIGN-PROMPT.md`. **Deliver two distinct visual directions to choose
from.**

---

## 1. Who this is for (read first — it shapes everything)

Bob is a **voice companion for a 87-year-old Russian great-grandad**. He is very
old and lonely, and Bob is a warm friend who keeps him company.

**It is voice-only. He never reads, types, or taps anything.** The phone sits in
a stand by his chair or bed, plugged in, always on. So the screen is **ambient** —
something calm and alive to *rest his eyes on*, not a UI to operate. There are
essentially **no controls and almost no text**. The whole screen is really just
**one living presence** that he talks to.

The screen's only job: make him feel **warm, safe, and not alone** — "someone is
here with me, and it's glad I'm here."

---

## 2. The feeling (north star)

**Warm and alive.** A calm, living glow in a dark room — cozy, gentle, clearly
*awake* and happy to see him. Premium and beautifully crafted, but never
clinical, techy, or busy. Think "a quiet living companion," not "an app."

---

## 3. The core element — a living orb

A single **glowing orb** (a "soul"), centered on a dark screen. **Not a face.
Not a copy of Siri** — its own thing: a warm, breathing, olive-green light.

- **Color:** olive / nature / moss green at heart (green = life, calm, growth),
  with **warm amber/honey accents**. Earthy and warm, never a cold clinical
  green. Soft gradients, a gentle **bloom/glow**, slightly **organic** (not a
  hard geometric circle — light that breathes, drifts, and lives inside it).
- **Alive at rest:** even when idle it is never static — it **breathes** slowly,
  and light drifts gently within it, like calm water or a slow heartbeat.

This orb is the emotional center of the whole app. Everything else is quiet.

---

## 4. States — how the orb responds to the conversation

The orb shows what's happening through **color, glow, and motion — no words.**
Transitions between states are smooth and gentle (see §5):

| State | What's happening | How the orb feels |
|---|---|---|
| **Resting / idle** | Waiting, listening for him | Slow deep breathing; soft olive glow; calm, patient |
| **Listening** | He is speaking | Warmly "opens up" / brightens; gentle ripples that respond to his voice — attentive, welcoming |
| **Thinking** | Bob is composing a reply | A slow inward swirl / soft shimmer — unhurried, "gathering thoughts" |
| **Speaking** | Bob is talking (his voice plays) | Flows and pulses **in time with the speech** — expressive, alive, this is Bob talking |
| **Resting again** | Done | Settles back into calm breathing |

(There may also be a quiet "trouble/offline" state — dimmer and softer, **never
alarming**.)

---

## 5. Motion (this matters as much as the look)

Motion should feel **natural and physical**, in the spirit of Emil Kowalski's
motion work:

- **Spring-based, natural easing** — gentle overshoot and settle. **Never linear,
  never robotic, never jerky.**
- **Calm and slow by default** — this is an elderly viewer, often at night. Soft,
  unhurried, soothing. Nothing flashy or fast.
- **Organic and continuous** — light moves *within* the orb like breath or water,
  not like a mechanical spinner.
- **Purposeful** — every bit of motion communicates a state or a response. No
  decoration for its own sake.
- Respect **Reduce Motion** (offer a calmer, minimal-motion fallback).

---

## 6. The floating indicator (keeps going over other apps) — it MORPHS

When Bob is minimized while another app is open, a small living indicator stays
on top (the family's idea, and the star feature):

- **It morphs by position:**
  - Dragged to a **side or corner** → a small **glowing orb** (mini version of
    the main orb).
  - Dragged to the **top edge** → a **thin glowing line** spanning left→right,
    like the call / recording bar.
  - Dragging between positions **morphs smoothly** between orb and line.
- Same olive-green glow and the same state behavior (it pulses when Bob speaks,
  breathes when idle), just tiny and unobtrusive.

*(Technically this is a later layer — background/Picture-in-Picture — but design
it now so the whole system is coherent.)*

---

## 7. Text & typography (there's almost none — he can't read)

- Show **almost no text to him.** If a tiny status ever appears, keep it small,
  soft, low-contrast, easy to ignore.
- Text that *does* exist (first-time setup, or a warm headline for the family) can
  use an **elegant serif** (like How We Feel's *"How are you feeling this
  morning?"*) for a human, warm tone, paired with a clean sans for any small UI.
- Whatever shows must be **large, calm, and high-contrast** enough for old eyes.

---

## 8. Color & surface

- **Background:** dark — near-black, or a very deep green-black. Calm, easy on
  tired eyes, and it makes the orb glow beautifully at night by his bed.
- **The orb:** olive/moss greens + warm amber/honey accents, soft gradients, a
  gentle bloom, a touch of dimensional depth (like How We Feel's glossy ribbon
  and Apple Fitness's rings).
- **Shapes:** soft, rounded, pill-like for anything that isn't the orb (à la
  Apple Fitness's pill tab bar) — though there is almost nothing else on screen.

---

## 9. Accessibility for an 87-year-old (non-negotiable)

- Large and calm. High contrast where it carries meaning. **No small tap targets**
  (he doesn't tap — but the family does, in setup).
- **No flashing, no harsh strobing, no sudden fast motion.** Gentle brightness,
  especially at night. Nothing that could confuse or alarm him.

---

## 10. Inspiration (references only — do NOT copy)

- **How We Feel** — the glowing gradient ring/orb, the elegant serif headline, the
  dark background, the feeling of a *living, colorful presence*.
- **Apple Fitness** — dark surfaces, glowing rings, rounded pill tab bar, a
  premium tactile feel.

Take the **glow**, the **living ring**, the **dark calm**, and the **craft** — but
make it unmistakably Bob's own: **one warm olive-green living orb**, not a
rainbow, not a dashboard, not data.

---

## 11. What to deliver — TWO variants

Produce **two distinct visual directions** for the main screen (the living orb on
dark), both true to this brief, so the family can choose. For example:

- **Variant A** — a soft **solid glowing orb** (a breathing gradient sphere /
  bloom).
- **Variant B** — a luminous **open ring / halo** (an open ring that flows, in the
  spirit of How We Feel and Apple Fitness).

*(Or your own two takes.)* For **each** variant, show: the **resting** screen, the
four **states** (resting / listening / thinking / speaking), and the **morphing
floating indicator** (orb ↔ top line).

---

## 12. Build constraints (so it's actually buildable)

The app is **SwiftUI, iOS 18+**. Favor effects reachable in SwiftUI — gradients,
blurs, glows, shapes, `Canvas`, `TimelineView`, springs, and simple shaders.
Beautiful, but buildable by hand. (The engineering scaffold already exists; this
is about the look and motion that go on top.)
