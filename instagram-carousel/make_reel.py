"""Render the carousel as one Instagram reel: output/reel.mp4 (1080x1920, 9:16, silent).

Same captions and doodles as make_carousel.py, but each photo is shown full-bleed at full
height for REEL_SLIDE seconds with a short crossfade between photos.

Usage: python3 make_reel.py [--stills]   (--stills writes output/reel-NN.jpg previews only)
"""

import os
import subprocess
import sys

from PIL import Image

from make_carousel import FPS, OUT, REEL_H, REEL_SLIDE, REEL_W, SLIDES, Slide

XFADE = 0.3                # crossfade between photos, seconds


def main():
    os.makedirs(OUT, exist_ok=True)
    slides = [Slide(i, reel=True) for i in range(len(SLIDES))]
    if "--stills" in sys.argv:
        for s in slides:
            s.frame(REEL_SLIDE).save(os.path.join(OUT, f"reel-{s.idx:02d}.jpg"), quality=92)
        return

    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{REEL_W}x{REEL_H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", os.path.join(OUT, "reel.mp4")],
        stdin=subprocess.PIPE)
    per = int(REEL_SLIDE * FPS)
    xf = int(XFADE * FPS)
    for k, s in enumerate(slides):
        nxt = slides[k + 1] if k + 1 < len(slides) else None
        # the first xf frames of each slide (after the first) were already blended into the previous one
        first = xf if k > 0 else 0
        for f in range(first, per):
            frame = s.frame(f / FPS)
            if nxt and f >= per - xf:
                g = f - (per - xf)
                frame = Image.blend(frame, nxt.frame(g / FPS), (g + 1) / (xf + 1))
            ff.stdin.write(frame.tobytes())
        print("reel slide", s.stem)
    ff.stdin.close()
    ff.wait()


if __name__ == "__main__":
    main()
