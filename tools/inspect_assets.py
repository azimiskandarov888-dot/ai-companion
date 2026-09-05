#!/usr/bin/env python3
"""Check every cut plate for the faults a person cannot see one file at a time.

Two of the three checks here exist because the eye is bad at them:

  * **Grain drift.** tree-leafy-6 and tree-broad-6 are both six-metre trees and
    their leaf clumps differ by nearly 3x. Standing side by side in the world
    they are visibly different material, but opened one at a time in a viewer
    they both just look like trees. Only the number catches it.
  * **A background that never came off.** Corner alpha is either zero or it
    isn't. Judging this by eye is unreliable — a transparent PNG renders
    against whatever the viewer feels like, and the answer changes with the
    viewer.

The third, the base row, is here because the engine stands things on it and a
wrong one is invisible until the object floats.

    python3 tools/inspect_assets.py
    python3 tools/inspect_assets.py --only tree
    python3 tools/inspect_assets.py --kind tree --band 3.5 5.5   # percent of height
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from grain import GRAIN_BANDS_PCT, measure, verdict

CUT = Path("assets/cut")
MANIFEST = Path("assets/manifest.json")

MARK = {"in-zone": "ok", "too-fine": "FINE", "too-coarse": "COARSE",
        "unbanded": "?", "unmeasured": "-"}


def corner_alpha(a: np.ndarray) -> float:
    """Mean alpha over four small corner patches. Should be 0 for a cut-out."""
    h, w = a.shape
    k = max(4, min(h, w) // 40)
    return float(np.mean([p.mean() for p in
                          (a[:k, :k], a[:k, -k:], a[-k:, :k], a[-k:, -k:])]))


def base_row(a: np.ndarray) -> int | None:
    """Lowest row carrying a real amount of object — the feet, not the bbox.

    Same rule as cut_assets.py, so the two tools never disagree about where a
    thing stands.
    """
    solid = a > 0.5
    floor = max(1, int(0.004 * solid.shape[1]))
    heavy = np.where(solid.sum(1) >= floor)[0]
    return int(heavy[-1]) if len(heavy) else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="substring filter on the filename")
    ap.add_argument("--kind", default="tree", help="which kind --band applies to")
    ap.add_argument("--band", nargs=2, type=float, metavar=("LO", "HI"),
                    help="grain band for --kind, as %% of object height")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    bands = dict(GRAIN_BANDS_PCT)
    if args.band:
        bands[args.kind] = (args.band[0], args.band[1])

    man = {m["file"]: m for m in json.loads(MANIFEST.read_text(encoding="utf-8"))}

    rows, problems = [], []
    for p in sorted(CUT.glob("*.png")):
        if args.only and args.only.lower() not in p.name.lower():
            continue
        rgba = np.asarray(Image.open(p).convert("RGBA")).astype(np.float32) / 255.0
        entry = man.get(p.name, {})
        m = measure(rgba, entry.get("height_m"))
        m["file"] = p.name
        m["corner_alpha"] = corner_alpha(rgba[..., 3])
        m["base_row"] = base_row(rgba[..., 3])
        m["height_m"] = entry.get("height_m")
        m["in_manifest"] = p.name in man
        m["kind"] = entry.get("kind")
        m["verdict"] = verdict(m["grain_pct"], m["kind"], bands)
        rows.append(m)

        if not m["in_manifest"]:
            problems.append(f"{p.name}: not in the manifest — the engine cannot place it")
        if m["corner_alpha"] > 0.5:
            problems.append(f"{p.name}: corners are opaque — the background never came off")
        if m["verdict"] in ("too-fine", "too-coarse"):
            lo, hi = bands[m["kind"]]
            problems.append(
                f"{p.name}: grain {m['grain_pct']:.1f}% of height is {m['verdict']} "
                f"for the {lo:.1f}-{hi:.1f}% {m['kind']} zone "
                f"({m['grain_cm']:.0f} cm on a {m['height_m']:.1f} m object)")

    if args.json:
        print(json.dumps(rows, indent=2))
        return

    print(f"{'file':<24}{'kind':>7}{'height':>8}{'cover':>7}"
          f"{'corners':>9}{'grain':>8}{'of height':>11}   zone")
    print("-" * 84)
    for m in sorted(rows, key=lambda r: (r["kind"] or "~",
                                         not np.isfinite(r["grain_pct"]), r["grain_pct"])):
        hm = f"{m['height_m']:.1f}m" if m["height_m"] else "-"
        gc = f"{m['grain_cm']:.0f} cm" if np.isfinite(m["grain_cm"]) else "-"
        gp = f"{m['grain_pct']:.1f}%" if np.isfinite(m["grain_pct"]) else "-"
        print(f"{m['file']:<24}{m['kind'] or '-':>7}{hm:>8}{m['coverage']:>7.0%}"
              f"{m['corner_alpha']:>9.2f}{gc:>8}{gp:>11}   {MARK[m['verdict']]}")

    for kind, (lo, hi) in sorted(bands.items()):
        vals = [m["grain_pct"] for m in rows
                if m["kind"] == kind and np.isfinite(m["grain_pct"])]
        if vals:
            print(f"\n{kind}: {min(vals):.1f}%-{max(vals):.1f}% of height "
                  f"across {len(vals)} plates (zone {lo:.1f}-{hi:.1f}%)")

    if problems:
        print(f"\n{len(problems)} problem(s):")
        for t in problems:
            print(f"  ! {t}")
    else:
        print("\nno problems found")


if __name__ == "__main__":
    main()
