#!/usr/bin/env python3
"""How big the brush strokes are — the axis that area measurement is blind to.

Two canopies can carry exactly the same amount of green and still be made of
different material: one built from five broad masses, the other from a thousand
small marks. They composite to the same pixel count. They do not read as the
same world.

`HOW-THE-ART-IS-MADE.md` already names this axis without giving it a number:

    too minimal   flat shapes, one colour per form, no texture. Correct, dead
    too realistic individual leaves, photographic detail
    the target    painterly stylised - visible texture, simplified forms

That is a feature-size window, and a feature size is measurable. For N discs of
radius r, the area is N*pi*r^2 and the outline is N*2*pi*r, so

    2 * area / perimeter  ==  r

exactly, whatever N is. Quantity cancels; only the size of the typical feature
survives. Blobs that merge read as one larger feature, which is correct — two
touching leaf clumps *are* one bigger shape on screen.

Scaled by the asset's real height from the manifest, r stops being pixels and
becomes centimetres of actual foliage, which is the number worth arguing about.
"""

from __future__ import annotations

import numpy as np

# The zone, as a percentage of the object's own height.
#
# Absolute centimetres is the wrong invariant and the measurements say so: a
# 0.5 m grass tuft has 1 cm features and an 11 m tree has 52 cm features, and
# both are correct. Relative to height, six of the seven trees fall in a tight
# 3.2-4.8% band while tree-broad-6 sits at 9.5% — twice the top of the cluster,
# and the one plate whose canopy reads as a single continuous mass rather than
# as clumps. That is the outlier worth catching, and only the relative measure
# finds it.
#
# Bands are per kind because a bush is not a small tree. Kinds absent here are
# reported without a verdict: there are two bushes and one grass tuft in the
# set, which is not enough to draw a band around. Add one once there is.
GRAIN_BANDS_PCT: dict[str, tuple[float, float]] = {
    "tree": (3.0, 6.0),
}

# Foliage is green through blue-green. Trunks are blue, ground is warm.
FOLIAGE_HUE = (60.0, 170.0)
FOLIAGE_MIN_SAT = 0.18


def hsv(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Vectorised RGB->HS. Hue in degrees, saturation 0..1. Values in 0..1."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(-1), rgb.min(-1)
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
    return h, s


def perimeter(mask: np.ndarray) -> int:
    """Boundary length: foreground pixels with a background 4-neighbour.

    Pixels on the image border count as boundary too, so a shape running off
    the edge of the frame is not credited with a free straight side.
    """
    p = np.zeros_like(mask)
    p[:-1] |= mask[:-1] & ~mask[1:]
    p[1:] |= mask[1:] & ~mask[:-1]
    p[:, :-1] |= mask[:, :-1] & ~mask[:, 1:]
    p[:, 1:] |= mask[:, 1:] & ~mask[:, :-1]
    edge = np.zeros_like(mask)
    edge[0], edge[-1], edge[:, 0], edge[:, -1] = True, True, True, True
    return int((p | (mask & edge)).sum())


def feature_px(mask: np.ndarray) -> float:
    """Effective feature radius in pixels. NaN if the mask is empty."""
    a, p = int(mask.sum()), perimeter(mask)
    return (2.0 * a / p) if p else float("nan")


def foliage_mask(rgba: np.ndarray) -> np.ndarray:
    """The green part of an RGBA float image, where it is actually opaque."""
    h, s = hsv(rgba[..., :3])
    lo, hi = FOLIAGE_HUE
    return (rgba[..., 3] > 0.5) & (h > lo) & (h < hi) & (s > FOLIAGE_MIN_SAT)


def cm_per_px(rgba: np.ndarray, height_m: float) -> float:
    """Real centimetres per pixel, from the object's own opaque extent.

    The manifest's height_m describes the object, not the file, so the scale
    comes from how many rows the object actually occupies — not the canvas.
    """
    rows = np.where((rgba[..., 3] > 0.5).any(1))[0]
    if not len(rows):
        return float("nan")
    return height_m * 100.0 / (rows[-1] - rows[0] + 1)


def measure(rgba: np.ndarray, height_m: float | None) -> dict:
    """Everything worth knowing about a plate's material, in one pass."""
    solid = rgba[..., 3] > 0.5
    fol = foliage_mask(rgba)
    out = {
        "coverage": float(solid.mean()),
        "foliage_px": int(fol.sum()),
        "foliage_frac": float(fol.sum() / solid.sum()) if solid.any() else 0.0,
        "grain_px": feature_px(fol) if fol.sum() > 2000 else float("nan"),
        "grain_cm": float("nan"),
        "grain_pct": float("nan"),
    }
    if height_m and np.isfinite(out["grain_px"]):
        out["grain_cm"] = out["grain_px"] * cm_per_px(rgba, height_m)
        out["grain_pct"] = out["grain_cm"] / (height_m * 100.0) * 100.0
    return out


def verdict(grain_pct: float, kind: str | None,
            bands: dict[str, tuple[float, float]] | None = None) -> str:
    """in-zone / too-fine / too-coarse / unbanded / unmeasured.

    `unbanded` means the kind has no agreed zone yet — reported, never failed.
    """
    bands = GRAIN_BANDS_PCT if bands is None else bands
    if not np.isfinite(grain_pct):
        return "unmeasured"
    band = bands.get(kind or "")
    if band is None:
        return "unbanded"
    lo, hi = band
    if grain_pct < lo:
        return "too-fine"
    if grain_pct > hi:
        return "too-coarse"
    return "in-zone"
