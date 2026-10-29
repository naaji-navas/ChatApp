# a random day at the office — Instagram carousel

13 slides, 1080×1350 (4:5). Post either the animated `output/NN-*.mp4` files or the
static `output/NN-*.jpg` files, in number order.

Regenerate with `python3 make_carousel.py` (needs Pillow, numpy and ffmpeg; fonts are in `fonts/`, from Google Fonts (OFL)). Captions and
crops live in the `SLIDES` list at the top of the script. `output/preview.mp4` (all slides back
to back) is built too but not committed.

## Reel

`python3 make_reel.py` builds `output/reel.mp4`: the same 13 photos as one 1080×1920 (9:16) reel,
about 35 s long and silent (add music in Instagram). Each photo is shown full-height for 3 s with the
same captions and doodles, plus a short crossfade between photos. Crops and caption heights for the
reel are in the `REEL` table in `make_carousel.py`.
