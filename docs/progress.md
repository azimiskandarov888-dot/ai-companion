# Progress

Where we are. The full state of the project is in `docs/HANDOVER.md`; this file is the short running log.

## Done
- (see `docs/HANDOVER.md`)

## Next
- (frontend branch) «Замер» on his iPhone: after the leaf cut (alpha test), the new grass light and the gold leaves. The sky bake costs nothing on the phone.
- (frontend branch) The trunk is a dark silhouette now (L* 18/25); whether the bark needs a detail layer is for his eye on the phone.
- (frontend branch) The crown's underside lost some of the field's bounce: it is multiplied by the baked sky visibility (3–7 % low in the crown), though those leaves see the bright field below. A second baked number (the ground's share, lower hemisphere) would fix it; COLOR_0.a would have to stop being the leaf flag.
- (frontend branch) Realism steps left: Ghost-style local contrast at ¼ resolution, a 32³ LUT, a grey card in sun/shade/crown to check the shade is cool.

## Log
- 2026-11-09 — Omega setup added: CLAUDE.md, these three docs, builder/reviewer agents on Haiku, reflect skill, project settings (Opus, effort xhigh, compact at 60%).
- 2026-11-09 (frontend branch) — Realism steps 1–4 in `ios/design/world.html` (LOOK): haze near us as thin as clear air, a contrast curve before AgX, backlit leaves filtered by their pigment, sky light in the crown cut by its baked shade. Measured on the design page (393×852, sun −3°/6°): darkest pixel L* 17.8 → 0.5, darkest 2 % L* 39 → 24, spread 2.2 → 3.4 stops. The app bundle is rebuilt.
- 2026-11-09 (frontend branch) — Tree leaves fixed (the owner: «like butterflies, random white and black lines»). The page read the glTF's maps upside down (flipY), so each card showed a piece of another leaf; the leaf map is a JPG with black between the leaflets (42 % of a card), which showed as dark lines. Now: a mask from the green map with an alpha test, the black filled with the leaflets' own colour and a flat normal around them (`ios/design/scene/leaf_alpha.py`), the same mask on the sun's shadow of the crown (dappled light), and cards seen edge-on cut away (in full sun they were thin white streaks). White on the crown 1.9 % → 0.06 %. The crown is lighter now (its darkest 5 % L* 20 → 34): part of the old darkness was that black. Checked on the design page, with `?webgl` and in the app's copy. Not yet on the iPhone.
- 2026-11-10 (frontend branch) — Research «Листва трава и свет уровня TLOU2» (reports/), then building without approvals (his words). A measured decomposition (clear sky, sun −3°/6°, Bob's light off, `bobLight.visible = false`) showed what made the tree grey: not the sky light in the crown (−3 %), but the lens flare's mirrored halo (it lifted the crown's darkest tenth from L* 21 to 39), then the eye's veil and the haze in front. Done: halo 0.15 → 0.02 in all four flare styles (crown L* p10 38.6 → 24.3, texture 6.9 → 9.3; his mj-15: 17 and 9.9); the tree's sky light traced offline through the tree (`scene/sky_bake.py`, 96 rays per vertex through a 10 cm grid, ~90 s per file in Blender; crownSky power 2 → 1); light dying down into the grass (Beer–Lambert: `CANOPY`, the field's darkest tenth L* 44 → 36); gold leaves (`scene/gold_leaves.py`, each leaf cluster its own shade, pigment 2 → 1, tree saturation 1.3 → 1.1); clear air out to 150 m (`LOOK.nearTo`). All together (design page, clear sky): crown L* p10 38.6 → 18.5 (mj-15: 17), crown texture 6.9 → 11.4 (9.9), trunk L* p10/p50 36/43 → 18/25 (5/18), field p10 44 → 36. Not yet on the iPhone.
