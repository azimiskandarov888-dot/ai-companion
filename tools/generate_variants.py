#!/usr/bin/env python3
"""Generate four variants of one asset, throw away the ones that miss, and
build a single picture you can judge from a phone.

The point of the contact sheet is that it survives the trip. A browser window
on the desktop only works if you are sitting at the desktop; an image dropped
into the conversation reaches the terminal, claude.ai/code and the phone app
identically. So the choosing step is a picture Claude *sends*, not a screen you
have to be in front of.

The rejection step is what makes four variants worth looking at instead of
twenty. Every candidate is cut, measured and compared against the grain band
for its kind before you ever see it, so a plate whose canopy came out as one
undifferentiated mass never reaches the sheet. That check is in grain.py, and
it is the same one inspect_assets.py runs over the finished set.

    python3 tools/generate_variants.py tree-leafy-11
    python3 tools/generate_variants.py tree-leafy-11 -n 6 --note "lighter crown"
    python3 tools/generate_variants.py tree-leafy-11 --keep-all

Then, once you have picked:

    python3 tools/accept_variant.py tree-leafy-11 B
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import recraft
from grain import GRAIN_BANDS_PCT, measure, verdict

RAW_README = Path("assets/raw/README.md")
MANIFEST = Path("assets/manifest.json")
STYLE = Path("assets/style.json")
VARIANTS = Path("assets/variants")

LETTERS = "ABCDEFGH"

# From HOW-THE-ART-IS-MADE.md. Parts are components nobody ever sees whole, so
# they are posed and boring on purpose; scenes are what a person looks at.
PART_PROMPT = (
    "{what}, side view, no perspective, centred, standing on the bottom edge "
    "of the frame, plain flat background, light from the upper right, "
    "no shadow, no ground, nothing else")
SCENE_PROMPT = (
    "{what}, wide view, eye level, natural off-centre composition, things "
    "running out of the frame at the edges, nothing posed, coloured light and "
    "haze, empty ground across the bottom of the image")
NEGATIVE = "cast shadow, ground plane, horizon line, text, watermark, border, frame"


def read_catalogue() -> dict[str, dict]:
    """Parse the asset tables in assets/raw/README.md.

    That file is already the source of truth for names — "The manifest is keyed
    off them, and a renamed file is a broken asset" — so the prompt is built
    from it rather than from a second list that could drift out of step.
    """
    if not RAW_README.exists():
        sys.exit(f"missing {RAW_README}")
    out: dict[str, dict] = {}
    section = ""
    for line in RAW_README.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            section = line.lstrip("#").strip().lower()
        cells = [c.strip() for c in line.strip().strip("|").split("|")] \
            if line.strip().startswith("|") else []
        if len(cells) < 2 or not cells[0].startswith("`"):
            continue
        name = cells[0].strip("`").removesuffix(".png")
        metres = None
        if len(cells) >= 3:
            try:
                metres = float(cells[2])
            except ValueError:
                metres = None
        out[name] = {"name": name, "what": cells[1], "height_m": metres,
                     "is_scene": "band" in section or "frame" in section}
    return out


def load_style() -> dict:
    """The anchor: a Recraft style_id if one has been made, else a plain style."""
    if STYLE.exists():
        return json.loads(STYLE.read_text(encoding="utf-8"))
    return {}


def manifest_kind(name: str) -> str | None:
    if not MANIFEST.exists():
        return None
    for m in json.loads(MANIFEST.read_text(encoding="utf-8")):
        if m.get("id") == name or m.get("file") == f"{name}.png":
            return m.get("kind")
    # tree-leafy-11 -> tree, bush-wide-10 -> bush
    head = re.split(r"[-_]", name)[0]
    return head or None


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/System/Library/Fonts/Helvetica.ttc",
              "C:/Windows/Fonts/arialbd.ttf"):
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                pass
    return ImageFont.load_default()


def contact_sheet(cards: list[dict], title: str, out: Path,
                  cell: int = 760, cols: int = 2) -> None:
    """One labelled picture of every surviving candidate.

    Checkerboard behind each plate, because a transparent PNG on a flat ground
    hides exactly the fault you most want to see — a background that never came
    off reads as a deliberate colour choice until you put a pattern behind it.
    """
    pad, head, foot = 26, 96, 74
    rows = (len(cards) + cols - 1) // cols
    W = pad + cols * (cell + pad)
    H = head + rows * (cell + foot + pad) + pad
    sheet = Image.new("RGB", (W, H), (246, 245, 240))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 30), title, font=_font(34), fill=(26, 25, 24))

    check = Image.new("RGB", (cell, cell), (255, 255, 255))
    cd = ImageDraw.Draw(check)
    for y in range(0, cell, 28):
        for x in range(0, cell, 28):
            if (x // 28 + y // 28) % 2:
                cd.rectangle([x, y, x + 27, y + 27], fill=(232, 231, 226))

    for i, c in enumerate(cards):
        cx = pad + (i % cols) * (cell + pad)
        cy = head + (i // cols) * (cell + foot + pad)
        tile = check.copy()
        im = Image.open(io.BytesIO(c["png"])).convert("RGBA")
        im.thumbnail((cell - 24, cell - 24), Image.LANCZOS)
        tile.paste(im, ((cell - im.width) // 2, (cell - im.height) // 2), im)
        sheet.paste(tile, (cx, cy))
        d.rectangle([cx, cy, cx + cell - 1, cy + cell - 1], outline=(206, 204, 198))

        ok = c["verdict"] in ("in-zone", "unbanded")
        d.text((cx + 4, cy + cell + 6), c["letter"], font=_font(46),
               fill=(26, 25, 24) if ok else (168, 74, 62))
        gp = f"{c['grain_pct']:.1f}%" if np.isfinite(c["grain_pct"]) else "-"
        gc = f"{c['grain_cm']:.0f} cm" if np.isfinite(c["grain_cm"]) else "-"
        # Kept short deliberately: the caption sits inside one cell's width, and
        # a long one runs under the next cell's letter. "of height" is in the title.
        d.text((cx + 50, cy + cell + 16),
               f"grain {gp} ({gc})   cover {c['coverage']:.0%}   {c['verdict']}",
               font=_font(22), fill=(60, 58, 55) if ok else (168, 74, 62))

    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, optimize=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("asset", help="an id from assets/raw/README.md, e.g. tree-leafy-11")
    ap.add_argument("-n", type=int, default=4, help="how many variants (default 4)")
    ap.add_argument("--note", default="", help="extra steering, e.g. 'lighter crown'")
    ap.add_argument("--keep-all", action="store_true",
                    help="show candidates that miss the grain band instead of dropping them")
    ap.add_argument("--dry-run", action="store_true", help="print the prompt and stop")
    args = ap.parse_args()

    cat = read_catalogue()
    if args.asset not in cat:
        sys.exit(f"unknown asset {args.asset!r}. Known: {', '.join(sorted(cat))}")
    spec = cat[args.asset]
    kind = manifest_kind(args.asset)

    what = spec["what"]
    if spec["height_m"]:
        what = f"{what}, {spec['height_m']:g} metres tall"
    if args.note:
        what = f"{what}, {args.note}"
    template = SCENE_PROMPT if spec["is_scene"] else PART_PROMPT
    prompt = template.format(what=what)

    style = load_style()
    print(f"{args.asset}  ({kind or 'unknown kind'}, {spec['height_m'] or '?'} m)")
    print(f"prompt: {prompt}")
    print(f"style : {style.get('style_id') or recraft.DEFAULT_STYLE}"
          f"{'' if style.get('style_id') else '  (no anchor yet — see tools/recraft.py)'}")
    if args.dry_run:
        return

    print(f"\ngenerating {args.n}...")
    raws = recraft.generate(prompt, n=args.n, style_id=style.get("style_id"),
                            style=None if style.get("style_id") else recraft.DEFAULT_STYLE,
                            substyle=style.get("substyle"),
                            negative_prompt=NEGATIVE)

    out_dir = VARIANTS / args.asset
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*"):
        old.unlink()

    cards, dropped = [], []
    for i, raw in enumerate(raws):
        letter = LETTERS[i]
        print(f"  {letter}: cutting...", end="", flush=True)
        cut = recraft.remove_background(raw, filename=f"{args.asset}-{letter}.png")
        rgba = np.asarray(Image.open(io.BytesIO(cut)).convert("RGBA")).astype(np.float32) / 255.0
        m = measure(rgba, spec["height_m"])
        v = verdict(m["grain_pct"], kind, GRAIN_BANDS_PCT)
        card = {"letter": letter, "png": cut, "verdict": v, **m}
        (out_dir / f"{letter}-raw.png").write_bytes(raw)
        (out_dir / f"{letter}.png").write_bytes(cut)
        gp = f"{m['grain_pct']:.1f}%" if np.isfinite(m["grain_pct"]) else "-"
        print(f" grain {gp:>6}  {v}")
        (cards if v in ("in-zone", "unbanded") or args.keep_all else dropped).append(card)

    if not cards:
        print("\nEvery candidate missed the band. Nothing worth showing — "
              "re-run with --keep-all to look anyway, or adjust --note.")
    band = GRAIN_BANDS_PCT.get(kind or "")
    title = f"{args.asset} — {len(cards)} of {args.n}"
    if band:
        title += f"   zone {band[0]:.1f}-{band[1]:.1f}% of height"
    sheet = out_dir / "contact-sheet.png"
    contact_sheet(cards or dropped, title, sheet)

    (out_dir / "variants.json").write_text(json.dumps(
        [{k: (None if isinstance(v, float) and not np.isfinite(v) else v)
          for k, v in c.items() if k != "png"} for c in cards + dropped],
        indent=2), encoding="utf-8")

    if dropped and not args.keep_all:
        print(f"\ndropped {len(dropped)}: " +
              ", ".join(f"{c['letter']} ({c['verdict']})" for c in dropped))
    print(f"\ncontact sheet: {sheet}")
    print(f"accept with:   python3 tools/accept_variant.py {args.asset} <letter>")


if __name__ == "__main__":
    main()
