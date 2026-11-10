"""Jacaranda leaf clusters: the three leaf-card footprints of the tree atlas, each filled with big opaque gold leaves
laid along the frond's spine (pinnate), so a card reads as a solid cluster from 30 m instead of a mist of 1 cm leaflets.
Spine leaves first (7 per frond), then fill leaves placed on the thinnest spots of the footprint until its coverage
reaches 0.88 (at most 40 fills).
    python3 scene/leaf_clusters.py field-assets/ph field-assets/ph [seed 7] [preview.jpg]      (from ios/design)
Reads jacaranda_leaves_mask.jpg (white = the three fronds' leaflets). Writes jacaranda_cluster_colour.jpg,
jacaranda_cluster_mask.jpg and jacaranda_cluster_nor_gl.jpg at 1024 (no suffix) and 512 (suffix -512).
"""
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

SRC, OUT = sys.argv[1], sys.argv[2]
SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 7
PREVIEW = sys.argv[4] if len(sys.argv) > 4 else None
N = 2048
FILL_COVER, FILL_MAX = 0.88, 40
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(SEED)
lin = lambda c: np.where(c <= 0.04045, c/12.92, ((c + 0.055)/1.055)**2.4)
srgb = lambda c: np.where(c <= 0.0031308, c*12.92, 1.055*np.power(np.maximum(c, 0), 1/2.4) - 0.055)
# (a little yellower than the frond map's gold: the crown's shade, amber by THROUGH, pulled the whole tree to copper)
GOLD = [(0, (108, 72, 10)), (0.45, (198, 146, 30)), (0.75, (234, 194, 68)), (1, (250, 230, 146))]


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


def blur(m, radius):
    """float 0..1 -> blurred float 0..1 (8-bit precision is enough for masks and shadows)"""
    img = Image.fromarray(np.clip(np.round(m*255), 0, 255).astype(np.uint8))
    return np.asarray(img.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32)/255


def value_noise(bw, bh):
    g = rng.uniform(-1, 1, (64, 64)).astype(np.float32)
    return np.asarray(Image.fromarray(g).resize((bw, bh), Image.BILINEAR), dtype=np.float32)


# 1. footprints: the three fronds, gaps closed, three largest components
src = np.asarray(Image.open(f'{SRC}/jacaranda_leaves_mask.jpg').convert('L').resize((N, N), Image.BILINEAR),
                 dtype=np.float32)/255
F = blur((blur(src, 22) > 0.18).astype(np.float32), 10) > 0.5          # fast closing of the fronds' gaps

S = 256
small = np.asarray(Image.fromarray((F*255).astype(np.uint8)).resize((S, S), Image.NEAREST)) > 127
lab = np.zeros((S, S), np.int32)
sizes = []
for sy in range(S):
    for sx in range(S):
        if small[sy, sx] and lab[sy, sx] == 0:
            n_lab = len(sizes) + 1
            stack = [(sy, sx)]; lab[sy, sx] = n_lab; cnt = 0
            while stack:
                y, x = stack.pop(); cnt += 1
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < S and 0 <= xx < S and small[yy, xx] and lab[yy, xx] == 0:
                        lab[yy, xx] = n_lab; stack.append((yy, xx))
            sizes.append(cnt)
keep = np.argsort(sizes)[::-1][:3]
lab_big = np.asarray(Image.fromarray(lab).resize((N, N), Image.NEAREST))
comps = [(lab_big == k + 1) & F for k in keep]
print('fronds:', len(comps), 'component sizes (256 grid):', [sizes[k] for k in keep])

X, Y = np.meshgrid(np.arange(N, dtype=np.float32), np.arange(N, dtype=np.float32))
BORDER = np.clip(np.minimum(np.minimum(X, Y), np.minimum(N - 1 - X, N - 1 - Y))/10, 0, 1)   # fade within 10 px


def frond_geometry(comp):
    ys, xs = np.nonzero(comp)
    x, y = xs.astype(np.float64), ys.astype(np.float64)
    cx, cy = x.mean(), y.mean()
    vals, vecs = np.linalg.eigh(np.cov(np.stack([x - cx, y - cy])))
    a = vecs[:, np.argmax(vals)]
    p = (x - cx)*a[0] + (y - cy)*a[1]
    smin, smax = p.min(), p.max()
    L = smax - smin
    lo = (p <= smin + 0.15*L).sum(); hi = (p >= smax - 0.15*L).sum()
    if hi < lo:                      # the stem end has fewer pixels: point a from the stem to the tip
        a = -a; p = -p
    smin, smax = p.min(), p.max()
    q = -(x - cx)*a[1] + (y - cy)*a[0]
    return dict(c=np.array([cx, cy]), a=a, smin=smin, L=smax - smin, width=2.5*q.std())


# 2. leaves per frond
def spine_specs():
    """7 spine leaves: 6 alternating sides along the spine plus the terminal leaf"""
    specs = []
    for i, u0 in enumerate([0.18, 0.30, 0.42, 0.54, 0.66, 0.78]):
        side = 1 if i % 2 == 0 else -1
        specs.append((u0 + rng.uniform(-0.03, 0.03), side*np.deg2rad(rng.uniform(35, 55))))
    specs.append((0.80, np.deg2rad(rng.uniform(-8, 8))))                     # terminal leaf
    return specs


# 3. drawing one leaf (bounding box only); keep = per-frond footprint clip times the border fade
def draw_leaf(b, d, l, w, cp, mask, nrm, fa, keep):
    e = np.array([-d[1], d[0]])
    margin = int(0.12*l) + 24
    corners = [b + d*s_ + e*t_ for s_ in (0, l) for t_ in (-w/2, w/2)]
    x0 = max(0, int(min(c[0] for c in corners)) - margin); x1 = min(N, int(max(c[0] for c in corners)) + margin + 1)
    y0 = max(0, int(min(c[1] for c in corners)) - margin); y1 = min(N, int(max(c[1] for c in corners)) + margin + 1)
    sl = (slice(y0, y1), slice(x0, x1))
    gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    rx, ry = gx - b[0], gy - b[1]
    s = (rx*d[0] + ry*d[1])/l
    t = rx*e[0] + ry*e[1]
    k = 1 if rng.uniform() < 0.5 else -1
    tp = t - 0.08*l*k*s*(1 - s)*4                                           # midrib bends sideways
    sc = np.clip(s, 0, 1)
    h = (w/2)*np.sin(np.pi*sc**0.75)**0.85                                  # ovate, pointed tip
    alpha = (np.clip((h - np.abs(tp))/1.2 + 0.5, 0, 1)*((s >= 0) & (s <= 1))).astype(np.float32)
    alpha = alpha*keep[sl]                                                  # clipped to the footprint and border
    bh, bw = alpha.shape

    base = ramp(GOLD, np.array([rng.uniform(0.25, 1.0)]))[0]
    mult = (0.82 + 0.28*sc)*np.where(np.abs(tp) < 1.6*(1 - sc) + 0.6, 1.12, 1.0)
    v = 0.5 + 0.5*np.sin(2*np.pi*(7*sc + 3.5*np.abs(tp)/w))
    mult = mult*(1 - 0.06*(v > 0.85))*(1 + 0.05*value_noise(bw, bh))*(0.9 + 0.1*np.clip((h - np.abs(tp))/6, 0, 1))
    col = (base[None, None, :]*mult[..., None]).astype(np.float32)

    sh = blur(alpha, 9)                                                     # shadow onto what is drawn
    shifted = np.zeros_like(sh); shifted[9:, 6:] = sh[:-9, :-6]             # +6 px x, +9 px y
    cp[sl] *= np.where(mask[sl] > 0, 1 - 0.5*shifted, 1)[..., None]

    th = np.deg2rad(rng.uniform(0, 32)); ph = rng.uniform(0, 2*np.pi)
    n0 = np.array([np.sin(th)*np.cos(ph), np.sin(th)*np.sin(ph), np.cos(th)])
    ex, ey = e[0], -e[1]                                                    # picture up is -row
    bulge = 0.45*tp/(w/2)
    crease = np.where(np.abs(tp) < 2, -0.15*np.sign(tp), 0)
    nx = n0[0] + (bulge + crease)*ex
    ny = n0[1] + (bulge + crease)*ey
    nz = np.full_like(nx, n0[2])
    ln = np.sqrt(nx**2 + ny**2 + nz**2)
    leafn = np.stack([nx/ln, ny/ln, nz/ln], -1).astype(np.float32)

    a3 = alpha[..., None]
    cp[sl] = cp[sl]*(1 - a3) + col*a3                                       # premultiplied colour
    mask[sl] = np.maximum(mask[sl], alpha)
    fa[sl] = np.maximum(fa[sl], alpha)
    nrm[sl] = nrm[sl]*(1 - a3) + leafn*a3


cp = np.zeros((N, N, 3), np.float32)
mask = np.zeros((N, N), np.float32)
nrm = np.zeros((N, N, 3), np.float32); nrm[..., 2] = 1
report = []
for comp in comps:
    g = frond_geometry(comp)
    a, smin, L, c = g['a'], g['smin'], g['L'], g['c']
    perp = np.array([-a[1], a[0]])
    ell = 0.32*L
    keep_f = np.clip((blur(comp.astype(np.float32), 16) - 0.3)/0.4, 0, 1)*BORDER   # F grown a little, faded at border
    ys_c, xs_c = np.nonzero(comp)

    spine = []
    for u, ang in spine_specs():
        length = ell*rng.uniform(0.85, 1.15); w = 0.48*length
        d = np.cos(ang)*a + np.sin(ang)*perp
        b = c + a*(smin + u*L)
        spine.append((b, d, length, w))
    fa = np.zeros((N, N), np.float32)
    for i in rng.permutation(len(spine)):
        draw_leaf(*spine[i], cp, mask, nrm, fa, keep_f)

    # fill: put a leaf on the thinnest spot of the footprint until its coverage reaches FILL_COVER
    n_fill = 0
    for _ in range(FILL_MAX):
        if ((mask > 0.5) & comp).sum()/comp.sum() >= FILL_COVER:
            break
        vals = blur(mask, 18)[ys_c, xs_c]
        cand = np.nonzero(vals <= vals.min() + 1e-6)[0]
        j = cand[rng.integers(len(cand))]
        q = np.array([xs_c[j], ys_c[j]], np.float64)
        proj_q = (q[0] - c[0])*a[0] + (q[1] - c[1])*a[1]
        u = np.clip((proj_q - smin)/L, 0.1, 0.95)
        p = c + a*(smin + u*L)
        vec = q - p; dist = np.linalg.norm(vec)
        if dist < 0.15*ell:                                                 # on the spine: point along the axis
            ang = (1 if rng.uniform() < 0.5 else -1)*np.deg2rad(rng.uniform(30, 60))
            d = np.cos(ang)*a + np.sin(ang)*perp
        else:
            d0 = vec/dist; d0p = np.array([-d0[1], d0[0]])
            rot = np.deg2rad(rng.uniform(-20, 20))
            d = np.cos(rot)*d0 + np.sin(rot)*d0p
        length = ell*rng.uniform(0.7, 1.0); w = 0.48*length
        b = q - d*0.45*length
        draw_leaf(b, d, length, w, cp, mask, nrm, fa, keep_f)
        n_fill += 1

    proj = (X - c[0])*a[0] + (Y - c[1])*a[1]
    u_ax = np.clip((proj - smin)/L, 0, 1)
    cp *= (1 - fa*(1 - (0.72 + 0.28*u_ax)))[..., None]                      # cluster shade, only where covered
    report.append((L, g['width'], len(spine) + n_fill, comp))

# 4. finish: straight colour, gaps filled outward, normals
mask_c = np.clip(mask, 0, 1)
col = np.zeros_like(cp)
np.divide(cp, np.maximum(mask_c, 1e-4)[..., None], out=col, where=(mask_c > 1e-4)[..., None])
filled = push_pull(col.astype(np.float32), (mask_c > 0.95).astype(np.float32))
final = np.where((mask_c < 0.5)[..., None], filled, col)
nrm_f = nrm/(np.linalg.norm(nrm, axis=-1, keepdims=True) + 1e-6)
nrm_f[mask_c < 0.5] = [0, 0, 1]


def to8(x):
    return Image.fromarray(np.clip(np.round(x*255), 0, 255).astype(np.uint8))


colour8 = to8(srgb(final)); mask8 = to8(mask_c); nor8 = to8(nrm_f*0.5 + 0.5)
for size, suffix in [(1024, ''), (512, '-512')]:
    for im, name, q in ((colour8, 'colour', 92), (mask8, 'mask', 95), (nor8, 'nor_gl', 95)):
        im.resize((size, size), Image.LANCZOS).save(f'{OUT}/jacaranda_cluster_{name}{suffix}.jpg', quality=q)

if PREVIEW:
    col_s = srgb(final)
    grey = np.full((N, N, 3), 40/255, np.float32)
    left = col_s*mask_c[..., None] + grey*(1 - mask_c[..., None])
    pv = Image.new('RGB', (1600, 800))
    pv.paste(to8(left).resize((800, 800), Image.LANCZOS), (0, 0))
    pv.paste(to8(nrm_f*0.5 + 0.5).resize((800, 800), Image.LANCZOS), (800, 0))
    pv.save(PREVIEW, quality=92)

for i, (L, width, n_leaves, comp) in enumerate(report):
    cov = ((mask_c > 0.5) & comp).sum()/max(comp.sum(), 1)
    print(f'frond {i}: length {L:.0f} px, width {width:.0f} px (2048 grid), leaves {n_leaves}, '
          f'footprint covered (mask>0.5) {cov:.3f}')
print('whole image mask share', round(float((mask_c > 0.5).mean()), 3), ' files in', OUT)

# mip levels of the saved 1024 mask: share of footprint pixels with mask > 0.5
m1024 = Image.open(f'{OUT}/jacaranda_cluster_mask.jpg').convert('L')
f1024 = Image.fromarray((F*255).astype(np.uint8))
for s in (1024, 128, 64, 32):
    ms = np.asarray(m1024.resize((s, s), Image.BOX)) > 127
    fs = np.asarray(f1024.resize((s, s), Image.BOX)) > 127
    print(f'mip {s}: footprint covered (mask>0.5) {(ms & fs).sum()/max(fs.sum(), 1):.3f}')
