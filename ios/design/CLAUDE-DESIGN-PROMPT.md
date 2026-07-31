# Prompt for Claude design — the app's screens (v2)

Copy everything below the line into Claude design and **attach `product-spec.html`**
(structure and content of every screen) **and `palette.html`** (the finished color
system). The orb is NOT part of this job — leave it as a plain placeholder circle.

---

You are designing the screens of a **voice-friend app for everyone** — you talk out
loud, and a warm, real-feeling friend answers. I've attached **`product-spec.html`**
(the source of truth for **what goes on each screen and where**) and **`palette.html`**
(the **finished color system — use it exactly, don't invent new colors**). Your job is
to make those screens **beautiful and cohesive** — layout, type, spacing, components,
states. Don't change the feature list or the philosophy; they're set.

**The one law: it must never feel like AI.** It must feel like a real, natural human
being — and the whole app must feel **natural, with life in it**. No chat bubbles, no
waveforms, no mic icons, no robot glow, no "generating…" — ever.

**The world it's built from (from the spec — honor it):**
- **Landscape paintings** as the canvas (sign-in, profile, the writing scenes, the
  living companion scene) — all clearly painted by **one artist's hand**.
- **Parchment, quill & ink** for everything written by the user; an **ancient handmade
  handwritten book** for the friend's diary. Never a plain floating form.
- **Colors — "sunlight through leaves"** (full system in `palette.html`, follow it):
  green is the world, gold is the light on it. Two surfaces decide every text color —
  **night** (`#0E1210` bg, panels `#1B211A`; text linen `#EFE9D8`, sage `#BCC3AC`,
  lichen `#8A9280`, accent sun `#E3B75A`) and **parchment** (`#F2E8D0`; text ink
  `#2E2718`, soft ink `#574C36`, deep gold `#7E5A14`). Greens: `#4A5C36` `#5E7442`
  `#7B9455` `#9DB477`. Destructive: clay `#D2735A` (dark) / `#A4402A` (paper).
  **Never** pure white text, pure black backgrounds, blue/purple/gray-blue, iOS system
  colors, gradient buttons, glassmorphism, or neon glow. Gold accents **one** action
  per screen. **Text over a painting always needs a bottom-up scrim**
  (`rgba(10,14,10,.82)` → transparent by ~70% height).
- Motion described, not animated: scrolls roll up and drift out of frame, pages turn,
  the orb wanders and settles. Gentle, spring-based. Respect Reduce Motion.
- **Do NOT design the orb.** Wherever the spec shows it, use a plain placeholder
  circle — the owner paints the real orb separately.
- Built in **SwiftUI, iOS 18+** — keep it buildable (paintings as layered images,
  native components underneath).

**Screens to design (all nine, from the spec):**
1. Sign in (landscape painting) · 2. Payment · 3. Your story — «Tell us about you and
your likings» (scroll + rock + quill + ink in a landscape) · 4. Who you'd be with
(second scroll scene; age/gender/origin only — no name; the quote below the scroll) ·
5. Meet him & choose your world (Regular orb vs Living scene) · 6. Companion (both
modes, states: resting/listening/thinking/speaking) · 7. The Companion's Diary (the
handmade book) · 8. Account / Profile (landscape painting) · 9. Settings (deliberately
ordinary).

**How to work — two directions first:**
1. **Propose TWO distinct visual directions** for the whole world. Show each applied to
   **the Companion screen (6, both modes)** *and* **the Your-story scroll scene (3)** —
   those two screens carry the soul. Make the directions genuinely different (e.g. one
   more painterly/romantic, one more minimal/refined), and say in a line what each is
   going for.
2. **I'll pick one.** Then design **all nine screens** in that direction as one
   cohesive set sharing a single visual language (type scale, color, spacing,
   components, iconography).

**For the final set, include:**
- The Companion screen in its four states, in both modes (placeholder circle only).
- The scroll-to-scroll **transition moment** between screens 3 → 4 (a key frame or two).
- The Diary as an open book spread with handwritten-feeling text.
- A short build note per screen: type sizes, colors, key components.

**Priorities:** the Companion screen is the hero; the scroll scenes are the signature
onboarding; the Diary is the treasure. Every screen should feel like one natural,
living, painted world — warm, premium, and human.
