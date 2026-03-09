"""
pin_layouts.py - Diverse visual layouts for Pinterest pin images.

Six distinct layout styles to prevent repetitive posting flags:
- card_dark: Dark card with design centered (original, improved)
- tshirt_photo: Real Printify mockup photo in Pinterest format
- poster_frame: Design displayed in a framed poster on a wall
- gradient: Design on a color gradient background
- split: Top design area + bottom info section
- minimal: Clean light background with generous whitespace
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH = 1000
HEIGHT = 1500

# ── Color palette ──────────────────────────────────────────────────
PALETTE = {
    "black": (26, 26, 26),
    "dark": (17, 17, 17),
    "charcoal": (42, 42, 42),
    "gray": (136, 136, 136),
    "light_gray": (220, 220, 220),
    "off_white": (245, 245, 240),
    "white": (255, 255, 255),
    "orange": (232, 80, 10),
    "cream": (250, 245, 235),
    "warm_wall": (235, 225, 210),
    "cool_wall": (215, 220, 230),
    "sage_wall": (215, 225, 210),
}

GRADIENTS = {
    "orange_dark": [(232, 80, 10), (26, 26, 26)],
    "teal_dark": [(0, 128, 128), (17, 17, 17)],
    "blue_dark": [(30, 60, 120), (17, 17, 17)],
    "red_dark": [(160, 30, 30), (17, 17, 17)],
    "purple_dark": [(80, 30, 120), (17, 17, 17)],
}


# ── Font helpers ───────────────────────────────────────────────────
def _hex(c):
    if isinstance(c, tuple):
        return c
    h = c.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _font_bold(size):
    for p in ["C:/Windows/Fonts/impact.ttf", "C:/Windows/Fonts/arialbd.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _font_medium(size):
    for p in ["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _font_regular(size):
    for p in ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [text]


def _center_text(draw, text, font, y, fill, width=WIDTH):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((width - tw) // 2, y), text, fill=fill, font=font)
    return y + bbox[3] - bbox[1] + 10


def _load_design(path, max_w, max_h):
    if not path or not Path(path).exists():
        return None
    img = Image.open(path)
    img.thumbnail((max_w, max_h), Image.LANCZOS)
    return img


def _draw_gradient(canvas, start, end):
    draw = ImageDraw.Draw(canvas)
    w, h = canvas.size
    for i in range(h):
        ratio = i / h
        r = int(start[0] + (end[0] - start[0]) * ratio)
        g = int(start[1] + (end[1] - start[1]) * ratio)
        b = int(start[2] + (end[2] - start[2]) * ratio)
        draw.line([(0, i), (w, i)], fill=(r, g, b))


# ── Layout 1: Dark Card (improved) ────────────────────────────────
def layout_card_dark(design_path, headline, cta, bg_color="#1a1a1a",
                     accent_color="#E8500A", **_kw):
    bg = _hex(bg_color)
    accent = _hex(accent_color)
    canvas = Image.new("RGB", (WIDTH, HEIGHT), bg)
    draw = ImageDraw.Draw(canvas)

    # Top accent
    draw.rectangle([(0, 0), (WIDTH, 6)], fill=accent)

    # Headline
    font_h = _font_bold(52)
    lines = _wrap(draw, headline.upper(), font_h, WIDTH - 80)
    y = 50
    for line in lines:
        y = _center_text(draw, line, font_h, y, PALETTE["white"])

    # Design
    design = _load_design(design_path, WIDTH - 80, 880)
    if design:
        px = (WIDTH - design.width) // 2
        py = 230 + (880 - design.height) // 2
        if design.mode == "RGBA":
            canvas.paste(design, (px, py), design)
        else:
            canvas.paste(design, (px, py))

    # Bottom
    draw.rectangle([(0, 1180), (WIDTH, 1188)], fill=accent)
    font_cta = _font_medium(38)
    _center_text(draw, cta, font_cta, 1220, accent)
    font_brand = _font_regular(22)
    _center_text(draw, "ROTATIONCLUB", font_brand, 1330, PALETTE["gray"])
    draw.rectangle([(0, HEIGHT - 6), (WIDTH, HEIGHT)], fill=accent)

    return canvas


# ── Layout 2: T-shirt Photo Mockup ────────────────────────────────
def layout_tshirt_photo(design_path, headline, cta, accent_color="#E8500A",
                        mockup_dir=None, **_kw):
    accent = _hex(accent_color)

    # Try real Printify mockup photo
    if mockup_dir and Path(mockup_dir).exists():
        files = sorted(Path(mockup_dir).glob("*.jpg")) + sorted(Path(mockup_dir).glob("*.png"))
        if files:
            # Prefer default (actual product photo), skip size charts
            defaults = [f for f in files if "default" in f.stem]
            product = [f for f in files if "angle" not in f.stem and "default" not in f.stem]
            pick = defaults[0] if defaults else (product[0] if product else files[0])
            return _layout_with_photo(Image.open(pick), headline, cta, accent)

    # Fallback: clean flat tee representation
    return _layout_flat_tee(design_path, headline, cta, accent)


def _layout_with_photo(photo, headline, cta, accent):
    """Pin using a real Printify product photo."""
    canvas = Image.new("RGB", (WIDTH, HEIGHT), PALETTE["off_white"])
    draw = ImageDraw.Draw(canvas)

    # Photo fills top ~63%
    photo_h = 950
    photo.thumbnail((WIDTH, photo_h), Image.LANCZOS)
    px = (WIDTH - photo.width) // 2
    canvas.paste(photo, (px, 0))

    # Soft fade at bottom of photo into background
    fade = Image.new("RGBA", (WIDTH, 120), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fade)
    bg = PALETTE["off_white"]
    for i in range(120):
        alpha = int(255 * (i / 120))
        fd.line([(0, i), (WIDTH, i)], fill=(bg[0], bg[1], bg[2], alpha))
    canvas.paste(Image.new("RGB", (WIDTH, 120), bg),
                 (0, photo.height - 60), fade.split()[3])

    # Info below photo
    y = photo.height + 10
    draw = ImageDraw.Draw(canvas)

    draw.rectangle([(60, y), (WIDTH - 60, y + 4)], fill=accent)
    y += 30

    font_h = _font_bold(44)
    lines = _wrap(draw, headline.upper(), font_h, WIDTH - 100)
    for line in lines:
        y = _center_text(draw, line, font_h, y, PALETTE["black"])
    y += 15

    font_cta = _font_medium(34)
    _center_text(draw, cta, font_cta, y, accent)

    font_brand = _font_regular(22)
    _center_text(draw, "ROTATIONCLUB | Sneaker Culture Apparel", font_brand,
                 HEIGHT - 60, PALETTE["gray"])
    draw.rectangle([(0, HEIGHT - 6), (WIDTH, HEIGHT)], fill=accent)

    return canvas


def _layout_flat_tee(design_path, headline, cta, accent):
    """Fallback: design on a clean folded-tee shape."""
    canvas = Image.new("RGB", (WIDTH, HEIGHT), PALETTE["light_gray"])
    draw = ImageDraw.Draw(canvas)

    # Headline
    font_h = _font_bold(44)
    _center_text(draw, headline.upper(), font_h, 50, PALETTE["black"])

    # Folded tee shape (simple rounded rect + v-neck hint)
    tee_w, tee_h = 600, 680
    tee_x = (WIDTH - tee_w) // 2
    tee_y = 200

    # Shadow
    draw.rounded_rectangle(
        [(tee_x + 6, tee_y + 6), (tee_x + tee_w + 6, tee_y + tee_h + 6)],
        radius=18, fill=(180, 180, 180),
    )
    # Tee body
    draw.rounded_rectangle(
        [(tee_x, tee_y), (tee_x + tee_w, tee_y + tee_h)],
        radius=18, fill=PALETTE["white"],
    )
    # V-neck detail
    cx = tee_x + tee_w // 2
    draw.polygon([(cx - 35, tee_y), (cx, tee_y + 30), (cx + 35, tee_y)],
                 fill=PALETTE["light_gray"])

    # Design on chest
    design = _load_design(design_path, 340, 380)
    if design:
        dx = (WIDTH - design.width) // 2
        dy = tee_y + 130
        if design.mode == "RGBA":
            canvas.paste(design, (dx, dy), design)
        else:
            canvas.paste(design, (dx, dy))

    # Bottom info
    draw.rectangle([(0, 1040), (WIDTH, 1048)], fill=accent)
    font_cta = _font_medium(36)
    _center_text(draw, cta, font_cta, 1090, accent)
    font_detail = _font_regular(26)
    _center_text(draw, "Premium Cotton Tee | Multiple Colors", font_detail,
                 1180, PALETTE["charcoal"])
    font_brand = _font_regular(22)
    _center_text(draw, "ROTATIONCLUB", font_brand, HEIGHT - 70, PALETTE["gray"])
    draw.rectangle([(0, HEIGHT - 6), (WIDTH, HEIGHT)], fill=accent)

    return canvas


# ── Layout 3: Poster Frame ────────────────────────────────────────
def layout_poster_frame(design_path, headline, cta, accent_color="#E8500A",
                        wall_style="warm", **_kw):
    wall = PALETTE.get(f"{wall_style}_wall", PALETTE["warm_wall"])
    accent = _hex(accent_color)
    canvas = Image.new("RGB", (WIDTH, HEIGHT), wall)
    draw = ImageDraw.Draw(canvas)

    # Frame dimensions
    frame_w, frame_h = 620, 780
    frame_x = (WIDTH - frame_w) // 2
    frame_y = 120
    border = 16
    mat = 28

    # Shadow behind frame
    shadow_c = tuple(max(0, c - 35) for c in wall)
    draw.rectangle(
        [(frame_x + 8, frame_y + 8),
         (frame_x + frame_w + 8, frame_y + frame_h + 8)],
        fill=shadow_c,
    )

    # Frame (dark)
    draw.rectangle(
        [(frame_x, frame_y), (frame_x + frame_w, frame_y + frame_h)],
        fill=(30, 30, 30),
    )

    # Mat (white inner border)
    draw.rectangle(
        [(frame_x + border, frame_y + border),
         (frame_x + frame_w - border, frame_y + frame_h - border)],
        fill=PALETTE["off_white"],
    )

    # Design inside mat
    da_x = frame_x + border + mat
    da_y = frame_y + border + mat
    da_w = frame_w - 2 * (border + mat)
    da_h = frame_h - 2 * (border + mat)

    design = _load_design(design_path, da_w, da_h)
    if design:
        dx = da_x + (da_w - design.width) // 2
        dy = da_y + (da_h - design.height) // 2
        if design.mode == "RGBA":
            canvas.paste(design, (dx, dy), design)
        else:
            canvas.paste(design, (dx, dy))

    # Text below frame
    y = frame_y + frame_h + 50
    font_h = _font_bold(42)
    lines = _wrap(draw, headline.upper(), font_h, WIDTH - 100)
    for line in lines:
        y = _center_text(draw, line, font_h, y, PALETTE["black"])
    y += 10

    font_cta = _font_medium(32)
    _center_text(draw, cta, font_cta, y, accent)

    font_sub = _font_regular(24)
    _center_text(draw, "Available as Premium Poster Print", font_sub,
                 y + 55, PALETTE["gray"])

    font_brand = _font_regular(22)
    _center_text(draw, "ROTATIONCLUB", font_brand, HEIGHT - 60, PALETTE["gray"])

    return canvas


# ── Layout 4: Gradient Showcase ────────────────────────────────────
def layout_gradient(design_path, headline, cta, accent_color="#E8500A",
                    gradient_style="orange_dark", **_kw):
    colors = GRADIENTS.get(gradient_style, GRADIENTS["orange_dark"])
    accent = _hex(accent_color)

    canvas = Image.new("RGB", (WIDTH, HEIGHT), colors[1])
    _draw_gradient(canvas, colors[0], colors[1])
    draw = ImageDraw.Draw(canvas)

    # Headline
    font_h = _font_bold(52)
    lines = _wrap(draw, headline.upper(), font_h, WIDTH - 80)
    y = 60
    for line in lines:
        y = _center_text(draw, line, font_h, y, PALETTE["white"])

    # Glow effect behind design
    design = _load_design(design_path, 700, 850)
    if design:
        glow_w = design.width + 80
        glow_h = design.height + 80
        glow = Image.new("RGB", (glow_w, glow_h), colors[1])
        gd = ImageDraw.Draw(glow)
        glow_color = tuple(min(255, c + 40) for c in colors[0])
        gd.rounded_rectangle([(0, 0), (glow_w, glow_h)], radius=30,
                             fill=glow_color)
        glow = glow.filter(ImageFilter.GaussianBlur(25))
        gx = (WIDTH - glow_w) // 2
        gy = 260 + (850 - glow_h) // 2
        canvas.paste(glow, (gx, gy))
        draw = ImageDraw.Draw(canvas)

        px = (WIDTH - design.width) // 2
        py = 300 + (850 - design.height) // 2
        if design.mode == "RGBA":
            canvas.paste(design, (px, py), design)
        else:
            canvas.paste(design, (px, py))
        draw = ImageDraw.Draw(canvas)

    # CTA
    font_cta = _font_medium(36)
    _center_text(draw, cta, font_cta, 1260, PALETTE["white"])
    font_brand = _font_regular(22)
    faded = tuple(min(255, c + 50) for c in colors[1])
    _center_text(draw, "ROTATIONCLUB", font_brand, 1360, faded)
    draw.rectangle([(0, HEIGHT - 6), (WIDTH, HEIGHT)], fill=accent)

    return canvas


# ── Layout 5: Split (top design + bottom info) ────────────────────
def layout_split(design_path, headline, cta, accent_color="#E8500A",
                 top_color="#1a1a1a", bottom_color="#f5f5f0", **_kw):
    top_c = _hex(top_color)
    bottom_c = _hex(bottom_color)
    accent = _hex(accent_color)

    split_y = 900
    canvas = Image.new("RGB", (WIDTH, HEIGHT), bottom_c)
    draw = ImageDraw.Draw(canvas)

    # Top section
    draw.rectangle([(0, 0), (WIDTH, split_y)], fill=top_c)

    # Diagonal split
    draw.polygon([(0, split_y), (WIDTH, split_y - 50), (WIDTH, split_y)],
                 fill=bottom_c)

    # Design in top
    design = _load_design(design_path, WIDTH - 100, split_y - 80)
    if design:
        px = (WIDTH - design.width) // 2
        py = (split_y - 50 - design.height) // 2
        if design.mode == "RGBA":
            canvas.paste(design, (px, py), design)
        else:
            canvas.paste(design, (px, py))

    # Bottom info
    y = split_y + 30
    text_c = PALETTE["black"] if sum(bottom_c) > 400 else PALETTE["white"]

    draw.rectangle([(80, y), (WIDTH - 80, y + 4)], fill=accent)
    y += 30

    font_h = _font_bold(42)
    lines = _wrap(draw, headline.upper(), font_h, WIDTH - 100)
    for line in lines:
        y = _center_text(draw, line, font_h, y, text_c)
    y += 10

    font_cta = _font_medium(34)
    _center_text(draw, cta, font_cta, y, accent)

    font_brand = _font_regular(22)
    _center_text(draw, "ROTATIONCLUB | Sneaker Culture Apparel", font_brand,
                 HEIGHT - 55, PALETTE["gray"])

    return canvas


# ── Layout 6: Minimal Light ───────────────────────────────────────
def layout_minimal(design_path, headline, cta, accent_color="#E8500A", **_kw):
    accent = _hex(accent_color)
    canvas = Image.new("RGB", (WIDTH, HEIGHT), PALETTE["white"])
    draw = ImageDraw.Draw(canvas)

    # Thin accent line
    draw.rectangle([(120, 45), (WIDTH - 120, 48)], fill=accent)

    # Subtle headline
    font_h = _font_medium(30)
    _center_text(draw, headline.upper(), font_h, 75, PALETTE["gray"])

    # Large design with generous space
    design = _load_design(design_path, WIDTH - 140, 1000)
    if design:
        px = (WIDTH - design.width) // 2
        py = 180 + (1000 - design.height) // 2
        if design.mode == "RGBA":
            canvas.paste(design, (px, py), design)
        else:
            canvas.paste(design, (px, py))

    # Clean bottom
    draw.rectangle([(120, 1260), (WIDTH - 120, 1263)], fill=PALETTE["light_gray"])
    font_cta = _font_medium(34)
    _center_text(draw, cta, font_cta, 1295, accent)
    font_brand = _font_regular(22)
    _center_text(draw, "ROTATIONCLUB", font_brand, 1390, PALETTE["light_gray"])
    draw.rectangle([(120, HEIGHT - 35), (WIDTH - 120, HEIGHT - 32)], fill=accent)

    return canvas


# ── Dispatcher ─────────────────────────────────────────────────────
LAYOUT_MAP = {
    "card_dark": layout_card_dark,
    "tshirt_photo": layout_tshirt_photo,
    "poster_frame": layout_poster_frame,
    "gradient": layout_gradient,
    "split": layout_split,
    "minimal": layout_minimal,
}


def build_layout(layout_name: str, design_path, template: dict,
                 mockup_dir=None) -> Image.Image:
    """Build a pin image using the specified layout."""
    headline = template.get("headline_placeholder", "")
    cta = template.get("cta", "Shop now")
    accent = template.get("footer_accent", "#E8500A")
    bg = template.get("background", "#1a1a1a")
    opts = template.get("layout_options", {})

    func = LAYOUT_MAP.get(layout_name, layout_card_dark)

    kwargs = {
        "design_path": design_path,
        "headline": headline,
        "cta": cta,
        "accent_color": accent,
    }

    if layout_name == "card_dark":
        kwargs["bg_color"] = bg
    elif layout_name == "tshirt_photo":
        kwargs["mockup_dir"] = mockup_dir
    elif layout_name == "poster_frame":
        kwargs["wall_style"] = opts.get("wall_style", "warm")
    elif layout_name == "gradient":
        kwargs["gradient_style"] = opts.get("gradient_style", "orange_dark")
    elif layout_name == "split":
        kwargs["top_color"] = opts.get("top_color", "#1a1a1a")
        kwargs["bottom_color"] = opts.get("bottom_color", "#f5f5f0")

    return func(**kwargs)
