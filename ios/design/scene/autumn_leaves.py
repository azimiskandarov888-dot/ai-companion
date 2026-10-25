"""Turn a photographed green leaf texture to the oranges and ambers of his tree, keeping every leaf's own light and dark,
veins and edges.

    python3 scene/autumn_leaves.py <leaves_diff.jpg> <out.jpg>

Each leaf pixel keeps its brightness relative to the leaves around it; its colour is taken from his palette by that
brightness (deep amber in its darker parts, orange, peach where it is light), with slow patches of variation so not every
leaf is the same.
"""
import sys

import cv2
import numpy as np
from PIL import Image

# his tree's leaves, linear: from the darker parts of a leaf to the lightest
PALETTE = np.array([(0.30, 0.07, 0.012), (0.62, 0.20, 0.035), (0.80, 0.36, 0.08), (0.92, 0.55, 0.20)], np.float32)


def main():
    src, out = sys.argv[1], sys.argv[2]
    c = np.asarray(Image.open(src).convert('RGB')).astype(np.float32)/255
    lin = np.where(c <= 0.04045, c/12.92, ((c + 0.055)/1.055)**2.4)
    lum = lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    leafy = (lum > 0.012).astype(np.float32)
    mean = cv2.GaussianBlur(lum*leafy, (0, 0), 25)/np.maximum(cv2.GaussianBlur(leafy, (0, 0), 25), 1e-4)
    t = np.clip(0.42 + 0.55*np.log2(np.maximum(lum, 1e-4)/np.maximum(mean, 1e-4)), 0, 1)
    rng = np.random.default_rng(3)
    patch = cv2.GaussianBlur(rng.random(lum.shape).astype(np.float32), (0, 0), 40)
    patch = (patch - patch.mean())/(patch.std() + 1e-6)
    t = np.clip(t + 0.12*patch, 0, 1)*3
    i = np.minimum(t.astype(int), 2)
    col = PALETTE[i] + (PALETTE[i + 1] - PALETTE[i])*(t - i)[..., None]
    col = np.where(leafy[..., None] > 0, col, lin)                 # what is not leaf stays as it was
    srgb = np.where(col <= 0.0031308, col*12.92, 1.055*np.power(np.clip(col, 0, 1), 1/2.4) - 0.055)
    Image.fromarray((srgb*255 + 0.5).astype(np.uint8)).save(out, quality=92)
    print('→', out)


if __name__ == '__main__':
    main()
