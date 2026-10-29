"""Render an Instagram carousel ("a random day at the office").

Each slide is exported twice into output/:
  NN-name.mp4  animated slide (1080x1350, 4:5, 5 s, silent)
  NN-name.jpg  static slide (last frame of the animation)
plus preview.mp4 (all slides back to back) and contact-sheet.jpg.

Usage: python3 make_carousel.py [--stills] [slide-number ...]
"""

import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "source")
OUT = os.path.join(HERE, "output")
FONTS = os.path.join(HERE, "fonts")

W, H = 1080, 1350          # Instagram portrait 4:5
FPS = 30
DURATION = 5.0
BORDER = 30                # off-white frame around the photo
RADIUS = 22                # photo corner radius
PW, PH = W - 2 * BORDER, H - 2 * BORDER

FRAME_COLOR = (247, 244, 238)
ACCENT = (246, 205, 84)    # warm yellow for underline and doodles
WHITE = (255, 255, 255)


def font(path, size, variation=None):
    f = ImageFont.truetype(path, size)
    if variation:
        f.set_variation_by_name(variation)
    return f


TITLE_FONT = font(f"{FONTS}/DancingScript.ttf", 104, b"Bold")
COVER_FONT = font(f"{FONTS}/DancingScript.ttf", 118, b"Bold")
SUB_FONT = font(f"{FONTS}/Caveat.ttf", 50, b"Bold")
DOODLE_FONT = font(f"{FONTS}/Caveat.ttf", 64, b"Bold")
CHIP_FONT = font("/usr/share/fonts/opentype/inter/Inter-SemiBold.otf", 26)

# file, crop top (source px, chosen to drop the old burned-in captions),
# vertical centre of the caption block (fraction of photo height), chip (cover only), title, subtitle, doodle
SLIDES = [
    ("01-cover.png", 290, 0.75, "thu · 29 oct", "a random day\nat the office", "swipe", "arrow"),
    ("02-fit-check.png", 300, 0.80, None, "quick fit check", "navy hoodie · black polo · beige cargos", "sparkles"),
    ("03-breakfast.jpg", 120, 0.19, None, "breakfast plan", "barley, fresh fruit, seeds & honey", "sun"),
    ("04-work.png", 450, 0.47, None, "work mode: on", "four things on the list. optimistic.", "ticks"),
    ("05-meeting-coffee.png", 215, 0.585, None, "meetings + coffee", "and a little tokyo on the screen", "steam"),
    ("06-office.png", 260, 0.25, None, "office kind of day", "a slow walk around the floor", "stars"),
    ("07-lunch.png", 380, 0.50, None, "the lunch chapter", "tandoori chicken, rotis & curry", "heart"),
    ("08-pause.png", 230, 0.50, None, "a little pause", "the cafeteria, minus the crowd", "loops"),
    ("09-recharge.png", 230, 0.30, None, "recharge mode", "yes, there's a nap room", "zzz"),
    ("10-desk.png", 240, 0.33, None, "back to the desk", "with my green neighbours", "leaf"),
    ("11-logging-off.png", 290, 0.72, None, "logging off", "little moments, ordinary day", "moon"),
    ("12-gym.jpg", 700, 0.19, None, "fit body, fit mind", "one last set before the commute", "dumbbell"),
    ("13-traffic.jpg", 380, 0.83, None, "and then…\nbangalore traffic", "the real final boss", "spiral"),
]


# Reel (make_reel.py): 1080x1920 full-bleed, each photo shown at full height.
REEL_W, REEL_H = 1080, 1920
REEL_SLIDE = 3.0           # seconds per photo
REEL_SPEED = 1.6           # caption animation runs this much faster than in the carousel
# stem: crop top (source px, just below the old burned-in caption), horizontal centre (fraction),
#       vertical centre of the caption block, subtitle override
REEL = {
    "01-cover": (262, 0.5, 0.66, "a day in my life"),
    "02-fit-check": (200, 0.45, 0.72, None),
    "03-breakfast": (0, 0.5, 0.25, None),
    "04-work": (290, 0.55, 0.40, None),
    "05-meeting-coffee": (190, 0.5, 0.55, None),
    "06-office": (200, 0.45, 0.30, None),
    "07-lunch": (285, 0.45, 0.50, None),
    "08-pause": (200, 0.5, 0.50, None),
    "09-recharge": (200, 0.5, 0.33, None),
    "10-desk": (200, 0.5, 0.33, None),
    "11-logging-off": (262, 0.5, 0.66, None),
    "12-gym": (0, 0.5, 0.28, None),
    "13-traffic": (0, 0.5, 0.70, None),
}

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
    return img.crop((0, top, sw, top + ch)).resize((int(PW * 1.08), int(PH * 1.08)), Image.LANCZOS)


def load_reel_photo(name, top, cx, pw, ph):
    """Tallest 9:16 window below the old burned-in caption, centred at cx (fraction of width)."""
    img = Image.open(os.path.join(SRC, name)).convert("RGB")
    sw, sh = img.size
    ch = sh - top
    cw = min(sw, round(ch * pw / ph))
    ch = round(cw * ph / pw)
    x = min(max(int(sw * cx - cw / 2), 0), sw - cw)
    return img.crop((x, top, x + cw, top + ch)).resize((int(pw * 1.08), int(ph * 1.08)), Image.LANCZOS)


def top_scrim(pw, ph):
    """Light gradient at the top so the chips read on bright ceilings."""
    a = np.zeros((ph, pw), np.uint8)
    ys = np.arange(170)
    a[:170] = (70 * (1 - ys / 170) ** 2).astype(np.uint8)[:, None]
    layer = Image.new("RGBA", (pw, ph), (0, 0, 0, 255))
    layer.putalpha(Image.fromarray(a))
    return layer


def text_layer(text, fnt, fill, shadow=130, blur=7):
    """Text with a soft drop shadow on a tight RGBA tile; returns (tile, margin)."""
    m = 30
    l, t, r, b = fnt.getbbox(text)
    tile = Image.new("RGBA", (r + 2 * m, b + 2 * m), (0, 0, 0, 0))
    sh = tile.copy()
    ImageDraw.Draw(sh).text((m, m + 3), text, font=fnt, fill=(0, 0, 0, shadow))
    tile.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(tile).text((m, m), text, font=fnt, fill=fill + (255,))
    return tile, m


def with_alpha(tile, alpha):
    if alpha >= 1:
        return tile
    out = tile.copy()
    out.putalpha(out.getchannel("A").point(lambda v: int(v * alpha)))
    return out


def reveal(tile, p, feather=60):
    """Left-to-right write-on wipe with a soft edge."""
    if p >= 1:
        return tile
    arr = np.array(tile)
    x = np.arange(arr.shape[1])
    edge = p * (arr.shape[1] + feather)
    ramp = np.clip((edge - x) / feather, 0, 1)
    arr[..., 3] = (arr[..., 3] * ramp[None, :]).astype(np.uint8)
    return Image.fromarray(arr)


# ---------- doodles: lists of strokes (point lists) in photo coordinates ----------

def wave(x0, x1, y, amp=7, periods=3.0, n=60):
    return [(x0 + (x1 - x0) * i / n, y + amp * math.sin(2 * math.pi * periods * i / n)) for i in range(n + 1)]


def sparkle(cx, cy, r):
    pts = []
    for i in range(41):
        a = 2 * math.pi * i / 40
        # astroid: a four-pointed star with concave sides
        pts.append((cx + r * math.cos(a) ** 3, cy + r * math.sin(a) ** 3))
    return [pts]


def heart(cx, cy, s):
    pts = []
    for i in range(61):
        t = 2 * math.pi * i / 60
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * s, cy - y * s))
    return [pts]


def circle(cx, cy, r, a0=0, a1=2 * math.pi, n=40):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def doodle_strokes(kind, box, sub_box):
    """Strokes for a slide's doodle, placed around the title box (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = box
    cx = (x0 + x1) / 2
    if kind == "arrow":
        sx, sy = sub_box[2] + 16, (sub_box[1] + sub_box[3]) / 2 + 4
        curve = [((1 - u) ** 2 * sx + 2 * u * (1 - u) * (sx + 45) + u * u * (sx + 100),
                  (1 - u) ** 2 * sy + 2 * u * (1 - u) * (sy + 26) + u * u * (sy - 6)) for u in np.linspace(0, 1, 30)]
        ex, ey = curve[-1]
        head = [(ex - 22, ey - 14), (ex, ey), (ex - 16, ey + 18)]
        return [curve, head] + sparkle(x1 + 10, y0 - 4, 26) + sparkle(x0 - 26, y0 + 40, 16)
    if kind == "dumbbell":
        dx, dy = cx - 43, y0 - 34
        bar = [(dx, dy), (dx + 86, dy)]
        plates = [[(px, dy - h), (px, dy + h)] for px, h in ((dx + 12, 22), (dx + 24, 15), (dx + 62, 15), (dx + 74, 22))]
        return [bar] + plates + sparkle(x0 - 32, y0 + 20, 18)
    if kind == "sparkles":
        return sparkle(x1 + 18, y0 + 6, 30) + sparkle(x1 + 54, y0 + 54, 16) + sparkle(x0 - 30, y1 - 20, 20)
    if kind == "sun":
        sx, sy, r = x0 - 44, y0 + 30, 18
        rays = [[(sx + (r + 10) * math.cos(a), sy + (r + 10) * math.sin(a)),
                 (sx + (r + 26) * math.cos(a), sy + (r + 26) * math.sin(a))]
                for a in [i * math.pi / 4 for i in range(8)]]
        return [circle(sx, sy, r)] + rays
    if kind == "ticks":
        return [[(x0 - 66, y0 + 46), (x0 - 52, y0 + 62), (x0 - 24, y0 + 22)]] + sparkle(x1 + 30, y0 + 10, 22)
    if kind == "steam":
        strokes = []
        for k, dx in enumerate((-36, 0, 36)):
            h = 70 if k == 1 else 54
            strokes.append([(cx + dx + 9 * math.sin(2 * math.pi * 1.5 * i / 30), y0 - 18 - h * i / 30) for i in range(31)])
        return strokes
    if kind == "stars":
        return sparkle(x0 - 34, y0 + 10, 24) + sparkle(x1 + 30, y0 + 30, 20) + sparkle(x1 + 6, y1 + 6, 12)
    if kind == "heart":
        return heart(x1 + 44, y0 + 22, 2.0) + sparkle(x0 - 30, y0 + 18, 18)
    if kind == "loops":
        n = 90
        curl = [(x0 - 130 + 90 * i / n + 16 * math.sin(2 * math.pi * 3 * i / n),
                 y0 + 40 - 16 * math.cos(2 * math.pi * 3 * i / n)) for i in range(n + 1)]
        return [curl] + sparkle(x1 + 30, y0 + 10, 20)
    if kind == "leaf":
        lx, ly = x1 + 30, y0 + 10
        a = [(lx + 50 * i / 30, ly + 40 * i / 30 - 26 * math.sin(math.pi * i / 30)) for i in range(31)]
        b = [(lx + 50 * i / 30, ly + 40 * i / 30 + 18 * math.sin(math.pi * i / 30)) for i in range(31)]
        mid = [(lx - 14, ly - 10), (lx + 42, ly + 34)]
        return [a, b, mid]
    if kind == "moon":
        mx, my, r = x1 + 46, y0 + 20, 30
        outer = circle(mx, my, r, math.radians(60), math.radians(300))
        inner = circle(mx + 14, my, r * 0.78, math.radians(300), math.radians(60))
        return [outer, inner] + sparkle(x0 - 30, y0 + 16, 16)
    if kind == "spiral":
        sx, sy = x1 + 30, y0 + 70
        sp = [(sx + 3.2 * a * math.cos(a), sy + 3.2 * a * math.sin(a)) for a in np.linspace(0, 6 * math.pi, 90)]
        return [sp, [(x0 - 40, y0 + 10), (x0 - 46, y0 + 58)], [(x0 - 20, y0 + 6), (x0 - 26, y0 + 54)],
                circle(x0 - 47, y0 + 76, 3), circle(x0 - 27, y0 + 72, 3)]
    return []


def draw_strokes(layer, strokes, p, color, width=6):
    """Draw the first fraction p of the strokes' total length."""
    lengths = [sum(math.dist(s[i], s[i + 1]) for i in range(len(s) - 1)) for s in strokes]
    budget = p * sum(lengths)
    d = ImageDraw.Draw(layer)
    for s, L in zip(strokes, lengths):
        if budget <= 0:
            break
        pts, used = [s[0]], 0.0
        for i in range(len(s) - 1):
            seg = math.dist(s[i], s[i + 1])
            if used + seg > budget:
                f = (budget - used) / seg
                pts.append((s[i][0] + (s[i + 1][0] - s[i][0]) * f, s[i][1] + (s[i + 1][1] - s[i][1]) * f))
                break
            pts.append(s[i + 1])
            used += seg
        budget -= L
        if len(pts) > 1:
            d.line(pts, fill=color + (255,), width=width, joint="curve")
        for x, y in (pts[0], pts[-1]):
            d.ellipse((x - width / 2 + 0.5, y - width / 2 + 0.5, x + width / 2 - 0.5, y + width / 2 - 0.5), fill=color + (255,))


def shadowed(layer):
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    sh.putalpha(layer.getchannel("A").point(lambda v: int(v * 0.5)).filter(ImageFilter.GaussianBlur(5)))
    out = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    out.alpha_composite(sh, (0, 3))
    out.alpha_composite(layer)
    return out


class Slide:
    def __init__(self, i, reel=False):
        name, top, anchor, self.chip, title, sub, self.doodle = SLIDES[i]
        self.idx, self.total = i + 1, len(SLIDES)
        self.stem = os.path.splitext(name)[0]
        self.reel = reel
        if reel:
            # full-bleed 9:16, no frame or chips, captions animate faster
            r_top, r_cx, anchor, r_sub = REEL[self.stem]
            sub = r_sub or sub
            self.w, self.h, self.border = REEL_W, REEL_H, 0
            self.pw, self.ph = REEL_W, REEL_H
            self.speed, self.dur = REEL_SPEED, REEL_SLIDE
            self.photo = load_reel_photo(name, r_top, r_cx, self.pw, self.ph)
        else:
            self.w, self.h, self.border = W, H, BORDER
            self.pw, self.ph = PW, PH
            self.speed, self.dur = 1.0, DURATION
            self.photo = load_photo(name, top)
        PW_, PH_ = self.pw, self.ph
        self.scrim = top_scrim(PW_, PH_)
        self.mask = Image.new("L", (PW_, PH_), 0)
        ImageDraw.Draw(self.mask).rounded_rectangle((0, 0, PW_ - 1, PH_ - 1), radius=0 if reel else RADIUS, fill=255)

        # caption block: centred title lines, wavy underline, handwritten subtitle
        fnt = COVER_FONT if self.idx == 1 else TITLE_FONT
        self.lines = [text_layer(line, fnt, WHITE) for line in title.split("\n")]
        line_h = int(fnt.size * 1.08)
        self.sub = text_layer(sub, SUB_FONT, (255, 246, 222))
        block_h = line_h * len(self.lines) + 34 + 64
        y = int(PH_ * anchor - block_h / 2)
        self.line_pos = []
        widths = []
        for tile, m in self.lines:
            w = tile.width - 2 * m
            widths.append(w)
            self.line_pos.append(((PW_ - w) // 2 - m, y - m - int(fnt.size * 0.12)))
            y += line_h
        title_box = ((PW_ - max(widths)) / 2, y - line_h * len(self.lines), (PW_ + max(widths)) / 2, y)
        ul_w = min(max(widths) * 0.55, 340)
        self.underline = [wave(PW_ / 2 - ul_w / 2, PW_ / 2 + ul_w / 2, y + 14, amp=6, periods=2.5)]
        sw = self.sub[0].width - 2 * self.sub[1]
        sub_y = y + 30
        self.sub_pos = ((PW_ - sw) // 2 - self.sub[1], sub_y - self.sub[1])
        sub_box = ((PW_ - sw) / 2, sub_y, (PW_ + sw) / 2, sub_y + 56)
        self.doodles = doodle_strokes(self.doodle, title_box, sub_box)

        # soft dark glow behind the caption so it reads on any photo
        glow = Image.new("L", (PW_, PH_), 0)
        bw = max(max(widths), sw) / 2 + 120
        top_y, bot_y = title_box[1] - 50, sub_box[3] + 40
        ImageDraw.Draw(glow).ellipse((PW_ / 2 - bw, top_y, PW_ / 2 + bw, bot_y), fill=120)
        self.glow = glow.filter(ImageFilter.GaussianBlur(70))

    def frame(self, t):
        PW_, PH_ = self.pw, self.ph
        z = 1.08 - 0.08 * ease_out(t / self.dur)    # slow zoom-out
        t *= self.speed                              # caption animation clock
        cw, ch = int(PW_ * z), int(PH_ * z)
        ox, oy = (self.photo.width - cw) // 2, (self.photo.height - ch) // 2
        img = self.photo.crop((ox, oy, ox + cw, oy + ch)).resize((PW_, PH_), Image.BILINEAR).convert("RGBA")
        if not self.reel:
            img.alpha_composite(self.scrim)

        ga = progress(t, 0.2, 0.8)
        if ga > 0:
            g = Image.new("RGBA", (PW_, PH_), (0, 0, 0, 255))
            g.putalpha(self.glow.point(lambda v: int(v * ga)))
            img.alpha_composite(g)

        # chips: date on the cover, slide counter on the right (carousel only)
        a = progress(t, 0.15, 0.6)
        if a > 0 and not self.reel:
            d = ImageDraw.Draw(img)
            y0 = 46 - int(10 * (1 - a))
            if self.chip:
                tw = CHIP_FONT.getlength(self.chip)
                d.rounded_rectangle((40, y0, 40 + tw + 36, y0 + 50), radius=25, fill=(255, 255, 255, int(235 * a)))
                d.text((58, y0 + 10), self.chip, font=CHIP_FONT, fill=(30, 30, 30, int(255 * a)))
            counter = f"{self.idx:02d}/{self.total:02d}"
            cw2 = CHIP_FONT.getlength(counter)
            x1 = PW_ - 40
            chip = Image.new("RGBA", (PW_, PH_), (0, 0, 0, 0))
            cd = ImageDraw.Draw(chip)
            cd.rounded_rectangle((x1 - cw2 - 36, y0, x1, y0 + 50), radius=25, fill=(0, 0, 0, int(95 * a)))
            cd.text((x1 - cw2 - 18, y0 + 10), counter, font=CHIP_FONT, fill=WHITE + (int(255 * a),))
            img.alpha_composite(chip)

        # title is "written" line by line
        start = 0.45
        for (tile, m), pos in zip(self.lines, self.line_pos):
            p = min(max((t - start) / 1.0, 0), 1)
            if p > 0:
                img.alpha_composite(reveal(tile, p), pos)
            start += 0.85

        # underline and doodles draw on, subtitle fades in
        ink = Image.new("RGBA", (PW_, PH_), (0, 0, 0, 0))
        up = progress(t, start + 0.15, 0.6)
        if up > 0:
            draw_strokes(ink, self.underline, up, ACCENT, width=6)
        dp = progress(t, start + 0.5, 1.1)
        if dp > 0:
            if self.doodle == "zzz":
                x, y = self.line_pos[0][0] + self.lines[0][0].width - 20, self.line_pos[0][1]
                for k, (dx, dy, s) in enumerate(((0, 30, 0.8), (40, -14, 1.05), (92, -70, 1.35))):
                    za = min(max(dp * 3 - k, 0), 1)
                    if za > 0:
                        f = font(f"{FONTS}/Caveat.ttf", int(64 * s), b"Bold")
                        ImageDraw.Draw(ink).text((x + dx, y + dy), "z", font=f, fill=ACCENT + (int(255 * za),))
            else:
                draw_strokes(ink, self.doodles, dp, WHITE, width=5)
        img.alpha_composite(shadowed(ink))

        sa = progress(t, start + 0.35, 0.8)
        if sa > 0:
            tile, m = self.sub
            img.alpha_composite(with_alpha(tile, sa), (self.sub_pos[0], self.sub_pos[1] + int(14 * (1 - sa))))

        if self.reel:
            return img.convert("RGB")
        canvas = Image.new("RGB", (self.w, self.h), FRAME_COLOR)
        canvas.paste(img.convert("RGB"), (self.border, self.border), self.mask)
        return canvas


def render_slide(i, stills=False):
    s = Slide(i)
    if stills:
        s.frame(DURATION).save(os.path.join(OUT, f"{s.stem}.jpg"), quality=95)
        print("still", s.stem)
        return
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", os.path.join(OUT, f"{s.stem}.mp4")],
        stdin=subprocess.PIPE)
    frame = None
    for f in range(int(DURATION * FPS)):
        frame = s.frame(f / FPS)
        ff.stdin.write(frame.tobytes())
    ff.stdin.close()
    ff.wait()
    frame.save(os.path.join(OUT, f"{s.stem}.jpg"), quality=95)
    print("rendered", s.stem)


def finish(stills):
    stems = [os.path.splitext(s[0])[0] for s in SLIDES]
    if not stills:
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
    args = sys.argv[1:]
    stills = "--stills" in args
    picks = [int(a) - 1 for a in args if a.isdigit()]
    for i in picks or range(len(SLIDES)):
        render_slide(i, stills)
    if not picks:
        finish(stills)
