"""Cut the tree of his picture (mj-15) into numbers for the main screen: the paint, and the cards to carry it; and his
sky, as a smooth fit of its colour.

    python3 scene/trace_tree.py [check.jpg]
        reads framing/mj-15-hd.jpg and the tree's outline in scene/assets/tree.webp; writes field-assets/tree-paint.webp,
        field-assets/tree-trace.json and field-assets/sky.json (and, if asked, a picture to check the cut by eye)

The paint is his tree as it is in his picture, freed from his sky: the colour of each pixel, and how much of it is tree —
where the sky shows through the crown it is see-through, so our sky shows there. The cards are spots on a grid over the
tree, each with how far it is from the crown's outline and how thick the wood is under it. The field page sets each card
at its own depth along its ray from the camera and paints it with the picture cast from that camera (the way film paints
3D sets from a matte painting): at rest the tree is exactly his tree, and it is a real 3D tree — it sways in the wind,
thick wood hardly and the crown's edges most, and it casts its shadow.
"""
import json
import pathlib
import sys

import cv2
import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
SRC, PICTURE = HERE / 'assets' / 'tree.webp', HERE.parent / 'framing' / 'mj-15-hd.jpg'
OUT, PAINT = HERE.parent / 'field-assets' / 'tree-trace.json', HERE.parent / 'field-assets' / 'tree-paint.webp'
SKY = HERE.parent / 'field-assets' / 'sky.json'
PIC = (1536, 2752)                        # his picture; the tree's piece of it is its top-left corner
TRUNK_BASE = (228, 1889)
STEP, JITTER, REACH = 20, 3, 19.5          # cards: a grid, a little shaken; every bit of tree within REACH px of a card's middle


def sky_fit():
    """His sky's colour over his whole picture, as a smooth function of where it is (x, y from 0 to 1): the sky there
    is fitted with a cubic, leaving out the tree, the falling leaves and the field."""
    pic = np.asarray(Image.open(PICTURE).convert('RGB')).astype(np.float32)/255
    H, W, _ = pic.shape
    a = np.zeros((H, W), np.float32)
    t = np.asarray(Image.open(SRC).convert('RGBA'))[..., 3].astype(np.float32)/255
    a[:t.shape[0], :t.shape[1]] = t
    tree = cv2.dilate((a > 0.05).astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
    lum = pic @ np.array([0.299, 0.587, 0.114], np.float32)
    sky = (pic[..., 2] > pic[..., 0] + 0.08) & (lum > 0.2) & ~tree
    yy, xx = np.mgrid[0:H, 0:W]
    X, Y = (xx/W).ravel(), (yy/H).ravel()
    pick = np.nonzero(sky.ravel())[0][::5]
    x, y = X[pick], Y[pick]
    A = np.stack([np.ones_like(x), x, y, x*x, x*y, y*y, x*x*x, x*x*y, x*y*y, y*y*y], -1)
    coef = np.linalg.lstsq(A, pic.reshape(-1, 3)[pick], rcond=None)[0]
    print(f'sky: {len(pick)} px fitted, mean error {np.abs(A @ coef - pic.reshape(-1, 3)[pick]).mean():.4f}')
    SKY.write_text(json.dumps({'picture': PIC, 'terms': '1 x y xx xy yy xxx xxy xyy yyy',
                               'rgb': [[round(float(v), 5) for v in c] for c in coef]}, separators=(',', ':')))


def main():
    sky_fit()
    alpha = np.asarray(Image.open(SRC).convert('RGBA'))[..., 3].astype(np.float32)/255
    rgb = np.asarray(Image.open(PICTURE).convert('RGB')).astype(np.float32)[:alpha.shape[0], :alpha.shape[1]]/255
    inside = alpha > 0.5
    lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    # the wood: the dark of the picture inside the tree — trunk and branches are near black, leaves orange
    dark = (inside & (lum < 0.16)).astype(np.uint8)
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(dark, connectivity=8)
    keep = np.zeros(n, bool)
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        keep[i] = area >= 30 and max(bw, bh) >= 14                    # long enough to be wood, not a shadow between leaves
    wood = keep[lab].astype(np.uint8)
    wood = cv2.morphologyEx(wood, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    wood = (cv2.GaussianBlur(wood.astype(np.float32), (5, 5), 0) > 0.45).astype(np.uint8)
    # how thick the wood is around each of its pixels: the half-width of the trunk or branch it belongs to
    half = cv2.dilate(cv2.distanceTransform(wood, cv2.DIST_L2, 5), np.ones((11, 11), np.uint8))*wood

    # the sky behind the tree, as a smooth colour field fitted to the sky around it and in its gaps
    yy, xx = np.mgrid[0:rgb.shape[0], 0:rgb.shape[1]].astype(np.float32)
    basis = lambda x, y: np.stack([np.ones_like(x), x, y, x*x, x*y, y*y, y*y*y], -1)
    X, Y = xx/1000, yy/1000
    skyish = (rgb[..., 2] > rgb[..., 0] + 0.08) & (lum > 0.25) & (yy < 1800)
    pick = np.nonzero(skyish.ravel())[0][::7]
    A = basis(X.ravel()[pick], Y.ravel()[pick])
    coef = np.linalg.lstsq(A, rgb.reshape(-1, 3)[pick], rcond=None)[0]
    sky = (basis(X, Y) @ coef).astype(np.float32)
    print(f'sky fit: mean error {np.abs(A @ coef - rgb.reshape(-1, 3)[pick]).mean():.3f}')
    # how much of each pixel is tree: far from the sky's colour there — dark twigs against the sky stay, gaps go
    key = np.clip((np.linalg.norm(rgb - sky, axis=-1) - 0.06)/0.16, 0, 1)
    key = key*key*(3 - 2*key)
    tree = np.clip(alpha, 0, 1)*key
    tree = np.maximum(tree, cv2.GaussianBlur(wood.astype(np.float32), (3, 3), 0)*inside)   # the wood is solid
    # the tree's own colour where it is mixed with the sky at its edges, and its nearest colour beyond them, so nothing
    # of his sky is carried into ours
    k = np.maximum(key, 0.08)[..., None]
    fg = np.clip((rgb - (1 - k)*sky)/k, 0, 1)
    fg = np.where(tree[..., None] > 0.97, rgb, fg)
    solid = (tree > 0.5).astype(np.uint8)
    _, near = cv2.distanceTransformWithLabels(1 - solid, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    near = np.argwhere(solid == 1)[near - 1]                       # the labels count the solid pixels in reading order
    fg = np.where((tree < 0.5)[..., None], fg[near[..., 0], near[..., 1]], fg)
    paint = np.dstack([fg, tree]).clip(0, 1)
    Image.fromarray((paint*255 + 0.5).astype(np.uint8), 'RGBA').save(PAINT, quality=92, alpha_quality=100, method=6)
    print(f'paint {PAINT.stat().st_size//1024} KB → {PAINT}')

    # the cards: a grid where the tree is near, a little shaken; each knows how far it is from the crown's outline (deep
    # in the crown it moves less) and how thick the wood under it is (thick wood hardly moves)
    totree = cv2.distanceTransform(1 - solid, cv2.DIST_L2, 5)
    edge = cv2.distanceTransform(inside.astype(np.uint8), cv2.DIST_L2, 5)
    rng = np.random.default_rng(15)
    cards, marks = [], np.ones_like(solid)
    hh, ww = solid.shape
    for y in range(STEP//2, hh + STEP//2, STEP):
        for x in range(STEP//2, ww + STEP//2, STEP):
            px = min(max(x + int(rng.integers(-JITTER, JITTER + 1)), 0), ww - 1)
            py = min(max(y + int(rng.integers(-JITTER, JITTER + 1)), 0), hh - 1)
            if totree[py, px] > REACH:
                continue
            cards.append([px, py, round(float(edge[py, px]), 1), round(float(half[py, px]), 1)])
            marks[py, px] = 0
    gap = cv2.distanceTransform(marks, cv2.DIST_L2, 5)[solid == 1]
    print(f'cards {len(cards)}; farthest bit of tree from a card {gap.max():.1f} px (must be ≤ {REACH})')
    data = {'picture': PIC, 'trunkBase': TRUNK_BASE, 'step': STEP, 'edgeMax': round(float(edge.max()), 1),
            'paint': [int(alpha.shape[1]), int(alpha.shape[0])], 'cards': cards}
    OUT.write_text(json.dumps(data, separators=(',', ':')))
    print(f'{OUT.stat().st_size//1024} KB → {OUT}')
    if len(sys.argv) < 2:
        return
    # a picture to check by eye: the tree over magenta, the wood marked blue, every third card a dot
    view = paint[..., :3]*paint[..., 3:] + np.array([0.8, 0, 0.8])*(1 - paint[..., 3:])
    view[wood == 1] = view[wood == 1]*0.5 + np.array([0.25, 0.45, 1])*0.5
    view = (view*255).astype(np.uint8)
    for x, y, *_ in cards[::3]:
        cv2.circle(view, (int(x), int(y)), 2, (255, 255, 255), -1)
    Image.fromarray(view).save(sys.argv[1], quality=85)


if __name__ == '__main__':
    main()
