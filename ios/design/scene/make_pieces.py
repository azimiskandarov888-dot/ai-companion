"""Turn mj-15 and the AI cuts into the scene's pieces, with nothing missing behind them.

  python3 make_pieces.py

Reads  ../framing/mj-15-hd.jpg          the sharp picture (1536×2752)
       layers/layer-2.png               Qwen field layer — what the field looks like behind the trunk
       masks/{tree,grass,pampas-grass}  SAM 3 shapes, cut from the sharp picture
       pieces/piece-*.png               SAM 2 pieces of the near grass (crops/near-band.jpg, from y=1950)
Writes assets/sky.jpg      whole sky: the parts behind the tree, the grass and the flying leaves filled in
       assets/field.webp   the field, filled behind the trunk and under the plumes we lift off
       assets/tree.webp    the tree with soft edges
       assets/heads.webp   near plume heads, one atlas; each sways around its own stem
       assets/leaves.webp  leaves cut out of the sky, for the falling-leaf particles
       assets/layout.json  where every piece sits in the picture
Everything visible stays the sharp picture's own pixels; the AI layers only give
shapes and the hidden parts.
"""
import json, pathlib

import cv2
import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).parent
OUT = HERE / "assets"
BAND_Y = 1950          # crops/near-band.jpg starts here
FIELD_Y = 1500         # the field texture starts here (the skyline is lower, this leaves room to sway)
TREE_BOX = (0, 0, 1190, 1900)


def load(path, mode="RGB"):
    return np.asarray(Image.open(path).convert(mode)).astype(np.float32) / 255


def mask(path, size=None):
    m = Image.open(path).convert("L")
    if size and m.size != size:
        m = m.resize(size, Image.BILINEAR)
    return np.asarray(m).astype(np.float32) / 255


def push_pull(rgb, known):
    """Fill unknown pixels smoothly from the known ones (a pyramid: shrink, fill, grow back)."""
    levels, c, w = [], rgb * known[..., None], known.copy()
    while min(w.shape) > 2:
        levels.append((c, w))
        size = (max(1, w.shape[1] // 2), max(1, w.shape[0] // 2))
        c, w = cv2.resize(c, size, interpolation=cv2.INTER_AREA), cv2.resize(w, size, interpolation=cv2.INTER_AREA)
    fill = c / np.maximum(w, 1e-6)[..., None]
    for c, w in reversed(levels):
        up = cv2.resize(fill, (w.shape[1], w.shape[0]), interpolation=cv2.INTER_LINEAR)
        a = np.clip(w * 2, 0, 1)[..., None]
        fill = np.where(w[..., None] > 0, c / np.maximum(w, 1e-6)[..., None], up) * a + up * (1 - a)
    return fill


def guided(guide, p, r, eps):
    """Soft edges for a hard mask, following the picture's own edges (guided filter)."""
    box = lambda x: cv2.boxFilter(x, -1, (2 * r + 1, 2 * r + 1))
    mi, mp = box(guide), box(p)
    a = (box(guide * p) - mi * mp) / (box(guide * guide) - mi * mi + eps)
    b = mp - a * mi
    return np.clip(box(a) * guide + box(b), 0, 1)


def dilate(m, px):
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * px + 1, 2 * px + 1))
    return cv2.dilate(m.astype(np.uint8), k) > 0


def pack(sprites, width=2048, pad=4):
    """Shelf-pack sprites (H×W×4 arrays) into one atlas; returns the atlas and each sprite's rect."""
    order = sorted(range(len(sprites)), key=lambda i: -sprites[i].shape[0])
    rects, x, y, shelf = [None] * len(sprites), pad, pad, 0
    for i in order:
        h, w = sprites[i].shape[:2]
        if x + w + pad > width:
            x, y, shelf = pad, y + shelf + pad, 0
        rects[i] = (x, y, w, h)
        x, shelf = x + w + pad, max(shelf, h)
    atlas = np.zeros((y + shelf + pad, width, 4), np.float32)
    for s, (x, y, w, h) in zip(sprites, rects):
        atlas[y:y + h, x:x + w] = s
    return atlas, rects


def save_rgba(path, rgba, quality=88):
    Image.fromarray((np.clip(rgba, 0, 1) * 255 + .5).astype(np.uint8), "RGBA").save(path, quality=quality, method=6)


def main():
    OUT.mkdir(exist_ok=True)
    img = load(HERE / "../framing/mj-15-hd.jpg")
    H, W = img.shape[:2]
    size = (W, H)
    blue_red = img[..., 2] - img[..., 0]            # sky is blue, leaves orange, plumes cream: one channel tells them apart
    luma = img @ np.array([.299, .587, .114], np.float32)

    # ---------- shapes ----------
    tree = guided(blue_red, mask(HERE / "masks/tree-mask_000.png", size), 3, 1e-4)
    field = guided(blue_red, np.maximum(mask(HERE / "masks/grass-mask_000.png", size),
                                        mask(HERE / "masks/pampas-grass-mask_000.png", size)), 3, 1e-4)
    tree[tree < .03], field[field < .03] = 0, 0
    n, lab, stats, _ = cv2.connectedComponentsWithStats((field > .3).astype(np.uint8), 8)
    body = lab == 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    field *= dilate(body, 3)                          # drop leaves the grass shape caught in the air

    # ---------- sky: fill behind tree and field, then find the flying leaves and fill them too ----------
    hole = dilate(tree > .02, 6) | dilate(field > .02, 6)
    first = push_pull(img, (~hole).astype(np.float32))
    smooth = cv2.medianBlur((np.clip(first, 0, 1) * 255).astype(np.uint8), 51).astype(np.float32) / 255
    diff = np.abs(img - smooth).max(-1)                # what isn't sky: flying leaves and thin twigs
    dark = (smooth - img).mean(-1)                     # twigs are darker than the sky around them
    n, lab, stats, _ = cv2.connectedComponentsWithStats((((diff > .09) | (dark > .05)) & ~hole).astype(np.uint8), 8)
    near_tree = dilate(tree > .5, 25)
    leaves_mask, twigs = np.zeros((H, W), bool), np.zeros((H, W), bool)
    leaf_boxes = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < 12:
            continue
        part = lab[y:y + h, x:x + w] == i
        if near_tree[y:y + h, x:x + w][part].any():      # touches the crown: a twig, it sways with the tree
            twigs[y:y + h, x:x + w] |= part
        elif area <= 4000:
            leaves_mask[y:y + h, x:x + w] |= part
            if 60 <= area and max(w, h) <= 90:
                leaf_boxes.append((x, y, w, h, area))
    twig_a = np.clip(np.maximum(diff - .03, dark * 1.6) / .16, 0, 1) * dilate(twigs, 2)
    tree = np.maximum(tree, twig_a)
    hole |= dilate(twigs, 5) | dilate(tree > .02, 10)
    filled = hole | dilate(leaves_mask, 4)
    sky = push_pull(img, (~filled).astype(np.float32))
    # the picture's sky has a fine grain; give the filled parts the same grain
    grain = (img - cv2.GaussianBlur(img, (0, 0), 2))[~filled].std(0)
    noise = np.random.default_rng(7).normal(0, 1, sky.shape).astype(np.float32)
    sky = np.where(filled[..., None], sky + noise * grain, img)
    smooth = sky                                         # the clean sky, for taking the blue out of leaf edges
    Image.fromarray((np.clip(sky, 0, 1) * 255 + .5).astype(np.uint8)).save(OUT / "sky.jpg", quality=90)

    # ---------- leaves: cut out of the sky, with the blue taken out of their edges ----------
    leaf_sprites, leaf_info = [], []
    for x, y, w, h, area in sorted(leaf_boxes, key=lambda b: -b[4])[:14]:
        x0, y0, x1, y1 = max(0, x - 3), max(0, y - 3), min(W, x + w + 3), min(H, y + h + 3)
        a = np.clip((diff[y0:y1, x0:x1] - .03) / .16, 0, 1)
        a *= dilate(leaves_mask[y0:y1, x0:x1], 2)
        s = smooth[y0:y1, x0:x1]
        col = np.clip((img[y0:y1, x0:x1] - (1 - a[..., None]) * s) / np.maximum(a, .05)[..., None], 0, 1)
        leaf_sprites.append(np.dstack([col, a]))
        leaf_info.append({"x": int(x0), "y": int(y0), "w": int(x1 - x0), "h": int(y1 - y0)})
    atlas, rects = pack(leaf_sprites, width=512)
    save_rgba(OUT / "leaves.webp", atlas, 92)
    for info, r in zip(leaf_info, rects):
        info["atlas"] = list(map(int, r))

    # ---------- near plume heads: the SAM 2 pieces that are whole white heads ----------
    band = img[BAND_Y:]
    bh_, bw_ = band.shape[:2]
    band_luma = luma[BAND_Y:]
    cand = []
    hsv = cv2.cvtColor((band * 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32) / 255
    for f in sorted((HERE / "pieces").glob("piece-*.png")):
        m = mask(f, (bw_, bh_)) > .5
        area = int(m.sum())
        if not 500 <= area <= 40000:
            continue
        ys, xs = np.nonzero(m)
        x0, y0, x1, y1 = xs.min(), ys.min(), xs.max(), ys.max()
        if y0 <= 2:                              # cut by the band's top: not a whole head
            continue
        white = ((hsv[..., 2][m] > .78) & (hsv[..., 1][m] < .3)).mean()
        if white < .4:
            continue
        cand.append((area, f, m, (x0, y0, x1, y1)))
    taken = np.zeros((bh_, bw_), bool)
    chosen = []
    for area, f, m, (x0, y0, x1, y1) in sorted(cand, key=lambda c: c[0]):
        if (m & taken).sum() > .2 * area:
            continue
        taken |= m
        chosen.append((f.name, m, (x0, y0, x1, y1)))
    # the white plumes SAM 2 left joined together: split them apart with a watershed, so every
    # near plume can swing — none left frozen beside a moving neighbour
    white = ((hsv[..., 2] > .66) & (hsv[..., 1] < .38) & ~dilate(taken, 3)).astype(np.uint8)
    white = cv2.morphologyEx(white, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    dist = cv2.distanceTransform(white, cv2.DIST_L2, 5)
    peaks = ((dist >= cv2.dilate(dist, np.ones((31, 31), np.uint8))) & (dist > 6)).astype(np.uint8)
    n, markers = cv2.connectedComponents(cv2.dilate(peaks, np.ones((5, 5), np.uint8)))
    markers = markers + 1
    markers[(cv2.dilate(white, np.ones((7, 7), np.uint8)) > 0) & (markers == 1)] = 0   # unknown: let the watershed decide
    markers = cv2.watershed((band * 255).astype(np.uint8)[..., ::-1].copy(), markers.astype(np.int32))
    for lab in range(2, markers.max() + 1):
        m = (markers == lab) & (white > 0)
        area = int(m.sum())
        if not 500 <= area <= 30000:
            continue
        ys, xs = np.nonzero(m)
        x0, y0, x1, y1 = xs.min(), ys.min(), xs.max(), ys.max()
        if y0 <= 2 or y1 - y0 < 22:
            continue
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)) > 0
        taken |= m
        chosen.append((f"split-{lab}", m, (x0, y0, x1, y1)))
    heads, head_sprites = [], []
    for name, m, (x0, y0, x1, y1) in chosen:
        x0, y0 = max(0, x0 - 4), max(0, y0 - 4)
        x1, y1 = min(bw_, x1 + 5), min(bh_, y1 + 5)
        soft = guided(band_luma[y0:y1, x0:x1], cv2.GaussianBlur(m[y0:y1, x0:x1].astype(np.float32), (0, 0), 1.2), 2, 1e-3)
        head_sprites.append(np.dstack([band[y0:y1, x0:x1], soft]))
        ys, xs = np.nonzero(m[y0:y1, x0:x1])
        foot = xs[ys > ys.max() - .25 * (ys.max() - ys.min() + 1)].mean() + x0
        h = y1 - y0
        heads.append({"src": name, "x": int(x0), "y": int(y0 + BAND_Y), "w": int(x1 - x0), "h": int(h),
                      "pivot": [round(float(foot), 1), round(float(y1 + BAND_Y + 1.0 * h), 1)]})
    atlas, rects = pack(head_sprites)
    save_rgba(OUT / "heads.webp", atlas, 90)
    for hd, r in zip(heads, rects):
        hd["atlas"] = list(map(int, r))

    # ---------- field: sharp where seen, Qwen behind the trunk, filled under the lifted heads ----------
    q = load(HERE / "layers/layer-2.png", "RGBA")
    q = cv2.resize(q, size, interpolation=cv2.INTER_LANCZOS4)
    q_rgb, q_a = np.clip(q[..., :3], 0, 1), np.clip(q[..., 3], 0, 1)
    both = (field > .95) & (q_a > .95) & ~dilate(tree > .02, 30)
    for c in range(3):                                # match Qwen's colours to the sharp picture
        A = np.stack([q_rgb[..., c][both], np.ones(both.sum(), np.float32)], 1)
        g, o = np.linalg.lstsq(A, img[..., c][both], rcond=None)[0]
        q_rgb[..., c] = np.clip(q_rgb[..., c] * g + o, 0, 1)
    behind = dilate(tree > .02, 10).astype(np.float32)
    behind[:1550] = 0
    behind = cv2.GaussianBlur(behind, (0, 0), 3)
    alpha = np.maximum(field, q_a * behind)
    n, lab, stats, _ = cv2.connectedComponentsWithStats((alpha > .3).astype(np.uint8), 8)
    alpha *= dilate(lab == 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA]), 3)   # Qwen's layer has flying leaves too
    use_q = (behind * (1 - field))[..., None]            # Qwen only where the field itself is hidden
    rgb = img * (1 - use_q) + q_rgb * use_q
    lifted = np.zeros((H, W), bool)
    lifted[BAND_Y:] = dilate(taken, 2)
    # behind a lifted plume: more grass, deeper and in shade — the field's own texture from a little
    # further along, darkened and softened, over the golden colour of the stems around it
    stems = (alpha > .5) & ~lifted & (luma < .55)
    base = push_pull(rgb, stems.astype(np.float32))
    deeper = cv2.GaussianBlur(np.roll(rgb, (37, -29), (0, 1)), (0, 0), 1.2)
    under = np.clip(base * .4 + deeper * .6 * .72, 0, 1)
    edge = cv2.GaussianBlur(lifted.astype(np.float32), (0, 0), 1.5)[..., None]
    rgb = rgb * (1 - edge) + under * edge
    rgb = np.where((alpha < .5)[..., None], push_pull(rgb, (alpha >= .5).astype(np.float32)), rgb)   # no dark fringe
    save_rgba(OUT / "field.webp", np.dstack([rgb, alpha])[FIELD_Y:], 90)

    # ---------- tree ----------
    x0, y0, x1, y1 = TREE_BOX
    t_rgb = np.where((tree < .5)[..., None], push_pull(img, (tree >= .5).astype(np.float32)), img)
    save_rgba(OUT / "tree.webp", np.dstack([t_rgb, tree])[y0:y1, x0:x1], 90)

    trunk = mask(HERE / "masks/tree-trunk-mask_000.png", size) > .5
    ys, xs = np.nonzero(trunk)
    layout = {
        "size": [W, H],
        "field": {"y": FIELD_Y, "h": H - FIELD_Y},
        "tree": {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0,
                 "trunkBase": [round(float(xs[ys > ys.max() - 40].mean()), 1), int(ys.max())],
                 "trunkTop": [round(float(xs[ys < ys.min() + 40].mean()), 1), int(ys.min())]},
        "skyline": [int(np.argmax(field[:, x] > .5)) if (field[:, x] > .5).any() else H for x in range(0, W, 32)],
        "heads": heads,
        "leaves": leaf_info,
        "atlas": {"heads": [atlas.shape[1], atlas.shape[0]]},
    }
    la = np.asarray(Image.open(OUT / "leaves.webp")).shape
    layout["atlas"]["leaves"] = [la[1], la[0]]
    (OUT / "layout.json").write_text(json.dumps(layout, indent=1))
    print(f"sky, field, tree · {len(heads)} plume heads · {len(leaf_info)} leaves")


if __name__ == "__main__":
    main()
