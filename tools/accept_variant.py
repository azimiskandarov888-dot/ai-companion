#!/usr/bin/env python3
"""Take the variant you chose and put it in the world.

This is the step that used to be renaming a download by hand. It writes both
halves — the untouched original into assets/raw/ and the cut-out into
assets/cut/ — and then updates the manifest entry, keeping the fields that are
decisions rather than measurements.

That distinction is the whole reason this is a script. `w` and `h` are facts
about the file and get overwritten. `sway`, `solid_m` and `seat_m` are choices
somebody made about how the thing behaves in the world, and a regenerated plate
must not silently reset them.

    python3 tools/accept_variant.py tree-leafy-11 B
    python3 tools/accept_variant.py tree-leafy-11 B --build
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

RAW = Path("assets/raw")
CUT = Path("assets/cut")
VARIANTS = Path("assets/variants")
MANIFEST = Path("assets/manifest.json")

# Sensible starting points for a kind we have never placed before. Anything
# already in the manifest keeps its own values.
DEFAULT_SWAY = {"tree": 1.0, "bush": 1.6, "grass": 2.0, "frame": 0.5,
                "rock": 0.0, "seat": 0.0, "band": 0.0}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("asset", help="e.g. tree-leafy-11")
    ap.add_argument("letter", help="which variant, e.g. B")
    ap.add_argument("--build", action="store_true", help="rebuild the world page after")
    args = ap.parse_args()

    letter = args.letter.strip().upper()
    src_dir = VARIANTS / args.asset
    cut_src = src_dir / f"{letter}.png"
    raw_src = src_dir / f"{letter}-raw.png"
    if not cut_src.exists():
        sys.exit(f"no variant {letter} for {args.asset} — looked for {cut_src}")

    RAW.mkdir(parents=True, exist_ok=True)
    CUT.mkdir(parents=True, exist_ok=True)
    if raw_src.exists():
        shutil.copy2(raw_src, RAW / f"{args.asset}.png")
    shutil.copy2(cut_src, CUT / f"{args.asset}.png")

    with Image.open(cut_src) as im:
        w, h = im.size

    entries = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else []
    by_id = {e.get("id"): e for e in entries}
    existing = by_id.get(args.asset)

    meta = {}
    vjson = src_dir / "variants.json"
    if vjson.exists():
        for v in json.loads(vjson.read_text(encoding="utf-8")):
            if v.get("letter") == letter:
                meta = v
                break

    if existing:
        existing["file"] = f"{args.asset}.png"
        existing["w"], existing["h"] = w, h
        entry = existing
        note = "updated"
    else:
        kind = args.asset.split("-")[0]
        entry = {"id": args.asset, "file": f"{args.asset}.png", "kind": kind,
                 "w": w, "h": h, "sway": DEFAULT_SWAY.get(kind, 0.0)}
        entries.append(entry)
        note = "added"
    if meta.get("grain_pct") is not None:
        entry["grain_pct"] = round(meta["grain_pct"], 2)

    MANIFEST.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")

    print(f"{args.asset}: variant {letter} accepted")
    print(f"  assets/raw/{args.asset}.png   {'(original)' if raw_src.exists() else '(none)'}")
    print(f"  assets/cut/{args.asset}.png   {w}x{h}")
    print(f"  manifest entry {note}"
          + (f", grain {entry['grain_pct']}% of height" if "grain_pct" in entry else ""))
    if not existing:
        print("  ! new entry — set height_m and solid_m before it can be placed")

    if args.build:
        print()
        subprocess.run([sys.executable, "tools/build_world.py"], check=True)


if __name__ == "__main__":
    main()
