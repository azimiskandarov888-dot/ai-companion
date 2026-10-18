"""Cut the picture into the layers the wind needs: sky, tree, field.

Every pixel gets a label, by colour and by where it is:
  sky   — blue;
  field — everything below the field's top edge, plus the white plume tips that
          poke above it;
  tree  — the one big non-sky shape above the field (trunk, branches, crown),
          plus the small leaf clusters that sit right against it.
Small non-sky specks out in the open sky are the leaves already flying in the
picture; they are erased and replaced with sky, because the wind makes its own
leaves, and they fall from the crown.

Writes, next to this file: base.jpg (the picture, flying leaves erased),
sky.jpg (the sky with the tree removed — what shows behind a swaying branch),
mask.png (R sky, G tree, B field) and layers-check.jpg (to look at).
Usage: python3 make_layers.py <picture>
"""
import sys
from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).parent
src = Image.open(sys.argv[1]).convert("RGB")
W = 1080; H = round(src.height * W / src.width)
im = src.resize((W, H), Image.LANCZOS)
a = np.asarray(im).astype(np.float32) / 255
r, g, b = a[..., 0], a[..., 1], a[..., 2]
mx, mn = a.max(-1), a.min(-1)
sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)

sky = (b > r + 0.08) & (b > g - 0.02) & (sat > 0.15) & (mx > 0.25)

# the field's top edge: per column, just below the lowest sky pixel in the upper 85 %
ys = np.arange(H)[:, None]
lim = int(H * .85)
low = np.where(sky[:lim].any(0), lim - 1 - np.argmax(sky[:lim][::-1], 0), -1).astype(float)
cols = np.arange(W)
ok = low > H * .55                                      # columns where open sky meets the field (not sky between branches)
low[~ok] = np.interp(cols[~ok], cols[ok], low[ok])     # under the trunk: take it from the neighbours
k = 31
pad = np.pad(low, k // 2, mode="edge")
top = np.array([np.median(pad[i:i + k]) for i in range(W)]) + 1
field = ys >= top[None, :]

# the tree: the largest connected non-sky shape above the field
cand = (~sky) & (~field)
seen = np.zeros_like(cand)
best = None
for y0, x0 in zip(*np.nonzero(cand[::7, ::7])):
    y0, x0 = y0 * 7, x0 * 7
    if seen[y0, x0] or not cand[y0, x0]:
        continue
    comp = []; q = deque([(y0, x0)]); seen[y0, x0] = True
    while q:
        y, x = q.popleft(); comp.append((y, x))
        for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= yy < H and 0 <= xx < W and cand[yy, xx] and not seen[yy, xx]:
                seen[yy, xx] = True; q.append((yy, xx))
    if best is None or len(comp) > len(best):
        best = comp
tree = np.zeros_like(cand)
ty, tx = np.array(best).T; tree[ty, tx] = True
near_tree = np.asarray(Image.fromarray(tree.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(41))) > 0
whitish = (sat < .38) & (mx > .5)
near_field = ys >= (top[None, :] - 80)
tips = cand & ~tree & near_field & whitish              # plume tips above the edge: grass
tree |= cand & ~tips & near_tree & ~near_field          # leaf clusters hugging the crown: tree
field |= tips
flying = cand & ~tree & ~tips                           # the rest: leaves already in the air — erase

# the foot of the trunk stands inside the grass edge; dark trunk pixels there stay stiff
band = tree & (ys >= top[None, :] - 40)
if band.any():
    tx0, tx1 = np.nonzero(band)[1].min() - 6, np.nonzero(band)[1].max() + 6
    foot = field & (mx < .4) & (ys < top[None, :] + 140) & (cols[None, :] >= tx0) & (cols[None, :] <= tx1)
    tree |= foot; field &= ~foot

# the sky everywhere above the field: a smooth fit of the real sky's colour
yy, xx = np.nonzero(sky)
pick = np.random.default_rng(0).choice(len(yy), min(40000, len(yy)), replace=False)
Y, X = yy[pick] / H, xx[pick] / W
A = np.stack([np.ones_like(X), X, Y, X * Y, X * X, Y * Y], 1)
gy, gx = np.mgrid[0:H, 0:W]; GY, GX = gy / H, gx / W
fit = np.zeros((H, W, 3), np.float32)
for c in range(3):
    coef, *_ = np.linalg.lstsq(A, a[yy[pick], xx[pick], c], rcond=None)
    fit[..., c] = coef[0] + coef[1] * GX + coef[2] * GY + coef[3] * GX * GY + coef[4] * GX * GX + coef[5] * GY * GY
grain = np.random.default_rng(1).normal(0, .008, (H, W, 1)).astype(np.float32)
skyfill = np.clip(fit + grain, 0, 1)

erase = np.asarray(Image.fromarray(flying.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(5))) > 0
erase &= ~tree & ~field
base = a.copy(); base[erase] = skyfill[erase]
skyplate = np.where((sky & ~erase)[..., None], a, skyfill)
deep = field & (ys >= top[None, :] + 60)               # the plume tips wave into the sky: show sky behind them
skyplate[deep] = a[deep]

def soft(m):  # a one-pixel feather, so edges don't shimmer
    return np.asarray(Image.fromarray(m.astype(np.uint8) * 255).filter(ImageFilter.GaussianBlur(.7)))
mask = np.stack([soft(~tree & ~field), soft(tree), soft(field)], -1)
Image.fromarray((base * 255).astype(np.uint8)).save(HERE / "base.jpg", quality=90)
Image.fromarray((skyplate * 255).astype(np.uint8)).save(HERE / "sky.jpg", quality=88)
Image.fromarray(mask.astype(np.uint8)).save(HERE / "mask.png")
tint = base.copy()
tint[tree] = tint[tree] * .45 + np.array([1, .35, .1]) * .55
tint[field & ~tree] = tint[field & ~tree] * .45 + np.array([.2, .9, .3]) * .55
tint[erase] = np.array([1, 0, 1])
Image.fromarray((tint * 255).astype(np.uint8)).resize((W // 2, H // 2)).save(HERE / "layers-check.jpg", quality=85)
print(f"{W}x{H} · tree {tree.mean():.1%} · field {field.mean():.1%} · erased flying leaves {erase.sum()} px")

# what the wind code needs to know about the picture
import json
foot_x = int(np.nonzero(band)[1].mean()) if band.any() else int(W * .1)
crown_top = int(np.nonzero(tree)[0].min())
(HERE / "layout.json").write_text(json.dumps({
    "W": W, "H": H, "top": [round(float(t), 1) for t in top[::4]],
    "trunk": [foot_x, round(float(top[foot_x]), 1)], "crownTop": crown_top}))
print("trunk foot", foot_x, round(float(top[foot_x])), "· crown top", crown_top)
