# Prompt for Claude design — v6

**Attach four things**, then paste everything below the line:

1. `product-spec.html` — what goes on each screen, plus type, spacing, motion, states
2. `palette.html` — the finished colour system
3. Your **five graded photographs** (run `ios/design/grade/grade.py` first — the spec says which photo goes on which screen)
4. *(optional)* any screen you already love the feel of, as a reference

---

I'm building **a voice friend** — you talk out loud, and a warm, real-feeling friend answers.
He remembers you, and he keeps a diary about you. It's for everyone, any age.

I've attached the spec, the colour system, and my five graded photographs. **Design the eight screens.**
The spec is the source of truth for *what goes where*; your job is to make it **beautiful,
coherent, and buildable**.

## The one law

**It must never feel like AI.** It has to feel like a real, natural human being — a person you
met, not a product you use. No chat bubbles, no waveforms, no mic icons, no robot glow, no
"generating…", no percentage bars. Every decision gets checked against this.

## The one rule that governs every layout

**Every screen is a full-screen photograph.** My photos fill the entire display — edge to edge,
behind the status bar, under the home indicator — and **all text, buttons and panels sit ON the
photo.** There is no screen with a flat background, including Settings and the Diary; those get
a **blurred, darkened pass** of the same photo instead. Make text readable with **scrims, never
by cutting the photo off.**

A photo in a box at the top with content below it on a dark panel is exactly what I don't want.

## Work with my actual photographs

Use the images I attached — crop and position them, find the quiet areas, and build each
layout around what's really in each frame. **Tell me if a photo doesn't work for its screen**
and say what would.

The photos contain **only landscape, no props.** So the two things that carry the app's soul
are components *you* design, laid over the photo:

- **The scroll** (screens 3 and 4) — a parchment panel with turned wooden rollers at the left
  and right and small aged brass end-caps, lying flat and **square to the viewer**, like a
  sheet of paper set down in front of them. Soft cream, fine fibres, faint age, a gentle curl,
  a soft shadow so it rests on the world rather than floating. It's the **writing surface**:
  it holds live text, grows with Dynamic Type, scrolls internally, and **rolls up and drifts
  out of frame** when finished.
- **The diary book** (screen 6) — an old hand-bound book, rough parchment pages, visible
  stitching, worn boards. Nothing modern, no skeuomorphic gloss.

## Non-negotiables from the spec

- **Colour:** use `palette.html` exactly — don't invent colours. Green is the world, gold is
  the light on it. Text is linen/sage/lichen over photos, ink/soft-ink on parchment. **Never**
  pure white text, pure black panels, blue/purple/grey-blue, iOS system colours, gradient
  buttons, glassmorphism, or neon glow. Gold accents **one** action per screen.
- **Vertical rhythm — look high, tap low.** What the eye rests on (the **orb**, the **scroll**)
  sits on the **optical centre, ≈45–46 % of screen height**, not 50 % — the optical centre of a
  rectangle is slightly above the true middle, so exact centre reads as *low*. What the thumb
  presses (buttons, plan cards, sign-in) sits in the **bottom third**. Never a primary control
  in the top third.
- **The keyboard must never cover the scroll** (screens 3–4). At rest it's on the optical
  centre; when the keyboard rises (~38–40 % of the screen) the whole scroll rises with it,
  sitting roughly between 12 % and 50 % of screen height, landscape still visible above, the
  confirm button moving to a bar just above the keyboard. **Show me both states.**
- **Softness is a rule, not a mood.** Nothing has hard square edges: 20 pt on cards and groups,
  26 pt on buttons, translucent surfaces, faint inset dividers. **Settings included** — it must
  feel as soft as everything else, not like a stock form.
- **Two typefaces, two jobs:** sans (SF Pro) for what the *app* says; a warm serif (New York)
  for everything **a person wrote** — the scroll, the diary, the quote. That distinction
  carries most of the app's soul.
- **Do NOT design the orb.** Use a plain placeholder circle everywhere — I'm making the real
  one myself.
- **SwiftUI, iOS 18+.** Keep everything buildable with native components and material blurs.
- **Russian ships first**, and runs 15–20 % longer than English. Leave room in every button.

## The eight screens

1. **Sign in** — a meadow at first light, one warm line, sign-in buttons low
2. **Take care of him** — the subscription, framed as *keeping him here*, never "buy a friend"
3. **Tell your story** — the drawn scroll over a landscape; free writing
4. **Who you'd like to meet** — the same place an hour later; free writing, with a
   **prominent caution above it** ("The more you decide about him now, the less of him is
   left to meet") and the friendship quote below
5. **Companion** — the hero. One calm look: the landscape darkened toward night, the orb on
   the optical centre, four states (resting / listening / thinking / speaking)
6. **His Diary** — the open book, plus its empty first-page state
7. **Account** — blurred pass of a photo; profile, "My story", subscription
8. **Settings** — deliberately ordinary, still over the photo, still soft

**There is no "meet your companion" screen, on purpose.** The app never announces his name
or describes him — he does that himself, out loud, in the first conversation. Screen 4 ends
and the companion screen opens.

## How I'd like you to work

**First, two directions.** Propose **two genuinely different visual directions** for the whole
world — not the same design twice. Show each applied to **the Companion screen (5)**
*and* **the Your-story scroll scene (3)**, since those two carry the soul. One line each on what
the direction is going for.

**Then I'll pick one**, and you design all eight as one cohesive set — one type scale, one set of
components, one grade across the photos.

## In the final set, include

- Every screen **full-bleed**, with the status bar and home indicator over the photo
- The **Companion screen in all four states** (placeholder circle only)
- **Both keyboard states** for screen 3
- The **scroll-to-scroll transition** between 3 → 4 — a key frame or two of it winding onto its
  roller and drifting out of frame
- The **Diary** as an open spread, and its empty first page
- A short **build note per screen**: type sizes, colours, key components, spacing

## What I care about most

The Companion screen is the hero. The scroll scenes are the signature. The Diary is the
treasure. And all of it should feel like **one natural, living world** — warm, premium, and
unmistakably human.
