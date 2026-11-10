# Known issues

Gotchas and their fixes. Older ones are in `docs/HANDOVER.md` and `docs/AUDIT-2026-09.md`.

- `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` comes from a guide and is not confirmed to exist. If built-in Explore/Plan agents still run on Opus, that's why; `builder` and `reviewer` are on Haiku through their own `model: haiku` either way.
