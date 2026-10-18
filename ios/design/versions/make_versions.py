"""The world in two versions — Cinematic and Painted — at four times of day,
made with Nano Banana Pro. Same place in all eight, so only the style and the
hour differ. He is not in the pictures: the app draws his light on top.

The key: GEMINI_API_KEY or backend/.env, never printed.
Usage:  python3 make_versions.py <out-dir> [name ...]   (≈ $0.134 a picture)
"""
import base64, json, os, pathlib, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

MODEL, PRICE = "gemini-3-pro-image", 0.134
OUT = pathlib.Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
KEY = os.environ.get("GEMINI_API_KEY") or next(
    l.split("=", 1)[1].strip().strip("\"'")
    for l in (pathlib.Path(__file__).resolve().parents[3] / "backend/.env").read_text().splitlines()
    if l.startswith("GEMINI_API_KEY="))

STYLE = {
    "cinematic": "A still from the main menu of a big open-world video game: photorealistic with painterly colour "
                 "grading, volumetric light, atmospheric haze, shallow depth of field, subtle 35mm film grain, rich "
                 "but muted colours. Quiet, grown-up and beautiful.",
    "painted": "Hand-painted background art from a classic Japanese animated feature film: gouache and watercolour on "
               "paper, visible brush texture, lush greens, towering soft cumulus clouds, warm nostalgic light, "
               "detailed but painterly.",
}
PLACE = ("A wide hillside meadow above a valley: tall grass and wildflowers, one old tree on the right third, hills "
         "and far mountains, a big sky. Far away on a distant hill, a small wooden house with one window.")
TIME = {
    "morning": "At dawn: first soft light, low mist lying in the valley, dew on the grass, a pale peach and blue sky.",
    "day": "On a soft bright day: high thin clouds, the grass and flowers bending in the wind, a few petals drifting "
           "in the air.",
    "evening": "At golden hour: warm low sunlight shining through the tall grass from behind, long shadows, a few "
               "autumn leaves drifting in the wind, a glowing sky.",
    "night": "At night under a bright moon: stars, small fireflies over the grass, cool blue moonlight, and the far "
             "house's single window glowing warm.",
}
FRAME = ("Portrait phone screen. The upper 40% is mostly calm sky, left empty for a title. A clear open patch of "
         "meadow just below the centre is left empty. The bottom fifth is darker foreground grass. No people, no "
         "animals in the foreground, no text, no letters, no logos, no watermark, no border.")
PROMPTS = {f"{s}-{t}": f"{STYLE[s]} {PLACE} {TIME[t]} {FRAME}" for s in STYLE for t in TIME}


def make(name: str) -> str:
    body = json.dumps({"contents": [{"parts": [{"text": PROMPTS[name]}]}],
                       "generationConfig": {"responseModalities": ["IMAGE"],
                                            "imageConfig": {"aspectRatio": "9:16", "imageSize": "2K"}}}).encode()
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
                time.sleep(4 * 2 ** attempt); continue
            return f"{name}: HTTP {e.code} {msg}"
        except Exception as e:
            if attempt < 3:
                time.sleep(4 * 2 ** attempt); continue
            return f"{name}: {type(e).__name__} {e}"


only = sys.argv[2:] or list(PROMPTS)
with ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(make, only))
print("\n".join(results))
made = sum(r.endswith(": ok") for r in results)
print(f"made {made} of {len(only)} · about ${made * PRICE:.2f}")
