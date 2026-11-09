# Decisions

What's settled, with the date and why. Older settled decisions are in `docs/HANDOVER.md`.

- 2026-11-09 — Building is done Omega-style: Opus plans and checks, Haiku workers do the bulk work. Why: the owner chose it; cheaper per token, every piece of work gets a check.
- 2026-11-09 — The world's "real dark places" look (LOOK in `ios/design/world.html`) is on by default; `?look=old` or `world.setLook(true)` shows the old look for comparison. Why: the frame had no blacks, which the owner saw as "too artificial"; steps 1–4 of the realism report fix that at almost no GPU cost.
