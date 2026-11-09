# Decisions

What's settled, with the date and why. Older settled decisions are in `docs/HANDOVER.md`.

- 2026-11-09 — Building is done Omega-style: Opus plans and checks, Haiku workers do the bulk work. Why: the owner chose it; cheaper per token, every piece of work gets a check.
- 2026-11-09 — The world's "real dark places" look (LOOK in `ios/design/world.html`) is on by default; `?look=old` or `world.setLook(true)` shows the old look for comparison. Why: the frame had no blacks, which the owner saw as "too artificial"; steps 1–4 of the realism report fix that at almost no GPU cost.
- 2026-11-09 — The tree's leaf cards are cut to their leaflets (alpha test 0.5 on a mask, `jacaranda_leaves_mask`), and cards seen edge-on (|N·V| under ~0.2) are cut too. Why: the black between the leaflets and the sunlit edge-on cards were the «butterfly» lines the owner saw; an alpha test keeps the leaves opaque, so no sorting and TAA works as before.
