"""Render an Instagram carousel ("a random day at the office").

Each slide is exported twice into output/:
  NN-name.mp4  animated slide (1080x1350, 4:5, 5 s, silent)
  NN-name.jpg  static slide (last frame of the animation)
plus preview.mp4 (all slides back to back) and contact-sheet.jpg.

Usage: python3 make_carousel.py [slide-number ...]
"""

import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "source")
OUT = os.path.join(HERE, "output")

W, H = 1080, 1350          # Instagram portrait 4:5
FPS = 30
DURATION = 5.0
BORDER = 30                # off-white frame around the photo
RADIUS = 22                # photo corner radius
PAD = 58                   # text inset from the photo edge

FRAME_COLOR = (247, 244, 238)
ACCENT = (242, 201, 76)    # warm yellow underline
WHITE = (255, 255, 255)

FONT_DIR = "/usr/share/fonts/opentype/inter"
TITLE_FONT = ImageFont.truetype(f"{FONT_DIR}/InterDisplay-SemiBold.otf", 74)
COVER_FONT = ImageFont.truetype(f"{FONT_DIR}/InterDisplay-SemiBold.otf", 92)
SUB_FONT = ImageFont.truetype(f"{FONT_DIR}/Inter-Regular.otf", 33)
CHIP_FONT = ImageFont.truetype(f"{FONT_DIR}/Inter-SemiBold.otf", 26)

# file, crop top (source px, chosen to drop the old burned-in captions), chip, title, subtitle
SLIDES = [
    ("01-cover.png", 290, "thu · 29 oct", "a random day\nat the office", "swipe  →"),
    ("02-fit-check.png", 300, "08:40 am", "quick fit check", "navy hoodie, black polo, beige cargos"),
    ("03-breakfast.png", 215, "09:05 am", "breakfast plan: coffee", "and a little tokyo on the screen"),
    ("04-work.png", 450, "09:30 am", "work mode: on", "four things on the list. optimistic."),
    ("05-meeting.png", 260, "11:00 am", "meeting o'clock", "back-to-back, as usual"),
    ("06-lunch.png", 380, "01:15 pm", "the lunch chapter", "tandoori chicken, rotis & curry"),
    ("07-pause.png", 230, "02:00 pm", "a little pause", "the cafeteria, minus the crowd"),
    ("08-recharge.png", 230, "02:30 pm", "recharge mode", "yes, there's a nap room"),
    ("09-desk.png", 240, "03:30 pm", "back to the desk", "with my green neighbours"),
    ("10-logging-off.png", 290, "06:00 pm", "logging off", "little moments, ordinary day"),
    ("11-traffic.jpg", 380, "06:30 pm", "and then…\nbangalore traffic", "the real final boss"),
]


def ease_out(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def progress(t, start, length):
    return ease_out((t - start) / length)


def load_photo(name, top):
    img = Image.open(os.path.join(SRC, name)).convert("RGB")
    sw, sh = img.size
    ch = round(sw * H / W)
    top = min(top, sh - ch)
    # render the photo slightly larger so the slow zoom stays sharp
    pw, ph = W - 2 * BORDER, H - 2 * BORDER
    return img.crop((0, top, sw, top + ch)).resize((int(pw * 1.08), int(ph * 1.08)), Image.LANCZOS)


def scrim(pw, ph):
    """Dark gradients at the bottom (caption) and top (chips) for legibility."""
    mask = Image.new("L", (pw, ph), 0)
    px = mask.load()
    bottom_start = int(ph * 0.48)
    for y in range(ph):
        a = 0
        if y > bottom_start:
            a = int(215 * ((y - bottom_start) / (ph - bottom_start)) ** 1.6)
        elif y < 170:
            a = int(70 * (1 - y / 170) ** 2)
        for x in range(pw):
            px[x, y] = a
    black = Image.new("RGBA", (pw, ph), (0, 0, 0, 255))
    black.putalpha(mask)
    return black


def wrap(text, font, max_w):
    if "\n" in text:
        return [part.split() for part in text.split("\n")]
    lines, line = [], []
    for word in text.split():
        trial = " ".join(line + [word])
        if line and font.getlength(trial) > max_w:
            lines.append(line)
            line = [word]
        else:
            line.append(word)
    lines.append(line)
    return lines


def draw_text(layer, pos, text, font, fill, alpha):
    """Composite text with a soft drop shadow onto layer."""
    m = 20
    l, t, r, b = font.getbbox(text)
    tile = Image.new("RGBA", (r + 2 * m, b + 2 * m), (0, 0, 0, 0))
    shadow = tile.copy()
    ImageDraw.Draw(shadow).text((m, m + 2), text, font=font, fill=(0, 0, 0, int(110 * alpha)))
    tile.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(6)))
    ImageDraw.Draw(tile).text((m, m), text, font=font, fill=fill + (int(255 * alpha),))
    layer.alpha_composite(tile, (int(pos[0]) - m, int(pos[1]) - m))


def render_frame(photo, overlay, rounded, slide, idx, total, t):
    chip, title, sub = slide[2], slide[3], slide[4]
    pw, ph = W - 2 * BORDER, H - 2 * BORDER

    # slow zoom-out: 1.08 -> 1.0 across the clip
    z = 1.08 - 0.08 * ease_out(t / DURATION)
    cw, chh = int(pw * z), int(ph * z)
    ox, oy = (photo.width - cw) // 2, (photo.height - chh) // 2
    frame_photo = photo.crop((ox, oy, ox + cw, oy + chh)).resize((pw, ph), Image.BILINEAR).convert("RGBA")
    frame_photo.alpha_composite(overlay)

    layer = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))

    # top chips: time on the left, slide counter on the right
    a = progress(t, 0.15, 0.6)
    if a > 0:
        tw = CHIP_FONT.getlength(chip)
        chip_box = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        d = ImageDraw.Draw(chip_box)
        x0, y0 = PAD - 18, PAD - 12 - int(10 * (1 - a))
        d.rounded_rectangle((x0, y0, x0 + tw + 36, y0 + 50), radius=25, fill=(255, 255, 255, int(235 * a)))
        d.text((x0 + 18, y0 + 10), chip, font=CHIP_FONT, fill=(30, 30, 30, int(255 * a)))
        counter = f"{idx:02d}/{total:02d}"
        cw2 = CHIP_FONT.getlength(counter)
        x1 = pw - PAD + 18
        d.rounded_rectangle((x1 - cw2 - 36, y0, x1, y0 + 50), radius=25, fill=(0, 0, 0, int(95 * a)))
        d.text((x1 - cw2 - 18, y0 + 10), counter, font=CHIP_FONT, fill=WHITE + (int(255 * a),))
        layer.alpha_composite(chip_box)

    # title: words rise in one after another
    font = COVER_FONT if idx == 1 else TITLE_FONT
    line_h = int(font.size * 1.12)
    lines = wrap(title, font, pw - 2 * PAD)
    sub_h = 56
    block_bottom = ph - PAD - sub_h - 26
    y = block_bottom - line_h * len(lines)
    word_i = 0
    last_line_w = 0
    for line in lines:
        x = PAD
        for word in line:
            wa = progress(t, 0.45 + 0.09 * word_i, 0.55)
            if wa > 0:
                draw_text(layer, (x, y + int(28 * (1 - wa))), word, font, WHITE, wa)
            x += font.getlength(word + " ")
            word_i += 1
        last_line_w = font.getlength(" ".join(line))
        y += line_h

    # accent underline draws from left to right
    ua = progress(t, 0.55 + 0.09 * word_i, 0.7)
    if ua > 0:
        d = ImageDraw.Draw(layer)
        uy = block_bottom + 14
        ulen = int(min(last_line_w, 220) * ua)
        d.rounded_rectangle((PAD, uy, PAD + max(ulen, 6), uy + 6), radius=3, fill=ACCENT + (255,))

    # subtitle fades in last
    sa = progress(t, 0.85 + 0.09 * word_i, 0.7)
    if sa > 0:
        draw_text(layer, (PAD, ph - PAD - sub_h + 12 + int(12 * (1 - sa))), sub, SUB_FONT, (240, 240, 240), sa)

    frame_photo.alpha_composite(layer)

    canvas = Image.new("RGB", (W, H), FRAME_COLOR)
    canvas.paste(frame_photo.convert("RGB"), (BORDER, BORDER), rounded)
    return canvas


def render_slide(i):
    slide = SLIDES[i]
    idx, total = i + 1, len(SLIDES)
    stem = os.path.splitext(slide[0])[0]
    photo = load_photo(slide[0], slide[1])
    pw, ph = W - 2 * BORDER, H - 2 * BORDER
    overlay = scrim(pw, ph)
    rounded = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(rounded).rounded_rectangle((0, 0, pw - 1, ph - 1), radius=RADIUS, fill=255)

    out_mp4 = os.path.join(OUT, f"{stem}.mp4")
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", out_mp4],
        stdin=subprocess.PIPE)
    frame = None
    for f in range(int(DURATION * FPS)):
        frame = render_frame(photo, overlay, rounded, slide, idx, total, f / FPS)
        ff.stdin.write(frame.tobytes())
    ff.stdin.close()
    ff.wait()
    frame.save(os.path.join(OUT, f"{stem}.jpg"), quality=95)
    print("rendered", stem)


def finish():
    stems = [os.path.splitext(s[0])[0] for s in SLIDES]
    with open(os.path.join(OUT, "list.txt"), "w") as fh:
        fh.writelines(f"file '{s}.mp4'\n" for s in stems)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", os.path.join(OUT, "list.txt"), "-c", "copy",
                    os.path.join(OUT, "preview.mp4")], check=True)
    os.remove(os.path.join(OUT, "list.txt"))

    cols, tw = 4, 360
    th = tw * H // W
    rows = (len(stems) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * th), FRAME_COLOR)
    for n, s in enumerate(stems):
        im = Image.open(os.path.join(OUT, f"{s}.jpg")).resize((tw, th), Image.LANCZOS)
        sheet.paste(im, ((n % cols) * tw, (n // cols) * th))
    sheet.save(os.path.join(OUT, "contact-sheet.jpg"), quality=90)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    picks = [int(a) - 1 for a in sys.argv[1:]] or range(len(SLIDES))
    for i in picks:
        render_slide(i)
    if not sys.argv[1:]:
        finish()
