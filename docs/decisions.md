# Decisions

What's settled, with the date and why. Older settled decisions are in `docs/HANDOVER.md`.

- 2026-11-09 — Building is done Omega-style: Opus plans and checks, Haiku workers do the bulk work. Why: the owner chose it; cheaper per token, every piece of work gets a check.
- 2026-11-10 — Verification loop added: checklists, read-only reviewer that sees the real result, Stop hook that blocks finishing without PASS (3 tries, then the owner). Why: the owner wants Claude to own whole jobs and look only at work that passed.
