"""Move his exact still picture with the motion measured in a real-looking video.

  python3 still_motion.py <video.mp4> <picture.jpg> <out.mp4> [strength]   # strength 1 = as measured, 0.5 = half

For every frame, optical flow (OpenCV DIS) says where each pixel of that frame was in
the first frame; the still is then pulled from there. The picture itself is never
repainted — only moved. This is the base of "physics textures" (way 2 in
2D-WAYS-RESEARCH.md): the same measured motion can later be split into modes and
driven by wind and touch.
"""
import subprocess, sys, tempfile, pathlib

import cv2
import numpy as np


def frames(path):
    cap = cv2.VideoCapture(str(path))
    while True:
        ok, f = cap.read()
        if not ok:
            break
        yield f
    cap.release()


def main():
    video, picture, out = map(pathlib.Path, sys.argv[1:4])
    strength = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
    fps = cv2.VideoCapture(str(video)).get(cv2.CAP_PROP_FPS) or 24
    seq = list(frames(video))
    H, W = seq[0].shape[:2]
    still = cv2.resize(cv2.imread(str(picture)), (W, H), interpolation=cv2.INTER_AREA)
    # measure at half size: steadier on grass, then scale the flow back up
    small = lambda f: cv2.cvtColor(cv2.resize(f, (W // 2, H // 2), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    first = small(seq[0])
    flows = [cv2.resize(dis.calc(small(f), first, None), (W, H)) * 2 for f in seq]
    gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(len(seq)):
            # a little smoothing in time and space so measured noise doesn't make the grass boil
            f = np.mean(flows[max(0, i - 1):i + 2], axis=0)
            f = cv2.GaussianBlur(f, (0, 0), 1.5) * strength
            frame = cv2.remap(still, gx + f[..., 0], gy + f[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            cv2.imwrite(f"{tmp}/{i:03d}.png", frame)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(fps), "-i", f"{tmp}/%03d.png",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow",
                        "-movflags", "+faststart", str(out)], check=True)
    print(f"saved {out} · {len(seq)} frames")


if __name__ == "__main__":
    main()
