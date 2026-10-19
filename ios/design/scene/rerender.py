"""Repaint a motion draft so it looks real, keeping its motion, with his picture pinned.

  python3 rerender.py wan   <draft.mp4> <picture.jpg> <out.mp4>   # wan-video/wan-2.7-videoedit, $0.10 a second
  python3 rerender.py aleph <draft.mp4> <picture.jpg> <out.mp4>   # runwayml/aleph-2, $0.336 a second
  add --inline to put the files inside the request instead of uploading them first

The draft comes from scene.html (the logic: one wind, gusts, every plume on its stem);
the AI only makes it look real. Aleph gets the picture as the first and the last frame,
Wan as its reference image.
"""
import base64, pathlib, sys

from replicate_run import fetch, predict, upload

PROMPT = ("Re-render this video as real photographic footage that looks exactly like the reference image: "
          "the same lone tree with orange autumn leaves on the left, the same hill of white silver grass "
          "(Japanese susuki), the same clear blue sky and warm afternoon light. Keep the camera completely still "
          "and keep the motion of the video: a gust of wind from the left makes the silver grass plumes sway and "
          "bend from their stems, and the tree's crown sway gently while its leaves tremble. The grass and the "
          "leaves move naturally, like real plants in wind. Do not add anything new.")


def inline(path: pathlib.Path) -> str:
    """The file inside the request itself (a data URL), for models that can't read uploaded-file links."""
    mime = "video/mp4" if path.suffix == ".mp4" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def main():
    kind, draft, picture, out = sys.argv[1], *map(pathlib.Path, sys.argv[2:5])
    send = inline if "--inline" in sys.argv else upload
    video, image = send(draft), send(picture)
    if kind == "wan":
        p = predict("wan-video/wan-2.7-videoedit", {"video": video, "prompt": PROMPT, "reference_image": image,
                                                    "resolution": "1080p", "aspect_ratio": "auto"})
    elif kind == "aleph":
        p = predict("runwayml/aleph-2", {"video": video, "prompt": PROMPT, "keyframe_images": [image, image],
                                         "keyframe_positions": ["first", "last"]})
    else:
        raise SystemExit(f"unknown model: {kind}")
    result = p["output"][0] if isinstance(p["output"], list) else p["output"]
    out.write_bytes(fetch(result))
    print(f"saved {out}")


if __name__ == "__main__":
    main()
