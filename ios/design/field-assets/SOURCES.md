# Where these pictures come from

- `tree.gltf.json` — his tree from mj-15 (`framing/mj-15-hd.jpg`), grown as a 3D tree in Blender by `scene/build_tree.py`:
  the trunk and big limbs traced from his picture, the rest grown into his crown's outline (space colonisation), leaf
  sprays on the twigs. `tree-trace.json` and `scene/assets/tree-mask.png` (from `scene/trace_tree.py`) feed it.
- `leaf-color.webp`, `leaf-normal.webp` — CC0 (public domain): the nine maple leaves of "Leaf Set 027", ambientCG:
  https://ambientcg.com/view?id=LeafSet027 (2K-JPG: colour, opacity, normal, scattering), recoloured to his tree's
  oranges and composed into four sprays by `scene/leaf_atlas.py`.
- `bark-diff.jpg`, `bark-nor_gl.jpg` — CC0: "Japanese Zelkova Bark", Poly Haven: https://polyhaven.com/a/japanese_zelkova_bark
  (2K, scaled to 1024).
- `sky.json` — a fit of his sky's colour, by `scene/trace_tree.py`.
- `leaf-sprites.png` — CC0: the three single leaves of "Leaf Set 015", ambientCG: https://ambientcg.com/view?id=LeafSet015,
  recoloured to autumn. Used for the falling leaves.
