#!/usr/bin/env python3
"""Bake the cut sprites into a single self-contained world page.

An artifact is one HTML file with no server behind it, so the art has to travel
inside it. Everything is downscaled to the largest size it can ever appear at on
a phone and re-encoded as WebP, which carries alpha at roughly a fifth the size
of the PNGs — nineteen full-resolution plates would not fit, and would spend
their detail on pixels no one will see.

    python3 tools/build_world.py             # -> the scratchpad page
    python3 tools/build_world.py --out x.html
"""

from __future__ import annotations

import argparse
import base64
import io
import json
from pathlib import Path

from PIL import Image

CUT = Path("assets/cut")
MANIFEST = Path("assets/manifest.json")
TPL = Path(
    "/tmp/claude-0/-home-user-ai-companion/"
    "1e77023f-6584-560d-819b-b5ce172c6c2e/scratchpad/world.tpl.html"
)

# Bands stretch the full width of the screen and tile, so they keep more pixels
# than an object that is never drawn larger than a third of the frame.
MAX_OBJECT = 620
MAX_BAND = 1400
QUALITY = 86


def encode(path: Path, kind: str) -> tuple[str, int, int]:
    im = Image.open(path).convert("RGBA")
    cap = MAX_BAND if kind in ("band", "frame") else MAX_OBJECT
    if max(im.size) > cap:
        k = cap / max(im.size)
        im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))),
                       Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=QUALITY, method=6)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/webp;base64,{b64}", im.width, im.height


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(TPL.parent / "forest.html"))
    args = ap.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    art, total = {}, 0
    for rec in manifest:
        src = CUT / rec["file"]
        if not src.exists():
            print(f"  !! missing {rec['file']}")
            continue
        uri, w, h = encode(src, rec["kind"])
        total += len(uri)
        art[rec["id"]] = {
            "src": uri, "w": w, "h": h, "kind": rec["kind"],
            "height_m": rec.get("height_m"), "sway": rec.get("sway", 0),
        }
        print(f"  {rec['id']:<22} {w:>5}x{h:<5} {len(uri)/1024:7.0f} KB")

    html = TPL.read_text(encoding="utf-8").replace(
        "/*ART*/", json.dumps(art, separators=(",", ":")))
    out = Path(args.out)
    out.write_text(html, encoding="utf-8")
    print(f"\n{len(art)} sprites, art {total/1048576:.2f} MB, "
          f"page {out.stat().st_size/1048576:.2f} MB -> {out}")


if __name__ == "__main__":
    main()
