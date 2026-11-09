"""Gold leaves from the green map: each leaflet keeps its own light and dark (the green map's luminance, spread over a
gold ramp: deep amber → gold → pale gold), its own warmth (a yellower green leaflet → yellower gold, a bluer one →
amber), and the black between leaflets is filled with the leaflets' colour pushed outward (for far-off mip levels).
    python3 gold_leaves.py field-assets/ph field-assets/ph [contrast 1.5] [bright|deep]      (from ios/design)
The page loads jacaranda_leaves_gold(-512).jpg as the leaves' colour (world.html maps.leaves).
"""
import os
import sys

import numpy as np
from PIL import Image

SRC, OUT = sys.argv[1], sys.argv[2]
CONTRAST = float(sys.argv[3]) if len(sys.argv) > 3 else 1.5
os.makedirs(OUT, exist_ok=True)
lin = lambda c: np.where(c <= 0.04045, c/12.92, ((c + 0.055)/1.055)**2.4)
srgb = lambda c: np.where(c <= 0.0031308, c*12.92, 1.055*np.power(np.maximum(c, 0), 1/2.4) - 0.055)


def push_pull(c, w):
    levels = []
    cw, ww = c*w[..., None], w.copy()
    while min(ww.shape) > 1:
        levels.append((cw, ww))
        cw = cw[0::2, 0::2] + cw[1::2, 0::2] + cw[0::2, 1::2] + cw[1::2, 1::2]
        ww = ww[0::2, 0::2] + ww[1::2, 0::2] + ww[0::2, 1::2] + ww[1::2, 1::2]
    col = cw/np.maximum(ww, 1e-8)[..., None]
    smooth = lambda a, h, w: np.stack([np.asarray(Image.fromarray(a[..., i], 'F').resize((w, h), Image.BILINEAR))
                                       for i in range(a.shape[-1])], -1)
    for cw, ww in reversed(levels):
        up = smooth(col.astype(np.float32), *ww.shape)
        k = np.clip(ww, 0, 1)[..., None]
        col = cw/np.maximum(ww, 1e-8)[..., None]*k + up*(1 - k)
    return col


def ramp(stops, t):
    """stops: [(t, (r, g, b) in sRGB 0–255)], mixed in linear light"""
    ts = np.array([s[0] for s in stops]); cs = lin(np.array([s[1] for s in stops], dtype=np.float32)/255)
    i = np.clip(np.searchsorted(ts, t) - 1, 0, len(ts) - 2)
    f = np.clip((t - ts[i])/(ts[i + 1] - ts[i]), 0, 1)[..., None]
    return cs[i]*(1 - f) + cs[i + 1]*f


RAMPS = {'deep': ([(0, (60, 32, 6)), (0.5, (166, 98, 18)), (0.8, (214, 150, 44)), (1, (240, 198, 104))],
                  [(0, (72, 52, 8)), (0.5, (184, 140, 26)), (0.8, (228, 188, 62)), (1, (248, 228, 134))]),
         'bright': ([(0, (66, 40, 6)), (0.5, (180, 124, 22)), (0.8, (226, 176, 52)), (1, (246, 216, 120))],
                    [(0, (78, 58, 6)), (0.5, (196, 160, 30)), (0.8, (238, 208, 70)), (1, (252, 238, 150))])}
AMBER, YELLOW = RAMPS[sys.argv[4] if len(sys.argv) > 4 else 'bright']   # (the sun's own orange takes ~8° of hue off: 'bright' leans yellow)

g = np.asarray(Image.open(f'{SRC}/jacaranda_tree_leaves_diff_1k.jpg').convert('RGB'), dtype=np.float32)/255
m = g.max(-1)*255
mask = np.clip((m - 10)/(26 - 10), 0, 1); mask = mask*mask*(3 - 2*mask)
leaf = mask > 0.999
luma = g @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
lo, hi = np.percentile(luma[leaf], [2, 98])
t = np.clip((luma - lo)/(hi - lo), 0, 1)
t = np.clip(0.5 + (t - 0.5)*CONTRAST, 0, 1)                         # (more contrast: leaflets apart)
warmth = (g[..., 0] - g[..., 2])/np.maximum(g[..., 1], 1e-3)        # (a yellower green has more red over blue)
w0, w1 = np.percentile(warmth[leaf], [10, 90])
yellow = np.clip((warmth - w0)/(w1 - w0), 0, 1)[..., None]
gold = ramp(AMBER, t)*(1 - yellow) + ramp(YELLOW, t)*yellow           # linear light
filled = push_pull(gold, (mask > 0.999).astype(np.float32)*(luma > 0.05))
out = gold*mask[..., None] + filled*(1 - mask[..., None])
im = Image.fromarray(np.clip(np.round(srgb(out)*255), 0, 255).astype(np.uint8), 'RGB')
for size, suffix in [(1024, ''), (512, '-512')]:
    (im if size == im.width else im.resize((size, size), Image.LANCZOS)).save(f'{OUT}/jacaranda_leaves_gold{suffix}.jpg', quality=92)
o = srgb(out); mx, mn = o.max(-1), o.min(-1)
hue = np.where(mx - mn > 1e-6, 60*((o[..., 1] - o[..., 2])/np.maximum(mx - mn, 1e-6)), 0)
print('gold map: leaflet hue p10/50/90', [round(float(np.percentile(hue[leaf], q)), 1) for q in (10, 50, 90)],
      ' luma std', round(float((o @ np.array([0.2126, 0.7152, 0.0722]))[leaf].std()), 3), ' files in', OUT)
