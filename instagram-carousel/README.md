# a random day at the office — Instagram carousel

13 slides, 1080×1350 (4:5). Post either the animated `output/NN-*.mp4` files or the
static `output/NN-*.jpg` files, in number order.

Regenerate with `python3 make_carousel.py` (needs Pillow, numpy and ffmpeg; fonts are in `fonts/`, from Google Fonts (OFL)). Captions and
crops live in the `SLIDES` list at the top of the script. `output/preview.mp4` (all slides back
to back) is built too but not committed.

## Reels

`python3 make_reel.py` builds two 1080×1920 (9:16) reels, about 35 s each and silent (add music in
Instagram), 3 s per slide with a short crossfade:

- `output/reel-photos.mp4`: every photo full-screen at full height, with the same captions and doodles.
- `output/reel-carousel.mp4`: the framed carousel slides, centred on the cream background.

Crops and caption heights for the photo reel are in the `REEL` table in `make_carousel.py`.
