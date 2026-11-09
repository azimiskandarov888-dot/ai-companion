"""The tree's leaf cards had no transparency: their maps are JPGs, three feathery jacaranda leaves on black, and the
cards cover the black between the leaflets (42 % of the leaf surface). So the black showed as dark lines, and the
normal map's noise there as white glints — leaves like butterfly wings.

This makes, for each leaf map: a mask (the leaflets, soft-edged, from the original green map), the colour map with
the black filled by the leaflets' own colour pushed outward (push-pull, so far-away mip levels keep the leaf's colour
instead of fading to black), and the normal map flat around the leaflets (its noise there made the glints). Also: the
page must read these maps with flipY false, as glTF's UVs are made — flipped, each card showed another leaf's piece.

    python3 scene/leaf_alpha.py field-assets/ph field-assets/ph

Run it on the maps as they came (git: before the commit that added this file). Run again, it gives the same maps: the
mask comes from the untouched green map, and the leaflets' own pixels are kept as they are.
"""
import os
import sys

import numpy as np
from PIL import Image

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)


def push_pull(c, w):
    """Fill where w is 0 with the weighted colour around it (c: H×W×k, w: H×W in 0…1), keeping w = 1 as it is."""
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


green = np.asarray(Image.open(f'{SRC}/jacaranda_tree_leaves_diff_1k.jpg').convert('RGB'), dtype=np.float32)
m = green.max(-1)
mask = np.clip((m - 10)/(26 - 10), 0, 1)                        # (JPEG leaves a little noise in the black: 0–8)
mask = mask*mask*(3 - 2*mask)
solid = (mask > 0.999).astype(np.float32)                        # only clean leaf pixels give their colour away

autumn = np.asarray(Image.open(f'{SRC}/jacaranda_leaves_autumn.jpg').convert('RGB'), dtype=np.float32)/255
lin = np.where(autumn <= 0.04045, autumn/12.92, ((autumn + 0.055)/1.055)**2.4)
lum = lin @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
filled = push_pull(lin, solid*(lum > 0.03))                      # (dark stems and shaded leaflets give nothing away)
lin_out = lin*mask[..., None] + filled*(1 - mask[..., None])
srgb = np.where(lin_out <= 0.0031308, lin_out*12.92, 1.055*np.power(lin_out, 1/2.4) - 0.055)

nor = np.asarray(Image.open(f'{SRC}/jacaranda_tree_leaves_nor_gl_1k.jpg').convert('RGB'), dtype=np.float32)/255*2 - 1
flat = np.array([0, 0, 1], dtype=np.float32)                    # (around the leaflets: a flat leaf, no noise)
nor_out = nor*mask[..., None] + flat*(1 - mask[..., None])
nor_out /= np.maximum(np.linalg.norm(nor_out, axis=-1, keepdims=True), 1e-6)

def save(arr, name, mode):
    im = Image.fromarray(np.clip(np.round(arr*255), 0, 255).astype(np.uint8), mode)
    for size, suffix in [(1024, ''), (512, '-512')]:
        out = im if size == im.width else im.resize((size, size), Image.LANCZOS)
        out.save(f'{OUT}/{name}{suffix}.jpg', quality=95 if mode == 'L' else 92)   # (the page loads every map as .jpg)

save(mask, 'jacaranda_leaves_mask', 'L')
save(srgb, 'jacaranda_leaves_autumn', 'RGB')
save(nor_out*0.5 + 0.5, 'jacaranda_tree_leaves_nor_gl_1k', 'RGB')
print('mask: leaf share', round(float((mask > 0.5).mean())*100, 1), '% ; files in', OUT)
