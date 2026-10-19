"""Run a Replicate model on one picture and save what comes back.

  python3 replicate_run.py layers <picture> <out-dir> [num_layers]     # qwen/qwen-image-layered
  python3 replicate_run.py cut    <picture> <out-dir> "<what to cut>" [threshold]  # mattsays/sam3-image
  python3 replicate_run.py all    <picture> <out-dir>                  # meta/sam-2, every piece it sees

The key comes from REPLICATE_API_TOKEN (or the misspelt REPLICATER_API_TOKEN) in
backend/.env, and is never printed. Prices (2026-10-19): layers $0.07 a run +
$0.01 a layer (quality mode); cut ≈ $0.001 a run; all ≈ $0.02 a run.
"""
import io, json, mimetypes, os, pathlib, sys, time, urllib.error, urllib.request, uuid, zipfile

ENV = pathlib.Path.home() / "ai-companion/.claude/worktrees/ai-model-selection-voice-f93485/backend/.env"
TOKEN = os.environ.get("REPLICATE_API_TOKEN") or next(
    l.split("=", 1)[1].strip().strip("\"'") for l in ENV.read_text().splitlines()
    if l.split("=", 1)[0].strip() in ("REPLICATE_API_TOKEN", "REPLICATER_API_TOKEN"))
API = "https://api.replicate.com/v1"
UA = "bob-design/1.0"   # without a User-Agent Replicate's edge answers 403


def call(method, path, body=None, headers=None):
    h = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, **(headers or {})}
    req = urllib.request.Request(path if path.startswith("http") else API + path, data=body, method=method, headers=h)
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            # a small balance gets a tight rate limit: wait and try again
            if e.code != 429 or attempt == 5:
                raise
            time.sleep(int(e.headers.get("Retry-After") or 10))


def upload(picture: pathlib.Path) -> str:
    """Put the picture on Replicate's file store; returns a URL the model can read."""
    boundary = uuid.uuid4().hex
    mime = mimetypes.guess_type(picture.name)[0] or "application/octet-stream"
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"content\"; filename=\"{picture.name}\"\r\n"
            f"Content-Type: {mime}\r\n\r\n").encode() + picture.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    f = call("POST", "/files", body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    return f["urls"]["get"]


def predict(model: str, inputs: dict) -> dict:
    # official models take /models/<name>/predictions; community ones need their version id
    m = call("GET", f"/models/{model}")
    head = {"Content-Type": "application/json", "Prefer": "wait=60"}
    if m.get("is_official"):
        p = call("POST", f"/models/{model}/predictions", json.dumps({"input": inputs}).encode(), head)
    else:
        p = call("POST", "/predictions", json.dumps({"version": m["latest_version"]["id"], "input": inputs}).encode(), head)
    while p.get("status") not in ("succeeded", "failed", "canceled"):
        time.sleep(2)
        p = call("GET", p["urls"]["get"])
    if p["status"] != "succeeded":
        raise SystemExit(f"{model}: {p['status']} — {str(p.get('error'))[:300]}")
    print(f"{model}: done in {p.get('metrics', {}).get('predict_time', '?')} s")
    return p


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def main():
    kind, picture, out = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    url = upload(picture)
    if kind == "layers":
        n = int(sys.argv[4]) if len(sys.argv) > 4 else 4
        p = predict("qwen/qwen-image-layered", {"image": url, "num_layers": n, "description": "auto",
                                                 "go_fast": False, "output_format": "png"})
        outs = p["output"] if isinstance(p["output"], list) else [p["output"]]
        for i, u in enumerate(outs):
            (out / f"layer-{i}.png").write_bytes(fetch(u))
        print(f"saved {len(outs)} layers · about ${0.07 + 0.01 * len(outs):.2f}")
    elif kind == "cut":
        what = sys.argv[4]
        threshold = float(sys.argv[5]) if len(sys.argv) > 5 else 0.4
        p = predict("mattsays/sam3-image", {"image": url, "prompt": what, "mask_only": True, "return_zip": True,
                                            "threshold": threshold})
        data = fetch(p["output"])
        slug = "-".join(what.split())[:40]
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".png")]
            for n in names:
                (out / f"{slug}-{pathlib.Path(n).name}").write_bytes(z.read(n))
        print(f"saved {len(names)} masks for '{what}' · about $0.001")
    elif kind == "all":
        p = predict("meta/sam-2", {"image": url, "points_per_side": 32, "pred_iou_thresh": 0.8,
                                   "stability_score_thresh": 0.9, "use_m2m": True})
        masks = p["output"]["individual_masks"]
        for i, u in enumerate(masks):
            (out / f"piece-{i:03d}.png").write_bytes(fetch(u))
        print(f"saved {len(masks)} pieces · about $0.02")


if __name__ == "__main__":
    main()
