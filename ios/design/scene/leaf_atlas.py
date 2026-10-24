"""The leaves for the 3D tree: nine photographed maple leaves (ambientCG LeafSet027, CC0) recoloured to the oranges and
ambers of his tree, in one small atlas the tree's leaf cards share.

    python3 scene/leaf_atlas.py <LeafSet027_2K folder>
        writes field-assets/leaf-color.webp (colour, and the leaf's outline in alpha) and field-assets/leaf-normal.webp
        (the leaf's surface: veins and curl, x right, y up; and in alpha how much light it lets through — its scattering):
        four sprays of 10–14 leaves on a twig, the way game trees fill their crowns (one card carries a whole spray)

The photographs keep their own detail — veins, curl, light and dark — only their colour is moved to his palette, each leaf
a little different, the way autumn leaves on one tree are.
"""
import pathlib
import sys

import cv2
import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / 'field-assets'
SIZE = 1024                                # 3 × 3 cells; a leaf is drawn about 15 px tall on the phone, so this is plenty
# his tree's leaves, linear: deep amber in the shade of a leaf, orange, and peach where it catches the light
PALETTE = [(0.62, 0.20, 0.035), (0.76, 0.30, 0.06), (0.82, 0.38, 0.09), (0.70, 0.25, 0.045), (0.85, 0.42, 0.11),
           (0.78, 0.33, 0.07), (0.66, 0.22, 0.04), (0.80, 0.36, 0.08), (0.84, 0.40, 0.10)]


def load(folder, name, mode):
    return np.asarray(Image.open(next(folder.glob(f'*_{name}.jpg'))).convert(mode)).astype(np.float32)/255


def main():
    src = pathlib.Path(sys.argv[1])
    col, opa, nor, sca = load(src, 'Color', 'RGB'), load(src, 'Opacity', 'L'), load(src, 'NormalGL', 'RGB'), load(src, 'Scattering', 'L')
    lin = np.where(col <= 0.04045, col/12.92, ((col + 0.055)/1.055)**2.4)
    lum = lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    h, w = opa.shape
    out_c, out_n = np.zeros((SIZE, SIZE, 4), np.float32), np.zeros((SIZE, SIZE, 4), np.float32)
    cell = SIZE//3
    for i in range(3):
        for j in range(3):
            ys, xs = slice(i*h//3, (i + 1)*h//3), slice(j*w//3, (j + 1)*w//3)
            m = opa[ys, xs] > 0.5
            # its own light and dark, around its own middle: the detail we keep
            l = lum[ys, xs]; mean = l[m].mean() if m.any() else 1
            detail = np.clip(l/mean, 0.45, 1.35)[..., None]
            k = i*3 + j
            c = np.array(PALETTE[k], np.float32)*detail
            c = np.where(c <= 0.0031308, c*12.92, 1.055*np.power(np.clip(c, 0, 1), 1/2.4) - 0.055)
            rgba = np.dstack([c, opa[ys, xs]])
            nrm = np.dstack([nor[ys, xs], sca[ys, xs]])
            out_c[i*cell:(i + 1)*cell, j*cell:(j + 1)*cell] = cv2.resize(rgba, (cell, cell), interpolation=cv2.INTER_AREA)
            out_n[i*cell:(i + 1)*cell, j*cell:(j + 1)*cell] = cv2.resize(nrm, (cell, cell), interpolation=cv2.INTER_AREA)
    # beyond each leaf, its own edge colour, so filtering never brings in black (and alpha never 0 under the normals)
    solid = (out_c[..., 3] > 0.5).astype(np.uint8)
    _, near = cv2.distanceTransformWithLabels(1 - solid, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    near = np.argwhere(solid == 1)[near - 1]
    out_c[..., :3] = np.where((solid == 0)[..., None], out_c[near[..., 0], near[..., 1], :3], out_c[..., :3])
    out_n[..., :3] = np.where((solid == 0)[..., None], out_n[near[..., 0], near[..., 1], :3], out_n[..., :3])
    out_n[..., 3] = np.maximum(out_n[..., 3], 0.02)
    sprays(out_c, out_n)
    print('leaf atlas →', OUT / 'leaf-color.webp', (OUT / 'leaf-color.webp').stat().st_size//1024, 'KB;', OUT / 'leaf-normal.webp', (OUT / 'leaf-normal.webp').stat().st_size//1024, 'KB')


def sprays(leaf_c, leaf_n, size=1024, seed=5):
    """Four sprays (2 × 2 cells): a twig from the bottom middle of the cell, leaves along it on both sides and at its tip,
    each turned and sized its own way; where a leaf lies over another, the one below is a little in its shade."""
    rng = np.random.default_rng(seed)
    cell, lc = size//2, leaf_c.shape[0]//3
    col, nor = np.zeros((size, size, 4), np.float32), np.zeros((size, size, 4), np.float32)
    nor[..., :3] = (0.5, 0.5, 1.0); nor[..., 3] = 0.02
    for v in range(4):
        oy, ox = (v//2)*cell, (v % 2)*cell
        c, n = np.zeros((cell, cell, 4), np.float32), np.zeros((cell, cell, 4), np.float32)
        n[..., :3] = (0.5, 0.5, 1.0)
        x, y, a = cell*0.5, cell*0.98, -np.pi/2 + rng.uniform(-0.25, 0.25)   # the twig, from the bottom, upward
        twig = []
        for step in range(8):
            nx, ny = x + np.cos(a)*cell*0.08, y + np.sin(a)*cell*0.085
            twig.append(((x, y), (nx, ny), 3.2 - 0.25*step)); x, y = nx, ny; a += rng.uniform(-0.25, 0.25)
        for (x0, y0), (x1, y1), w in twig:                          # the twig itself, thin and brown
            cv2.line(c, (int(x0), int(y0)), (int(x1), int(y1)), (0.16, 0.10, 0.06, 1), max(1, int(w)), cv2.LINE_AA)
        spots = [(p1, ang) for (p0, p1, _), k in zip(twig, range(8)) for ang in (-1, 1) if k > 1 and rng.random() < 0.8]
        spots.append((twig[-1][1], 0))
        rng.shuffle(spots)
        for (px, py), side in spots:
            k = rng.integers(9); ci, cj = divmod(int(k), 3)
            lcol, lnor = leaf_c[ci*lc:(ci + 1)*lc, cj*lc:(cj + 1)*lc], leaf_n[ci*lc:(ci + 1)*lc, cj*lc:(cj + 1)*lc]
            s = rng.uniform(0.3, 0.42)*cell/lc
            ang = np.degrees(-np.pi/2 - a) + side*rng.uniform(35, 75) + rng.uniform(-15, 15)   # leaf tip away from the twig
            M = cv2.getRotationMatrix2D((lc/2, lc*0.97), ang, s)                    # about its stalk
            M[0, 2] += px - lc/2; M[1, 2] += py - lc*0.97
            wc = cv2.warpAffine(lcol, M, (cell, cell), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
            wn = cv2.warpAffine(lnor, M, (cell, cell), flags=cv2.INTER_LINEAR, borderValue=(0.5, 0.5, 1, 0))
            t = np.radians(ang)                                    # its surface turns with it
            nx, ny = wn[..., 0]*2 - 1, wn[..., 1]*2 - 1
            wn[..., 0], wn[..., 1] = (nx*np.cos(t) - ny*np.sin(t))*0.5 + 0.5, (nx*np.sin(t) + ny*np.cos(t))*0.5 + 0.5
            al = wc[..., 3:4]
            c[..., :3] *= 1 - 0.18*al                              # the leaf below is a little in this one's shade
            c[..., :3] = wc[..., :3]*al + c[..., :3]*(1 - al); c[..., 3:] = al + c[..., 3:]*(1 - al)
            n[..., :4] = wn*al + n[..., :4]*(1 - al)
        col[oy:oy + cell, ox:ox + cell], nor[oy:oy + cell, ox:ox + cell] = c, n
    solid = (col[..., 3] > 0.5).astype(np.uint8)
    _, near = cv2.distanceTransformWithLabels(1 - solid, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    near = np.argwhere(solid == 1)[near - 1]
    col[..., :3] = np.where((solid == 0)[..., None], col[near[..., 0], near[..., 1], :3], col[..., :3])
    nor[..., 3] = np.maximum(nor[..., 3], 0.02)
    Image.fromarray((col.clip(0, 1)*255 + 0.5).astype(np.uint8), 'RGBA').save(OUT / 'leaf-color.webp', quality=92, alpha_quality=100, exact=True)
    Image.fromarray((nor.clip(0, 1)*255 + 0.5).astype(np.uint8), 'RGBA').save(OUT / 'leaf-normal.webp', quality=95, alpha_quality=100, exact=True)


if __name__ == '__main__':
    main()
