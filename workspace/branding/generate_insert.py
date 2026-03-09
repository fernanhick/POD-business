"""
Generate package insert cards for Printify (single-sided).
Two versions: landscape (1795x1193) and portrait (1193x1795).
Left/Top: Sneaker ID form (cream, writable).
Right/Bottom: RotationClub branding + Thank you + SneakersBook promo.

Font sizes calibrated for 300 DPI printing at 6"x4" physical size.
At 300 DPI: 1pt ≈ 4.17px, so e.g. 10pt ≈ 42px.
"""
import os
import qrcode
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))

ORANGE = "#FF6B1A"
DARK = "#1A1A1A"
WHITE = "#FFFFFF"
CREAM = "#F5F1EB"
MID_GREY = "#999999"
CHARCOAL = "#333333"
LINE_COLOR = "#C0B8AD"


def get_font(size, bold=False):
    candidates_bold = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
    ]
    candidates_regular = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
    ]
    for path in (candidates_bold if bold else candidates_regular):
        if os.path.isfile(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_centered_text(draw, text, y, font, fill, cx):
    """Draw text centered around cx."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text((cx - tw // 2, y), text, font=font, fill=fill)
    return bbox[3] - bbox[1]


def draw_sneaker_id(draw, x, y, w, h, max_notes=None, vcenter=False, scale=1.0):
    """Draw the Sneaker ID form fields within a bounding box.

    scale=1.0 for full-size landscape card, ~0.65 for 2-up compact cards.
    """
    s = scale
    margin = int(70 * s)
    fx = x + margin

    font_header = get_font(int(72 * s), bold=True)   # ~17pt at scale=1
    font_label = get_font(int(30 * s), bold=True)     # ~7pt at scale=1

    field_w = w - margin * 2
    half_gap = int(50 * s)
    half_w = (field_w - half_gap) // 2
    row_h = int(90 * s)
    notes_count = max_notes if max_notes is not None else 4
    line_spacing = int(50 * s)

    header_h = int(90 * s)
    underline_w = int(340 * s)
    header_gap = int(120 * s)
    label_gap = int(38 * s)
    line_w = max(1, int(2 * s))
    accent_w = max(2, int(5 * s))

    # Calculate total content height for optional vertical centering
    content_h = (header_gap +
                 (label_gap + row_h) +       # SHOE NAME
                 3 * (label_gap + row_h) +   # 3 double rows
                 label_gap + notes_count * line_spacing)  # NOTES

    if vcenter:
        fy = y + max(margin, (h - content_h) // 2)
    else:
        fy = y + margin

    draw.text((fx, fy), "SNEAKER ID", font=font_header, fill=CHARCOAL)
    draw.line([(fx, fy + header_h), (fx + underline_w, fy + header_h)],
              fill=ORANGE, width=accent_w)

    cy = fy + header_gap

    # SHOE NAME (full width)
    draw.text((fx, cy), "SHOE NAME", font=font_label, fill=MID_GREY)
    cy += label_gap
    draw.line([(fx, cy + row_h - int(40 * s)),
               (fx + field_w, cy + row_h - int(40 * s))],
              fill=LINE_COLOR, width=line_w)
    cy += row_h

    # Double rows
    doubles = [("BRAND", "COLORWAY"), ("SIZE", "CONDITION"),
               ("DATE COPPED", "RETAIL / RESALE")]
    for left, right in doubles:
        draw.text((fx, cy), left, font=font_label, fill=MID_GREY)
        draw.text((fx + half_w + half_gap, cy), right, font=font_label, fill=MID_GREY)
        cy += label_gap
        draw.line([(fx, cy + row_h - int(40 * s)),
                   (fx + half_w, cy + row_h - int(40 * s))],
                  fill=LINE_COLOR, width=line_w)
        draw.line([(fx + half_w + half_gap, cy + row_h - int(40 * s)),
                   (fx + field_w, cy + row_h - int(40 * s))],
                  fill=LINE_COLOR, width=line_w)
        cy += row_h

    # NOTES
    draw.text((fx, cy), "NOTES", font=font_label, fill=MID_GREY)
    cy += label_gap
    for i in range(notes_count):
        draw.line([(fx, cy + line_spacing * (i + 1)),
                   (fx + field_w, cy + line_spacing * (i + 1))],
                  fill=LINE_COLOR, width=line_w)


def draw_branding(draw, img, x, y, w, h):
    """Draw the RotationClub branding section (full-size landscape card)."""
    cx = x + w // 2

    # Dark background
    draw.rectangle([(x, y), (x + w, y + h)], fill=DARK)

    # Top orange accent
    accent_w = min(500, w - 120)
    accent_y = y + 80
    draw.line([(cx - accent_w // 2, accent_y), (cx + accent_w // 2, accent_y)],
              fill=ORANGE, width=5)

    # "ROTATION" / "CLUB" — ~29pt
    font_r = get_font(min(120, w // 4), bold=True)
    draw_centered_text(draw, "ROTATION", accent_y + 30, font_r, WHITE, cx)
    r_bbox = draw.textbbox((0, 0), "ROTATION", font=font_r)
    r_h = r_bbox[3] - r_bbox[1]
    draw_centered_text(draw, "CLUB", accent_y + 30 + r_h + 8, font_r, ORANGE, cx)
    c_bbox = draw.textbbox((0, 0), "CLUB", font=font_r)
    c_h = c_bbox[3] - c_bbox[1]

    # Tagline — ~6pt
    tag_y = accent_y + 30 + r_h + 8 + c_h + 25
    font_tag = get_font(25, bold=False)
    draw_centered_text(draw, "SNEAKER CULTURE APPAREL", tag_y, font_tag, MID_GREY, cx)

    # Bottom orange accent
    draw.line([(cx - accent_w // 2, tag_y + 45), (cx + accent_w // 2, tag_y + 45)],
              fill=ORANGE, width=5)

    # "Thank you for your purchase!" — ~10pt
    ty = tag_y + 85
    font_thank = get_font(42, bold=False)
    draw_centered_text(draw, "Thank you for your purchase!", ty, font_thank, "#CCCCCC", cx)

    # Hint text — ~6pt
    font_flip = get_font(25, bold=False)
    draw_centered_text(draw, "Use this card as a label for your sneaker box",
                       ty + 60, font_flip, "#555555", cx)

    # ── SneakersBook section ──
    div_y = y + h - 280
    draw.line([(x + 60, div_y), (x + w - 60, div_y)], fill="#2A2A2A", width=1)

    sb_logo_path = os.path.join(HERE, "appstore.png")
    if os.path.isfile(sb_logo_path):
        sb_logo = Image.open(sb_logo_path).convert("RGBA")
        sb_size = 110
        sb_logo = sb_logo.resize((sb_size, sb_size), Image.LANCZOS)
        block_w = sb_size + 25 + 420
        bx = cx - block_w // 2
        by = div_y + 35
        img.paste(sb_logo, (bx, by), sb_logo)

        font_app = get_font(38, bold=True)     # ~9pt
        font_desc = get_font(26, bold=False)    # ~6pt
        font_url = get_font(25, bold=False)     # ~6pt
        tx = bx + sb_size + 25
        draw.text((tx, by + 8), "SneakersBook", font=font_app, fill=WHITE)
        draw.text((tx, by + 52), "Track your sneaker collection digitally",
                  font=font_desc, fill=MID_GREY)
        draw.text((tx, by + 85), "www.sneakersbook.com", font=font_url, fill=ORANGE)

    # Footer — ~5pt
    font_footer = get_font(22, bold=False)
    draw_centered_text(draw, "rotationclub.etsy.com", y + h - 40, font_footer, "#444444", cx)


def draw_branding_compact(draw, img, x, y, w, h):
    """Compact branding for half-height 2-up cards — vertically centered."""
    cx = x + w // 2

    # Dark background
    draw.rectangle([(x, y), (x + w, y + h)], fill=DARK)

    # Measure total content height to center vertically
    font_size = min(80, w // 5)   # ~19pt
    font_r = get_font(font_size, bold=True)
    r_bbox = draw.textbbox((0, 0), "ROTATION", font=font_r)
    r_h = r_bbox[3] - r_bbox[1]
    c_bbox = draw.textbbox((0, 0), "CLUB", font=font_r)
    c_h = c_bbox[3] - c_bbox[1]

    # Calculate total content height for centering
    # accent → ROTATION → CLUB → tagline → accent → thank you → hint → divider → sneakersbook
    content_h = (25 + r_h + 5 + c_h + 12 + 22 + 75 + 32 + 42 + 22 + 58 + 1 + 18 + 80 + 30)
    start_y = y + max(20, (h - content_h) // 2)

    # Top orange accent
    accent_w = min(420, w - 80)
    accent_y = start_y
    draw.line([(cx - accent_w // 2, accent_y), (cx + accent_w // 2, accent_y)],
              fill=ORANGE, width=4)

    # "ROTATION" / "CLUB"
    draw_centered_text(draw, "ROTATION", accent_y + 25, font_r, WHITE, cx)
    draw_centered_text(draw, "CLUB", accent_y + 25 + r_h + 5, font_r, ORANGE, cx)

    # Tagline — ~5pt
    tag_y = accent_y + 25 + r_h + 5 + c_h + 12
    font_tag = get_font(20, bold=False)
    draw_centered_text(draw, "SNEAKER CULTURE APPAREL", tag_y, font_tag, MID_GREY, cx)

    # Bottom orange accent
    draw.line([(cx - accent_w // 2, tag_y + 35), (cx + accent_w // 2, tag_y + 35)],
              fill=ORANGE, width=4)

    # "Thank you for your purchase!" — ~7pt
    ty = tag_y + 75
    font_thank = get_font(30, bold=False)
    draw_centered_text(draw, "Thank you for your purchase!", ty, font_thank, "#CCCCCC", cx)

    # Use as label hint — ~5pt
    font_flip = get_font(20, bold=False)
    draw_centered_text(draw, "Use this card as a label for your sneaker box",
                       ty + 42, font_flip, "#555555", cx)

    # ── SneakersBook section ──
    div_y = ty + 100
    draw.line([(x + 40, div_y), (x + w - 40, div_y)], fill="#2A2A2A", width=1)

    sb_logo_path = os.path.join(HERE, "appstore.png")
    if os.path.isfile(sb_logo_path):
        sb_logo = Image.open(sb_logo_path).convert("RGBA")
        sb_size = 80
        sb_logo = sb_logo.resize((sb_size, sb_size), Image.LANCZOS)
        block_w = sb_size + 18 + 340
        bx = cx - block_w // 2
        by = div_y + 18
        img.paste(sb_logo, (bx, by), sb_logo)

        font_app = get_font(28, bold=True)     # ~7pt
        font_desc = get_font(20, bold=False)    # ~5pt
        font_url = get_font(20, bold=False)     # ~5pt
        tx = bx + sb_size + 18
        draw.text((tx, by + 5), "SneakersBook", font=font_app, fill=WHITE)
        draw.text((tx, by + 36), "Track your sneaker collection digitally",
                  font=font_desc, fill=MID_GREY)
        draw.text((tx, by + 60), "www.sneakersbook.com", font=font_url, fill=ORANGE)

    # Footer — ~4pt
    font_footer = get_font(18, bold=False)
    draw_centered_text(draw, "rotationclub.etsy.com", y + h - 25, font_footer, "#444444", cx)


def generate_landscape():
    """Landscape: 1795x1193. Left=Sneaker ID, Right=Branding."""
    W, H = 1795, 1193
    split = int(W * 0.55)  # sneaker ID gets 55%

    img = Image.new("RGB", (W, H), CREAM)
    draw = ImageDraw.Draw(img)

    # Left: Sneaker ID on cream (full scale)
    draw_sneaker_id(draw, 0, 0, split, H, scale=1.0)

    # Right: Branding on dark
    draw_branding(draw, img, split, 0, W - split, H)

    out = os.path.join(HERE, "insert_landscape.png")
    img.save(out, "PNG", dpi=(300, 300))
    print(f"  Landscape saved: {out}")


def generate_2up_portrait():
    """Portrait 1193x1795: Two identical mini landscape cards stacked.
    Each half = compact Sneaker ID (left) + Branding (right).
    Customer cuts along the center line to get 2 box labels."""
    W, H = 1193, 1795
    card_h = H // 2  # each card is half the height

    img = Image.new("RGB", (W, H), CREAM)
    draw = ImageDraw.Draw(img)

    for i in range(2):
        oy = i * card_h  # y offset for this card
        split = int(W * 0.55)

        # Left: Sneaker ID (compact — 2 notes lines, vertically centered)
        draw_sneaker_id(draw, 0, oy, split, card_h, max_notes=2,
                        vcenter=True, scale=0.65)

        # Right: Branding
        draw_branding_compact(draw, img, split, oy, W - split, card_h)

    # Dashed cut line in the middle
    mid_y = card_h
    dash_len = 18
    gap_len = 12
    x = 30
    while x < W - 30:
        draw.line([(x, mid_y), (min(x + dash_len, W - 30), mid_y)],
                  fill="#AAAAAA", width=2)
        x += dash_len + gap_len

    # Scissors icon hint
    font_cut = get_font(22, bold=False)
    draw.text((40, mid_y - 28), "\u2702", font=font_cut, fill="#AAAAAA")

    out = os.path.join(HERE, "insert_2up_portrait.png")
    img.save(out, "PNG", dpi=(300, 300))
    print(f"  2-up portrait saved: {out}")


if __name__ == "__main__":
    print("Generating package insert cards...")
    generate_landscape()
    generate_2up_portrait()
    print("Done!")
