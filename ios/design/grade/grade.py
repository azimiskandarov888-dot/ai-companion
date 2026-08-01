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
from PIL import Image, ImageFilter

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

# --------------------------------------------------------------------------- #
# Which photo becomes which screen.
#
# You don't rename anything: drop the files in `in/` however they downloaded,
# and each is recognised by the photographer's name somewhere in the filename.
# Five photographs become eight screens — some are used twice, cropped or
# blurred differently, because Account and Settings are blurred past
# recognition anyway and screen 4 is meant to be the same place as screen 3.
#
#   crop_bias : 0 keeps the top of the frame, 1 keeps the bottom
#   blur      : pixels of blur (Account and Settings only)
#   darken    : 0–1, how far toward night
# --------------------------------------------------------------------------- #
SCREENS: list[dict] = [
    dict(out="1-signin",    photo="aleksio",
         exposure=+0.02, contrast=+0.02, crop_bias=0.42),
    dict(out="2-payment",   photo="hilalbulbul",
         exposure=-0.06, sky_sat=-0.06, crop_bias=0.46, darken=0.10),
    dict(out="3-story",     photo="zak",
         exposure=+0.02, contrast=+0.03, crop_bias=0.44),
    # Same photograph as 3, an hour later: lower crop, cooler, a touch dimmer.
    dict(out="4-meet",      photo="zak",
         exposure=-0.05, contrast=+0.01, sky_warm=-0.05, crop_bias=0.62, darken=0.08),
    # He lives here. Darkened well toward night, but never a black rectangle.
    dict(out="5-companion", photo="yunustung",
         exposure=-0.04, contrast=-0.02, crop_bias=0.40, darken=0.46),
    dict(out="6-diary",     photo="samuel",
         exposure=-0.02, crop_bias=0.48, darken=0.12),
    # Blurred and darkened in the app; these are the versions to design against.
    dict(out="7-account",   photo="aleksio",
         exposure=-0.04, crop_bias=0.42, blur=34, darken=0.34),
    dict(out="8-settings",  photo="yunustung",
         exposure=-0.06, crop_bias=0.40, blur=38, darken=0.52),
]


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


def crop_to_phone(img: Image.Image, bias: float = 0.44) -> Image.Image:
    """Crop to the phone ratio. `bias` decides what survives: 0 keeps the top of
    the frame, 1 keeps the bottom. Sky is usually the easiest thing to lose."""
    tw, th = TARGET_W, TARGET_H
    w, h = img.size
    target = tw / th
    if w / h > target:
        new_w = int(round(h * target))
        left = int((w - new_w) * 0.5)
        img = img.crop((left, 0, left + new_w, h))
    else:
        new_h = int(round(w / target))
        top = int((h - new_h) * bias)
        img = img.crop((0, top, w, top + new_h))
    return img.resize((tw, th), Image.LANCZOS)


def blur_and_darken(img: Image.Image, blur: float, darken: float) -> Image.Image:
    """Account and Settings sit on a blurred, darkened pass of the same place —
    you can still tell you're outdoors, but every word stays legible."""
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(radius=blur))
    if darken:
        a = np.asarray(img, np.float32) / 255.0
        a *= (1.0 - darken)
        a += np.array([0.008, 0.010, 0.006], np.float32) * darken   # keep it warm, not grey
        img = Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB")
    return img


# --------------------------------------------------------------------------- #
def grade_one(path: Path, screen: dict) -> tuple[Image.Image, dict, dict]:
    img = Image.open(path).convert("RGB")
    if max(img.size) > 4200:
        img.thumbnail((4200, 4200), Image.LANCZOS)
    rgb = np.asarray(img, dtype=np.float32) / 255.0
    before = measure(rgb)

    look = {**LOOK}
    for k, v in screen.items():
        if k in look:
            look[k] = look[k] + v

    # 1 · match every photo to the same destination
    rgb = match_to_target(rgb)
    rgb = match_saturation(rgb)
    rgb = set_black_point(rgb)
    rgb = np.clip(rgb * (2.0 ** screen.get("exposure", 0.0)), 0.0, 1.0)

    # 2 · the house look
    rgb = s_curve(rgb, look["contrast"])
    rgb = shift_greens(rgb, look["green_hue"], look["green_sat"])
    rgb = calm_sky(rgb, look["sky_sat"], look["sky_warm"])
    rgb = split_tone(rgb, look["shadow_tint"], look["highlight_tint"])
    rgb = vibrance_saturation(rgb, look["vibrance"], look["saturation"])
    rgb = add_grain(rgb, look["grain"])
    rgb = np.clip(rgb, 0.0, 1.0)

    out = Image.fromarray((rgb * 255.0 + 0.5).astype(np.uint8), "RGB")
    out = crop_to_phone(out, screen.get("crop_bias", 0.44))
    out = blur_and_darken(out, screen.get("blur", 0), screen.get("darken", 0.0))
    after = measure(np.asarray(out, np.float32) / 255.0)
    return out, before, after


def find_source(files: list[Path], photo: str) -> Path | None:
    """Match a photographer's name anywhere in the filename, so nothing has to
    be renamed — `pexels-aleksio-12345.jpg` is recognised as `aleksio`."""
    for f in files:
        if photo.lower() in f.name.lower():
            return f
    return None


def _table(title, rows, note=""):
    """rows: (name, measurements, is_natural). Spread is computed only over the
    screens meant to look alike — the deliberately darkened and blurred ones
    would otherwise make a working grade look broken."""
    print(f"\n{title}")
    if note:
        print(f"  {note}")
    print(f"{'screen':<14}{'warmth':>9}{'sat':>8}{'contrast':>10}{'mean':>8}{'black':>8}   ")
    for name, m, natural in rows:
        mark = "" if natural else "  · darkened on purpose"
        print(f"{name:<14}{m['warmth']:>9.3f}{m['sat']:>8.3f}"
              f"{m['contrast']:>10.3f}{m['mean']:>8.3f}{m['black']:>8.3f}{mark}")
    nat = [m for _, m, natural in rows if natural]
    if len(nat) > 1:
        keys = ("warmth", "sat", "contrast", "mean", "black")
        spread = {k: max(m[k] for m in nat) - min(m[k] for m in nat) for k in keys}
        print("  spread      " + "".join(
            f"{spread[k]:>9.3f}" if k == "warmth"
            else f"{spread[k]:>10.3f}" if k == "contrast"
            else f"{spread[k]:>8.3f}" for k in keys)
            + "   ← smaller = more one world")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default=str(IN_DIR))
    ap.add_argument("--out", dest="dst", default=str(OUT_DIR))
    ap.add_argument("--preview", action="store_true", help="write before/after strips")
    ap.add_argument("--report", action="store_true", help="print the measurements")
    args = ap.parse_args()

    src, dst = Path(args.src), Path(args.dst)
    src.mkdir(parents=True, exist_ok=True)   # make the folders on a fresh clone
    dst.mkdir(parents=True, exist_ok=True)

    files = [p for p in sorted(src.iterdir())
             if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
    if not files:
        print(f"No photos yet. Drop your five photos into:\n  {src}\n"
              f"then run this again. (Tip: `open {src}` opens it in Finder.)",
              file=sys.stderr)
        return 1

    b_rows, a_rows, missing = [], [], set()
    for screen in SCREENS:
        source = find_source(files, screen["photo"])
        if source is None:
            missing.add(screen["photo"])
            continue
        graded, before, after = grade_one(source, screen)
        out_path = dst / f"{screen['out']}.jpg"
        graded.save(out_path, quality=93, subsampling=1, optimize=True)
        natural = not screen.get("blur") and screen.get("darken", 0) <= 0.2
        b_rows.append((screen["out"], before, natural))
        a_rows.append((screen["out"], after, natural))
        extra = ""
        if screen.get("blur"):
            extra = "  (blurred + darkened)"
        elif screen.get("darken", 0) > 0.3:
            extra = "  (darkened toward night)"
        print(f"✓ {source.name}  →  {out_path.name}{extra}")

        if args.preview:
            orig = crop_to_phone(Image.open(source).convert("RGB"),
                                 screen.get("crop_bias", 0.44))
            strip = Image.new("RGB", (TARGET_W, TARGET_H))
            strip.paste(orig.crop((0, 0, TARGET_W // 2, TARGET_H)), (0, 0))
            strip.paste(graded.crop((TARGET_W // 2, 0, TARGET_W, TARGET_H)),
                        (TARGET_W // 2, 0))
            strip.thumbnail((700, 1520), Image.LANCZOS)
            strip.save(dst / f"{screen['out']}--before-after.jpg", quality=88)

    if missing:
        print("\n⚠  Couldn't find a photo for: " + ", ".join(sorted(missing)))
        print("   The filename needs the photographer's name in it somewhere.")
        print("   Found in " + str(src) + ": " + ", ".join(f.name for f in files))

    if args.report and a_rows:
        _table("BEFORE — five different worlds", b_rows)
        _table("AFTER — one world", a_rows,
               note="Companion, Account and Settings are dimmed by design; "
                    "they're excluded from the spread.")

    print(f"\nDone. {len(a_rows)} screen(s) written to {dst}/.")
    print("Open them all at once and look: they should read as one place on one day.")
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
