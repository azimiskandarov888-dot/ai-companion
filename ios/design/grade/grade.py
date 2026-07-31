#!/usr/bin/env python3
"""Grade the app's photographs into one world.

Six beautiful photos, taken by six different people in six different lights, do
not belong to the same app — until they are graded together.

This does it in two stages:

  1. MATCH — each photo is measured and pulled toward the same destination:
     the same warmth, the same brightness, the same contrast, the same black
     point. This part is automatic and different for every photo, because every
     photo starts somewhere different. Drop in any new photo and it will join
     the family.

  2. LOOK — the same house character is then applied to all of them:
     greens toward olive, skies calmed and warmed, warm light and warm shade,
     a filmic curve, a whisper of grain.

Stage 1 makes them match. Stage 2 gives them character. Neither works alone.

THE DESTINATION — "the golden medium":
  · warm and sunlit, but never orange
  · real black in every frame — this is what reads as expensive rather than flat
  · medium-high contrast; NOT the muted, washed-out "cinematic" look
  · greens pulled toward olive and gold, away from emerald and lime
  · skies desaturated and warmed — no postcard blue
  · warm highlights, warm-green shadows; nothing in this app is cold

Usage:
    python3 grade.py                # grade ./in → ./out
    python3 grade.py --preview      # also write before/after strips
    python3 grade.py --report       # print the measurements, before and after
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
IN_DIR, OUT_DIR = HERE / "in", HERE / "out"

TARGET_W, TARGET_H = 1290, 2796          # iPhone Pro Max @3x

# --------------------------------------------------------------------------- #
# STAGE 1 — the shared destination
# --------------------------------------------------------------------------- #
TARGET_LUMA_MEAN = 0.400   # rich, not washed out
TARGET_LUMA_STD  = 0.195   # medium-high contrast — the "not too toned" part
TARGET_BALANCE   = (1.055, 1.000, 0.885)   # R : G : B — the warmth of the world
TARGET_SAT       = 0.330   # rich, but never garish
BLACK_POINT      = 0.014   # where the darkest 0.5 % should land
MATCH_STRENGTH   = 0.85    # 1.0 = identical siblings, 0 = leave alone

# --------------------------------------------------------------------------- #
# STAGE 2 — the house look, applied to everything
# --------------------------------------------------------------------------- #
LOOK = dict(
    contrast=0.24,          # filmic S on top of the matched contrast
    green_hue=-0.05,        # green → olive/gold
    green_sat=-0.10,        # take the lime out
    sky_sat=-0.40,          # no postcard blue
    sky_warm=0.17,
    shadow_tint=(0.030, 0.034, -0.026),    # warm-green shade
    highlight_tint=(0.052, 0.034, -0.030), # warm light
    vibrance=0.07,          # lift the dull colours only
    saturation=-0.05,       # ease the loud ones
    grain=0.009,
)

# Per-photo taste, on top of everything above. Small numbers only — the matching
# has already done the heavy lifting. Keys are the filename stems.
TASTE: dict[str, dict] = {
    "1-signin":    dict(exposure=+0.02, contrast=+0.02),  # the hero, a touch brighter
    "2-payment":   dict(exposure=-0.05, sky_sat=-0.06),   # dusk-ward, calmer sky
    "3-scroll":    dict(exposure=+0.02, contrast=+0.03),  # writing needs clarity
    "4-scroll2":   dict(exposure=-0.02),
    "6-companion": dict(exposure=-0.03, contrast=-0.02),  # he lives here — softer
    "7-diary":     dict(exposure=-0.02),
    "8-account":   dict(exposure=-0.04),                  # gets blurred anyway
    "9-settings":  dict(exposure=-0.08),                  # darkest of the set
}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def luma(rgb: np.ndarray) -> np.ndarray:
    return rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def measure(rgb: np.ndarray) -> dict:
    l = luma(rgb)
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    return dict(
        warmth=float((rgb[..., 0] - rgb[..., 2]).mean()),
        sat=float(sat.mean()),
        contrast=float(l.std()),
        mean=float(l.mean()),
        black=float(np.percentile(l, 0.5)),
    )


# --------------------------------------------------------------------------- #
# STAGE 1 — match this photo to the destination
# --------------------------------------------------------------------------- #
def match_to_target(rgb: np.ndarray, strength: float = MATCH_STRENGTH) -> np.ndarray:
    """Per-channel mean/spread matching — the move that makes photos siblings.

    Each channel is re-centred and re-scaled toward the target. Gains are
    clamped so a flat, hazy photo can't be stretched into something brittle.
    """
    out = rgb.copy()
    targets = [TARGET_LUMA_MEAN * b for b in TARGET_BALANCE]
    for c in range(3):
        ch = rgb[..., c]
        mean, std = float(ch.mean()), float(ch.std())
        if std < 1e-5:
            continue
        gain = np.clip((TARGET_LUMA_STD / std), 0.70, 1.75)
        matched = (ch - mean) * gain + targets[c]
        out[..., c] = ch * (1.0 - strength) + matched * strength
    return out


def match_saturation(rgb: np.ndarray, strength: float = 0.7) -> np.ndarray:
    """Bring every photo to the same colour intensity.

    Without this, a vivid alpine shot and a muted meadow still read as two
    different cameras even when their brightness and warmth agree.
    """
    _, sat = _hue_sat(np.clip(rgb, 0, 1))
    current = float(sat.mean())
    if current < 1e-4:
        return rgb
    factor = np.clip(TARGET_SAT / current, 0.55, 1.6)
    factor = 1.0 + (factor - 1.0) * strength
    grey = luma(rgb)[..., None]
    return grey + (rgb - grey) * factor


def set_black_point(rgb: np.ndarray) -> np.ndarray:
    """Put real black back in. Flat blacks are what make a photo look cheap."""
    l = luma(rgb)
    current = float(np.percentile(l, 0.5))
    lift = current - BLACK_POINT
    if lift <= 0:
        return rgb
    return (rgb - lift) / max(1e-6, 1.0 - lift)


# --------------------------------------------------------------------------- #
# STAGE 2 — the house look
# --------------------------------------------------------------------------- #
def s_curve(rgb, amount):
    if amount <= 0:
        return rgb
    x = np.clip(rgb, 0.0, 1.0)
    return x * (1 - amount) + (x * x * (3.0 - 2.0 * x)) * amount


def _hue_sat(rgb):
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = mx - mn
    hue = np.zeros_like(mx)
    ok = d > 1e-6
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    i = ok & (mx == r); hue[i] = ((g[i] - b[i]) / d[i]) % 6
    i = ok & (mx == g); hue[i] = (b[i] - r[i]) / d[i] + 2
    i = ok & (mx == b); hue[i] = (r[i] - g[i]) / d[i] + 4
    return hue / 6.0, np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0.0)


def _band(hue, centre, width):
    d = np.abs(((hue - centre + 0.5) % 1.0) - 0.5)
    return np.clip(1.0 - d / width, 0.0, 1.0) ** 1.4


def shift_greens(rgb, hue_shift, sat_shift):
    hue, sat = _hue_sat(np.clip(rgb, 0, 1))
    mask = (_band(hue, 0.27, 0.18) * np.clip(sat * 2.0, 0, 1))[..., None]
    grey = luma(rgb)[..., None]
    out = rgb.copy()
    out[..., 0] -= hue_shift * 0.90        # toward yellow/olive
    out[..., 1] -= hue_shift * 0.20
    out[..., 2] += hue_shift * 0.28
    out = out + (grey - out) * max(0.0, -sat_shift)
    return rgb * (1 - mask) + out * mask


def calm_sky(rgb, sat_drop, warm):
    hue, sat = _hue_sat(np.clip(rgb, 0, 1))
    mask = (_band(hue, 0.57, 0.22) * np.clip(sat * 1.6, 0, 1))[..., None]
    grey = luma(rgb)[..., None]
    out = rgb + (grey - rgb) * min(0.95, -sat_drop if sat_drop < 0 else 0.0)
    out[..., 0] += warm * 0.085
    out[..., 1] += warm * 0.045
    out[..., 2] -= warm * 0.050
    return rgb * (1 - mask) + out * mask


def split_tone(rgb, shadow, highlight):
    l = luma(rgb)[..., None]
    sh = np.clip(1.0 - l * 2.0, 0, 1)
    hi = np.clip(l * 2.0 - 1.0, 0, 1)
    return rgb + sh * np.array(shadow, np.float32) + hi * np.array(highlight, np.float32)


def vibrance_saturation(rgb, vib, sat):
    grey = luma(rgb)[..., None]
    if vib:
        _, s = _hue_sat(np.clip(rgb, 0, 1))
        weight = (1.0 - np.clip(s, 0, 1))[..., None]
        rgb = rgb + (rgb - grey) * vib * weight * 1.5
    if sat:
        rgb = rgb + (rgb - grey) * sat
    return rgb


def add_grain(rgb, amount, seed=11):
    if amount <= 0:
        return rgb
    rng = np.random.default_rng(seed)
    n = rng.normal(0.0, amount, rgb.shape[:2]).astype(np.float32)
    w = np.clip(1.0 - np.abs(luma(rgb) - 0.5) * 1.6, 0, 1)[..., None]
    return rgb + n[..., None] * w


def crop_to_phone(img: Image.Image) -> Image.Image:
    """Centre-crop to the phone ratio, favouring the ground — the interface
    lives on the lower half, and sky is the easiest thing to lose."""
    tw, th = TARGET_W, TARGET_H
    w, h = img.size
    target = tw / th
    if w / h > target:
        new_w = int(round(h * target))
        img = img.crop(((w - new_w) // 2, 0, (w - new_w) // 2 + new_w, h))
    else:
        new_h = int(round(w / target))
        top = int((h - new_h) * 0.42)
        img = img.crop((0, top, w, top + new_h))
    return img.resize((tw, th), Image.LANCZOS)


# --------------------------------------------------------------------------- #
def grade_one(path: Path, taste: dict) -> tuple[Image.Image, dict, dict]:
    img = Image.open(path).convert("RGB")
    if max(img.size) > 4200:
        img.thumbnail((4200, 4200), Image.LANCZOS)
    rgb = np.asarray(img, dtype=np.float32) / 255.0
    before = measure(rgb)

    look = {**LOOK, **{k: LOOK.get(k, 0) + v for k, v in taste.items() if k in LOOK}}
    exposure = taste.get("exposure", 0.0)

    # 1 · match
    rgb = match_to_target(rgb)
    rgb = match_saturation(rgb)
    rgb = set_black_point(rgb)
    rgb = np.clip(rgb * (2.0 ** exposure), 0.0, 1.0)

    # 2 · look
    rgb = s_curve(rgb, look["contrast"])
    rgb = shift_greens(rgb, look["green_hue"], look["green_sat"])
    rgb = calm_sky(rgb, look["sky_sat"], look["sky_warm"])
    rgb = split_tone(rgb, look["shadow_tint"], look["highlight_tint"])
    rgb = vibrance_saturation(rgb, look["vibrance"], look["saturation"])
    rgb = add_grain(rgb, look["grain"])

    rgb = np.clip(rgb, 0.0, 1.0)
    after = measure(rgb)
    out = Image.fromarray((rgb * 255.0 + 0.5).astype(np.uint8), "RGB")
    return crop_to_phone(out), before, after


def _table(title, rows):
    print(f"\n{title}")
    print(f"{'photo':<14}{'warmth':>9}{'sat':>8}{'contrast':>10}{'mean':>8}{'black':>8}")
    for name, m in rows:
        print(f"{name:<14}{m['warmth']:>9.3f}{m['sat']:>8.3f}"
              f"{m['contrast']:>10.3f}{m['mean']:>8.3f}{m['black']:>8.3f}")
    if len(rows) > 1:
        spread = {k: max(m[k] for _, m in rows) - min(m[k] for _, m in rows)
                  for k in ("warmth", "sat", "contrast", "mean", "black")}
        print("  spread      " + "".join(f"{spread[k]:>9.3f}" if k == "warmth"
              else f"{spread[k]:>8.3f}" if k != "contrast" else f"{spread[k]:>10.3f}"
              for k in ("warmth", "sat", "contrast", "mean", "black")))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default=str(IN_DIR))
    ap.add_argument("--out", dest="dst", default=str(OUT_DIR))
    ap.add_argument("--preview", action="store_true", help="write before/after strips")
    ap.add_argument("--report", action="store_true", help="print the measurements")
    args = ap.parse_args()

    src, dst = Path(args.src), Path(args.dst)
    if not src.exists():
        print(f"Put the photos in {src}/ first — see README.md", file=sys.stderr)
        return 1
    dst.mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in src.iterdir()
                   if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
                   and "before-after" not in p.name)
    if not files:
        print(f"No images found in {src}/.", file=sys.stderr)
        return 1

    b_rows, a_rows = [], []
    for path in files:
        graded, before, after = grade_one(path, TASTE.get(path.stem.lower(), {}))
        out_path = dst / f"{path.stem}.jpg"
        graded.save(out_path, quality=93, subsampling=1, optimize=True)
        b_rows.append((path.stem, before))
        a_rows.append((path.stem, after))
        print(f"✓ {path.name} → out/{out_path.name}  ({TARGET_W}×{TARGET_H})")

        if args.preview:
            orig = crop_to_phone(Image.open(path).convert("RGB"))
            strip = Image.new("RGB", (TARGET_W, TARGET_H))
            strip.paste(orig.crop((0, 0, TARGET_W // 2, TARGET_H)), (0, 0))
            strip.paste(graded.crop((TARGET_W // 2, 0, TARGET_W, TARGET_H)), (TARGET_W // 2, 0))
            strip.thumbnail((700, 1520), Image.LANCZOS)
            strip.save(dst / f"{path.stem}--before-after.jpg", quality=88)

    if args.report:
        _table("BEFORE — five different worlds", b_rows)
        _table("AFTER — one world", a_rows)

    print(f"\nDone. {len(files)} photo(s) in {dst}/. Open them side by side: they "
          f"should look like one place on one day.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
