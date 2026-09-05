#!/usr/bin/env python3
"""A thin client for the three Recraft endpoints this project needs.

Recraft is the production-side generator: it has a real REST API, so nothing
here drives a browser or clicks anything. Three endpoints carry the whole art
pipeline.

  generate            make n variants of one asset from one prompt
  remove_background   hand back a transparent PNG

    Between them these delete the magenta hack. `assets/raw/README.md` asks for
    a flat magenta ground because Midjourney has no alpha channel and the
    colour has to be keyed out afterwards; cut_assets.py then spends most of
    its length neutralising the magenta that bled into every anti-aliased edge.
    A generator that returns real alpha has neither problem. cut_assets.py
    stays exactly as it is for the plates already made that way.

  create_style        turn up to 5 approved plates into a reusable style_id

    This is the anchor from HOW-THE-ART-IS-MADE.md, held in weights instead of
    in a reference image attached to every prompt. That document budgeted ~15
    approved images and a 20-minute training run for it; this needs five and
    returns immediately.

Costs, at the time of writing: a V4.1 raster image is about 35 API units and
1000 units is a dollar, so four variants is roughly fifteen cents. Verify
against Recraft's own pricing before running a large batch.

The API token is read from RECRAFT_API_TOKEN, or from backend/.env, which is
already gitignored and already holds the project's other keys.
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx

BASE = "https://external.api.recraft.ai/v1"
TIMEOUT = httpx.Timeout(180.0, connect=30.0)

# V4.1 raster. Style/substyle values and model names move as Recraft ships new
# families, so these are the two knobs most likely to need updating.
DEFAULT_MODEL = "recraftv4.1"
DEFAULT_STYLE = "digital_illustration"


class RecraftError(RuntimeError):
    pass


def _token() -> str:
    tok = os.environ.get("RECRAFT_API_TOKEN")
    if tok:
        return tok
    env = Path("backend/.env")
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            key, _, val = line.partition("=")
            if key.strip() == "RECRAFT_API_TOKEN":
                return val.strip().strip('"').strip("'")
    raise RecraftError(
        "No RECRAFT_API_TOKEN. Put it in backend/.env (already gitignored) as\n"
        "    RECRAFT_API_TOKEN=...\n"
        "or export it in your shell. Get one at recraft.ai under API.")


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token()}"}


def _check(r: httpx.Response) -> httpx.Response:
    if r.status_code >= 400:
        raise RecraftError(f"Recraft {r.status_code} on {r.request.url}: {r.text[:400]}")
    return r


def generate(prompt: str, n: int = 4, *, style_id: str | None = None,
             style: str | None = None, substyle: str | None = None,
             model: str = DEFAULT_MODEL, size: str = "1024x1024",
             negative_prompt: str | None = None) -> list[bytes]:
    """n variants of one prompt, returned as raw PNG bytes.

    style_id and style are mutually exclusive — a custom style already encodes
    which family it belongs to, so passing both is rejected by the API.
    """
    if style_id and style:
        raise RecraftError("Pass style_id or style, not both — the API rejects both.")
    body: dict[str, object] = {
        "prompt": prompt, "n": n, "model": model,
        "size": size, "response_format": "url",
    }
    if style_id:
        body["style_id"] = style_id
    else:
        body["style"] = style or DEFAULT_STYLE
        if substyle:
            body["substyle"] = substyle
    if negative_prompt:
        body["negative_prompt"] = negative_prompt

    with httpx.Client(timeout=TIMEOUT) as c:
        data = _check(c.post(f"{BASE}/images/generations",
                             headers=_headers(), json=body)).json()
        urls = [d["url"] for d in data.get("data", []) if d.get("url")]
        if not urls:
            raise RecraftError(f"No images came back: {str(data)[:300]}")
        return [_check(c.get(u)).content for u in urls]


def remove_background(png: bytes, filename: str = "plate.png") -> bytes:
    """Same image with a real alpha channel where the background was."""
    with httpx.Client(timeout=TIMEOUT) as c:
        r = _check(c.post(f"{BASE}/images/removeBackground", headers=_headers(),
                          files={"file": (filename, png, "image/png")}))
        ct = r.headers.get("content-type", "")
        if ct.startswith("image/"):
            return r.content
        url = (r.json().get("image") or {}).get("url")
        if not url:
            raise RecraftError(f"No cut-out came back: {r.text[:300]}")
        return _check(c.get(url)).content


def create_style(images: list[Path], *, base_style: str = DEFAULT_STYLE) -> str:
    """Turn up to 5 approved plates into a style_id. Returns the id."""
    if not 1 <= len(images) <= 5:
        raise RecraftError(f"Recraft takes 1-5 reference images, got {len(images)}.")
    files = [("file", (p.name, p.read_bytes(), "image/png")) for p in images]
    with httpx.Client(timeout=TIMEOUT) as c:
        data = _check(c.post(f"{BASE}/styles", headers=_headers(),
                             data={"style": base_style}, files=files)).json()
        sid = data.get("id") or data.get("style_id")
        if not sid:
            raise RecraftError(f"No style id came back: {str(data)[:300]}")
        return str(sid)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Create a Recraft style from approved plates.")
    ap.add_argument("images", nargs="+", type=Path, help="1-5 approved PNGs")
    args = ap.parse_args()
    sid = create_style(args.images)
    print(f"style_id: {sid}\n\nSave it in assets/style.json as:\n"
          f'  {{"style_id": "{sid}"}}')
