# Known issues

Gotchas and their fixes. Older ones are in `docs/HANDOVER.md` and `docs/AUDIT-2026-09.md`.

- `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` comes from a guide and is not confirmed to exist. If built-in Explore/Plan agents still run on Opus, that's why; `builder` and `reviewer` are on Haiku through their own `model: haiku` either way.
- In a hidden browser pane, `?offscreen` leaves the sun and the sky black: @takram builds the atmosphere tables only in `requestIdleCallback`, and the offscreen loop never leaves the page idle. For measuring, load without `?offscreen`, wait a few seconds, then draw by hand.
- The sun drifts by itself every 15 s (SKYLIFE). For a before/after, call `world.setSun(az, el)` before each capture, or the two frames have different suns.
- Agents added to `.claude/agents/` load only when a session starts. In the session that added them, run the same brief on `general-purpose` with `model: haiku`.
- With `?webgl` (WebGL2, how iOS 17–18 draws the world) one vertex shader fails to compile: `'AtmosphereParameters' : syntax error`. three.js r184 leaves @takram's struct declarations out of it, and the `getStructs` patch at the top of `world.html` only helps a vertex stage that has no structs of its own. It was there before the realism change (seen on 889596c's page too). The evening frame still looks whole, so the failing object is probably one only seen at dusk (the stars); not yet fixed.
