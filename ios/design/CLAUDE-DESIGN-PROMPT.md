# Prompt for Claude design — the app's screens

Copy everything below the line into Claude design, and **attach `product-spec.html`**
(it defines the structure and content of every screen). This prompt is about the
**app's screens** — the orb is NOT your job here, leave it as a placeholder circle.

---

You are designing the screens of **Bob**, a warm voice companion iPhone app for a
lonely **87-year-old Russian great-grandad**. He talks to it out loud; it answers in
a warm voice. I've attached **`product-spec.html`** — it is the source of truth for
**what goes on each screen and where**. Your job is to make those screens **beautiful
and cohesive**. Design the layout, type, color, spacing, components, and states — not
the wording or the feature list (those are set in the spec).

**Two very different users — design for both:**
- **ELDER** — only ever sees screen **1 (Companion)**. Voice-only: he never reads,
  types, or taps. That screen must be almost wordless, huge, ultra-calm.
- **FAMILY / caretaker** — uses screens **2–6** (Onboarding, Account, Bob's Character,
  Memory, Settings) to set Bob up and check on him. These should be clean, modern,
  legible, and trustworthy.

**Screens to design (all six, from the spec):**
1. Companion (elder) · 2. Onboarding / Setup · 3. Account / Profile ·
4. Bob's Character · 5. Memory · 6. Settings

**Visual direction (decided with the family — please honor it):**
- **Warm and alive**, on a **dark near-black** background so things gently glow.
  Cozy and premium — never clinical or "medical app."
- **Olive / nature green** as the primary color (green = life), with **warm amber**
  accents. Suggested anchors: bg `#0d0f0e`, green `#7fae5e`, deep green `#3f5e3a`,
  amber `#e0b15a`, panel `#151a17` — refine as you see fit.
- Motion (describe it, don't animate): natural, gentle, **spring-based** — nothing
  jerky or flashy. Must respect Reduce Motion.
- **Do NOT design the orb.** Wherever the spec shows the living orb, leave a **plain
  placeholder circle** — the family designs the orb separately.
- Built in **SwiftUI, iOS 18+** — keep everything buildable with native components
  (no custom hardware, no web views).

**How I'd like you to work — give me two directions first:**
1. **First, propose TWO distinct visual directions** for the whole set. Show each
   direction applied to **the Companion screen (1)** *and* **one family screen (e.g.
   Settings or Account)**, so I can feel both the elder side and the family side.
   Make the two genuinely different (e.g. one softer/organic, one cleaner/structured)
   — not the same design twice. Briefly note what each direction is going for.
2. **I'll pick one.** Then design **all six screens** in that direction as one
   cohesive set sharing a single visual language (type scale, color, spacing,
   components, iconography).

**For each final screen, include:**
- The **elder-facing Companion** screen shown in its main states (resting, listening,
  thinking, speaking) — conveyed by the placeholder circle's color/glow only, no words.
- The **family screens** with their real sections filled in (use the spec's content).
- A short note on **type sizes, colors, and key components** so it can be built.

**Priorities:** the **Companion screen is the hero** — everything else is its calm,
legible support system. Optimize the elder screen for very old eyes (huge, high
contrast, no clutter); optimize the family screens for clarity and trust.
