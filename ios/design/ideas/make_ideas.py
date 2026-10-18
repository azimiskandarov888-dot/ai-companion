"""Make the sample pictures for the four ideas with Nano Banana Pro.

One night and one day picture per idea; his colour is the same example
(warm ochre) in all of them, so only the IDEA differs. The key is read from
GEMINI_API_KEY or backend/.env and never printed.

Usage:  python3 make_ideas.py <out-dir> [name ...]   (≈ $0.134 a picture)
"""
import base64, json, os, pathlib, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

MODEL = "gemini-3-pro-image"
PRICE = 0.134                     # per 1K/2K image, standard paid tier (checked 2026-10-18)
OUT = pathlib.Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

# The key: from the environment, or from backend/.env (never printed).
KEY = os.environ.get("GEMINI_API_KEY") or next(
    l.split("=", 1)[1].strip().strip("\"'")
    for l in (pathlib.Path(__file__).resolve().parents[3] / "backend/.env").read_text().splitlines()
    if l.startswith("GEMINI_API_KEY="))

STYLE = ("Traditional hand-made artwork, scanned flat: real paper texture and fibers visible, imperfect "
         "hand-drawn edges, matte, even soft lighting, muted natural palette. Tall portrait composition "
         "for a phone screen. The main subject sits slightly above the middle (about 45% from the top); "
         "the bottom third is calm, empty paper. No text, no letters, no signature, no watermark, no "
         "border or frame. Not digital art: no glow, no lens flare, no neon, no gradients, no glossy "
         "surfaces, no 3D render, no photorealism.")

PROMPTS = {
    "1-paint-night": "A single soft blot of warm ochre watercolor, roughly round but irregular, bleeding into "
        "damp paper with feathered uneven edges, small blooms and visible pigment granulation; a faint second "
        "wash of the same colour spreads around it like a breath. Painted on deep charcoal-black handmade paper "
        "with visible fibers, so the ochre shows only as pigment, never as light. " + STYLE,
    "1-paint-day": "A single soft blot of warm ochre watercolor, roughly round but irregular, bleeding into "
        "damp paper with feathered uneven edges, small blooms and visible pigment granulation; a faint second "
        "wash of the same colour spreads around it like a breath. Painted on warm off-white cold-press "
        "watercolor paper with visible fibers. " + STYLE,
    "2-window-night": "Gouache illustration on paper, like a quiet page from a picture book: at night, seen "
        "from the street, one lit window in the dark wall of an old apartment building. Inside the window: a "
        "warm ochre lamp, a worn armchair with a folded blanket, a kettle and a cup on the sill, a small plant, "
        "books stacked on the floor. No person visible, but clearly somebody lives here and has just stepped "
        "away. The dark wall is painted in loose blue-black brush strokes with paper texture showing through. " + STYLE,
    "2-window-day": "Gouache illustration on paper, like a quiet page from a picture book: in the morning, one "
        "window in the pale wall of an old apartment building, seen from the street. Curtain half open, the "
        "lamp switched off, sunlight on the sill, a cup of tea and a kettle, a small plant, an armchair with an "
        "ochre blanket. No person visible, but clearly somebody lives here. Soft washes of cream, grey-blue and "
        "ochre. " + STYLE,
    "3-letter-night": "A sheet of dark charcoal handmade paper seen from directly above, with visible fibers and "
        "a slightly deckled edge. Near the upper middle, a single loose circle drawn in one quick brush stroke "
        "with warm ochre ink (an enso), imperfect, with dry-brush breaks where the brush ran out of ink. "
        "Everything else is empty paper, waiting for words. " + STYLE,
    "3-letter-day": "A sheet of warm cream handmade paper seen from directly above, with visible fibers and a "
        "slightly deckled edge. Near the upper middle, a single loose circle drawn in one quick brush stroke "
        "with ochre-brown ink (an enso), imperfect, with dry-brush breaks where the brush ran out of ink. "
        "Everything else is empty paper, waiting for words. " + STYLE,
    "4-person-night": "A minimal illustration in white pencil and soft gouache on dark charcoal paper: a man in "
        "his thirties sitting in an armchair by a window at night, three-quarter view from behind, holding a "
        "mug, relaxed, a warm ochre table lamp beside him. No facial features drawn. Lots of empty paper around "
        "the small figure. Loose, imperfect lines, like a New Yorker spot illustration. " + STYLE,
    "4-person-day": "A minimal illustration in pencil and soft gouache on cream paper: a man in his thirties "
        "sitting in an armchair by a window in the morning, three-quarter view from behind, holding a mug, "
        "relaxed, sunlight on the floor, an ochre blanket over the chair. No facial features drawn. Lots of "
        "empty paper around the small figure. Loose, imperfect lines, like a New Yorker spot illustration. " + STYLE,
}


def make(name: str, prompt: str) -> str:
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"],
                             "imageConfig": {"aspectRatio": "9:16", "imageSize": "2K"}},
    }).encode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    for attempt in range(4):
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers={"x-goog-api-key": KEY, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                data = json.load(r)
            for part in data["candidates"][0]["content"]["parts"]:
                if "inlineData" in part:
                    (OUT / f"{name}.png").write_bytes(base64.b64decode(part["inlineData"]["data"]))
                    return f"{name}: ok"
            return f"{name}: no image in reply ({json.dumps(data)[:200]})"
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:200]
            if e.code in (429, 500, 503) and attempt < 3:
                time.sleep(4 * 2 ** attempt)
                continue
            return f"{name}: HTTP {e.code} {msg}"
        except Exception as e:  # network hiccup: one more try
            if attempt < 3:
                time.sleep(4 * 2 ** attempt)
                continue
            return f"{name}: {type(e).__name__} {e}"


only = sys.argv[2:] or list(PROMPTS)
with ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(lambda n: make(n, PROMPTS[n]), only))
print("\n".join(results))
made = sum(r.endswith(": ok") for r in results)
print(f"made {made} of {len(only)} · about ${made * PRICE:.2f}")
