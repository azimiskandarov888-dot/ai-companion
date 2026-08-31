#!/usr/bin/env python3
"""Cut the magenta out of generated art, and measure what the engine needs.

Generated assets arrive as a flat object on a magenta ground. Three things have
to happen before the engine can place one: the magenta has to go, the leftover
magenta bleeding into every anti-aliased edge has to be neutralised, and
somebody has to record where the object's feet are — because the engine stands
things on the ground by that row, not by the bottom of the file.

Keying is done in hue rather than by distance to one sampled colour: some plates
have a gradient background, and a single reference colour misses half of it. The
foreground is green and blue, the ground is magenta, and those sit far enough
apart on the wheel that one threshold separates them everywhere in the frame.

    python3 tools/cut_assets.py                 # assets/raw -> assets/cut
    python3 tools/cut_assets.py --only tree     # just the ones matching
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

RAW = Path("assets/raw")
CUT = Path("assets/cut")

# Magenta sits at ~300-330°. Everything we draw is green through blue, 80-260°.
# A generous window still leaves a wide empty gap on either side.
BG_HUE = 315.0
HUE_WINDOW = 62.0      # degrees either side of BG_HUE counted as background
MIN_SAT = 0.16         # near-grey pixels are never background, whatever the hue
SOFT = 14.0            # degrees of feathering at the edge of the window


def _hsv(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Vectorised RGB->HSV. Hue in degrees, s and v in 0..1."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = rgb.max(-1)
    mn = rgb.min(-1)
    d = mx - mn
    h = np.zeros_like(mx)
    nz = d > 1e-6
    ir = nz & (mx == r)
    ig = nz & (mx == g) & ~ir
    ib = nz & (mx == b) & ~ir & ~ig
    with np.errstate(invalid="ignore", divide="ignore"):
        h[ir] = (60 * ((g - b)[ir] / d[ir])) % 360
        h[ig] = (60 * ((b - r)[ig] / d[ig]) + 120) % 360
        h[ib] = (60 * ((r - g)[ib] / d[ib]) + 240) % 360
        s = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0.0)
    return h, s, mx


def _alpha(rgb: np.ndarray) -> np.ndarray:
    """1 where the object is, 0 where the magenta is, feathered between."""
    h, s, _ = _hsv(rgb)
    dist = np.abs((h - BG_HUE + 180) % 360 - 180)          # degrees from magenta
    # 0 at the centre of the window, 1 once we are SOFT degrees outside it
    a = np.clip((dist - HUE_WINDOW) / SOFT, 0.0, 1.0)
    a[s < MIN_SAT] = 1.0                                   # greys are never the ground
    return a


def _despill(rgb: np.ndarray, a: np.ndarray) -> np.ndarray:
    """Take the magenta back out of the edge pixels it bled into.

    An anti-aliased edge is part object, part ground, so every boundary pixel
    carries some magenta. Left alone it shows up as a pink halo the moment the
    sprite is composited over anything that is not magenta. Magenta is red and
    blue with no green, so clamping red and blue toward green removes it without
    touching colours that were meant to be there.
    """
    out = rgb.copy()
    edge = (a > 0.02) & (a < 0.985)
    if not edge.any():
        return out
    g = out[..., 1]
    cap = g + 0.06
    for c in (0, 2):
        ch = out[..., c]
        over = edge & (ch > cap)
        ch[over] = cap[over]
    return out


def _measure(a: np.ndarray) -> dict:
    """Bounding box, plus the row the object actually stands on."""
    solid = a > 0.5
    rows = np.where(solid.any(1))[0]
    cols = np.where(solid.any(0))[0]
    if not len(rows) or not len(cols):
        return {}
    top, bottom = int(rows[0]), int(rows[-1])
    left, right = int(cols[0]), int(cols[-1])

    # Feet, not the bounding box: find the lowest row carrying a real amount of
    # object, so one stray anti-aliased pixel does not decide where a tree stands.
    per_row = solid.sum(1)
    floor = max(1, int(0.004 * solid.shape[1]))
    heavy = np.where(per_row >= floor)[0]
    base = int(heavy[-1]) if len(heavy) else bottom
    return {"left": left, "top": top, "right": right, "bottom": bottom, "base_row": base}


def cut(src: Path, dst: Path) -> dict:
    im = Image.open(src).convert("RGB")
    rgb = np.asarray(im).astype(np.float32) / 255.0

    a = _alpha(rgb)
    rgb = _despill(rgb, a)
    box = _measure(a)
    if not box:
        return {"file": src.name, "error": "nothing left after keying"}

    out = np.dstack([rgb, a[..., None]])
    out = (np.clip(out, 0, 1) * 255).astype(np.uint8)

    # Crop tight horizontally and to the top, but keep everything down to the
    # base row so the feet stay at the bottom edge of the file.
    l, t, r, b = box["left"], box["top"], box["right"] + 1, box["base_row"] + 1
    pad = 2
    l, t = max(0, l - pad), max(0, t - pad)
    r = min(out.shape[1], r + pad)
    b = min(out.shape[0], b + pad)
    Image.fromarray(out[t:b, l:r]).save(dst, optimize=True)

    return {
        "file": dst.name,
        "w": int(r - l),
        "h": int(b - t),
        "kept": round(float((a > 0.5).mean()), 4),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="substring filter on the filename")
    args = ap.parse_args()

    CUT.mkdir(parents=True, exist_ok=True)
    report = []
    for src in sorted(RAW.glob("*.png")):
        if args.only and args.only.lower() not in src.name.lower():
            continue
        info = cut(src, CUT / src.name)
        report.append(info)
        if "error" in info:
            print(f"  !! {info['file']}: {info['error']}")
        else:
            print(f"  {info['file']:<52} {info['w']:>5}x{info['h']:<5} kept {info['kept']:.1%}")

    (CUT / "_cut-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n{len(report)} files -> {CUT}/")


if __name__ == "__main__":
    main()
