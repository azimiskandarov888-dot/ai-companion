# Known issues

Gotchas and their fixes. Older ones are in `docs/HANDOVER.md` and `docs/AUDIT-2026-09.md`.

- `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` comes from a guide and is not confirmed to exist. If built-in Explore/Plan agents still run on Opus, that's why; `builder` and `reviewer` are on Haiku through their own `model: haiku` either way.
- The verification gate trusts the reviewer: nothing technically stops the main session from running `verify.sh pass` itself. The rule in CLAUDE.md forbids it.
- The gate only watches uncommitted changes in backend/, ios/, tools/. Committing before review bypasses it; the rule forbids that too.
