# Progress

Where we are. The full state of the project is in `docs/HANDOVER.md`; this file is the short running log.

## Done
- (see `docs/HANDOVER.md`)

## Next
- (frontend branch) The owner picks the tree's colour from `ios/design/framing/tree-colour-choice.jpg` (1 = now; 2–4 less saturated, 2–3 nearest his mj-15); then set `LOOK.pigment` and `GRADE.tree` to it.
- (frontend branch) «Замер» on his iPhone after the leaf cut: the alpha test (discard) can cost on Apple GPUs.
- (frontend branch) Realism steps 5–7 from `reports/Реализм света и листвы по играм.md`: a 32³ LUT, Ghost-style local contrast at ¼ resolution, light shafts in the haze. The sky is still only 1.7 stops above the tree (target ≥ 3.5).
- (frontend branch) A grey card in sun, shade and crown, to check that the shade is cool (it is still as orange as the light).

## Log
- 2026-11-09 — Omega setup added: CLAUDE.md, these three docs, builder/reviewer agents on Haiku, reflect skill, project settings (Opus, effort xhigh, compact at 60%).
- 2026-11-09 (frontend branch) — Realism steps 1–4 in `ios/design/world.html` (LOOK): haze near us as thin as clear air, a contrast curve before AgX, backlit leaves filtered by their pigment, sky light in the crown cut by its baked shade. Measured on the design page (393×852, sun −3°/6°): darkest pixel L* 17.8 → 0.5, darkest 2 % L* 39 → 24, spread 2.2 → 3.4 stops. The app bundle is rebuilt.
- 2026-11-09 (frontend branch) — Tree leaves fixed (the owner: «like butterflies, random white and black lines»). The page read the glTF's maps upside down (flipY), so each card showed a piece of another leaf; the leaf map is a JPG with black between the leaflets (42 % of a card), which showed as dark lines. Now: a mask from the green map with an alpha test, the black filled with the leaflets' own colour and a flat normal around them (`ios/design/scene/leaf_alpha.py`), the same mask on the sun's shadow of the crown (dappled light), and cards seen edge-on cut away (in full sun they were thin white streaks). White on the crown 1.9 % → 0.06 %. The crown is lighter now (its darkest 5 % L* 20 → 34): part of the old darkness was that black. Checked on the design page, with `?webgl` and in the app's copy. Not yet on the iPhone.
