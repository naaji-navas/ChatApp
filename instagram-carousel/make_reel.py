"""Render two Instagram reels (1080x1920, 9:16, silent) into output/:

  reel-photos.mp4    every photo full-bleed at full height, with the captions and doodles
  reel-carousel.mp4  the framed 4:5 carousel slides, centred on the cream background

Each slide is shown for REEL_SLIDE seconds with a short crossfade between slides.

Usage: python3 make_reel.py [photos|carousel] [--stills]
       (--stills writes output/reel-<mode>-NN.jpg previews instead of the video)
"""

import os
import subprocess
import sys

from PIL import Image

from make_carousel import FPS, FRAME_COLOR, H, OUT, REEL_H, REEL_SLIDE, REEL_SPEED, REEL_W, SLIDES, Slide

XFADE = 0.3                # crossfade between slides, seconds


def framer(mode):
    """Return (slides, fn turning a slide frame into a 1080x1920 frame) for a reel mode."""
    if mode == "photos":
        return [Slide(i, reel=True) for i in range(len(SLIDES))], lambda f: f
    slides = [Slide(i, speed=REEL_SPEED, dur=REEL_SLIDE) for i in range(len(SLIDES))]
    top = (REEL_H - H) // 2

    def place(f):
        canvas = Image.new("RGB", (REEL_W, REEL_H), FRAME_COLOR)
        canvas.paste(f, (0, top))
        return canvas
    return slides, place


def render(mode, stills):
    slides, place = framer(mode)
    if stills:
        for s in slides:
            place(s.frame(REEL_SLIDE)).save(os.path.join(OUT, f"reel-{mode}-{s.idx:02d}.jpg"), quality=92)
        return

    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{REEL_W}x{REEL_H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", os.path.join(OUT, f"reel-{mode}.mp4")],
        stdin=subprocess.PIPE)
    per = int(REEL_SLIDE * FPS)
    xf = int(XFADE * FPS)
    for k, s in enumerate(slides):
        nxt = slides[k + 1] if k + 1 < len(slides) else None
        # the first xf frames of each slide (after the first) were already blended into the previous one
        first = xf if k > 0 else 0
        for f in range(first, per):
            frame = place(s.frame(f / FPS))
            if nxt and f >= per - xf:
                g = f - (per - xf)
                frame = Image.blend(frame, place(nxt.frame(g / FPS)), (g + 1) / (xf + 1))
            ff.stdin.write(frame.tobytes())
    ff.stdin.close()
    ff.wait()
    print("rendered", f"reel-{mode}.mp4")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    args = sys.argv[1:]
    modes = [m for m in ("photos", "carousel") if m in args] or ["photos", "carousel"]
    for m in modes:
        render(m, "--stills" in args)
