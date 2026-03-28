from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .keyword_service import select_keywords
from .models import PinResponse, PinStatus, PinType, get_conn

BASE_DIR = Path(__file__).resolve().parents[4]
WORKSPACE_DIR = BASE_DIR / "workspace"
APPROVED_DIR = WORKSPACE_DIR / "front_a_sneaker" / "approved"
PINS_DIR = WORKSPACE_DIR / "pinterest" / "pins"
TEMPLATES_FILE = WORKSPACE_DIR / "pinterest" / "pin_templates.json"
APP_TEMPLATES_FILE = WORKSPACE_DIR / "pinterest" / "app_pin_templates.json"

# Canvas dimensions (Pinterest 2:3)
WIDTH = 1000
HEIGHT = 1500

# Brand colors
BLACK = "#1a1a1a"
ORANGE = "#E8500A"
WHITE = "#FFFFFF"
GRAY = "#888888"
LIGHT = "#f5f5f0"


def _load_design_metadata_index() -> dict[str, dict[str, str | None]]:
    metadata: dict[str, dict[str, str | None]] = {}
    for path in sorted((WORKSPACE_DIR / "logs").glob("front_*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        rows = payload if isinstance(payload, list) else [payload]
        for row in rows:
            if not isinstance(row, dict):
                continue
            filename = row.get("filename")
            if not filename:
                continue
            metadata[filename] = {
                "style": row.get("style"),
                "color_palette": row.get("color_palette"),
            }
    return metadata


def _variant_label_from_palette(palette: str | None) -> str | None:
    if not palette:
        return None
    descriptor = palette.split(",", 1)[1].strip() if "," in palette else palette.strip()
    descriptor = re.sub(r"\b(aesthetic|finish|warmth|look)\b", "", descriptor, flags=re.IGNORECASE)
    descriptor = re.sub(r"\s+", " ", descriptor).strip()
    if not descriptor:
        return None
    return " ".join(descriptor.split()[:3]).title()


def _variant_label_from_style(style: str | None) -> str | None:
    if not style:
        return None
    normalized = style.replace("+", " ")
    normalized = re.sub(r"\b(text|graphic|letters|lettering|typography|layout)\b", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"[^a-zA-Z0-9 ]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return None
    return " ".join(normalized.split()[:3]).title()


def _number_to_edition_word(value: int) -> str:
    words = {
        0: "Zero",
        1: "One",
        2: "Two",
        3: "Three",
        4: "Four",
        5: "Five",
        6: "Six",
        7: "Seven",
        8: "Eight",
        9: "Nine",
        10: "Ten",
        11: "Eleven",
        12: "Twelve",
        13: "Thirteen",
        14: "Fourteen",
        15: "Fifteen",
        16: "Sixteen",
        17: "Seventeen",
        18: "Eighteen",
        19: "Nineteen",
        20: "Twenty",
    }
    return words.get(value, str(value))


def _display_name_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    base_stem = re.sub(r"_\d+$", "", stem)
    base_name = base_stem.replace("_", " ").title()

    matches = list(APPROVED_DIR.glob(f"{base_stem}_*.png"))
    if len(matches) <= 1:
        return base_name

    metadata = _load_design_metadata_index().get(Path(filename).name, {})
    variant_label = _variant_label_from_palette(metadata.get("color_palette"))
    if not variant_label:
        variant_label = _variant_label_from_style(metadata.get("style"))
    if not variant_label:
        suffix_match = re.search(r"_(\d+)$", stem)
        if suffix_match:
            variant_label = f"Edition {_number_to_edition_word(int(suffix_match.group(1)))}"

    return f"{base_name} {variant_label}" if variant_label else base_name


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_paths = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for fp in font_paths:
        if Path(fp).exists():
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()


def _get_font_regular(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for fp in font_paths:
        if Path(fp).exists():
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.Draw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


def _load_templates() -> list[dict]:
    if TEMPLATES_FILE.exists():
        return json.loads(TEMPLATES_FILE.read_text(encoding="utf-8"))
    return []


def _load_app_templates() -> list[dict]:
    if APP_TEMPLATES_FILE.exists():
        return json.loads(APP_TEMPLATES_FILE.read_text(encoding="utf-8"))
    return []


def _resolve_board(template: dict) -> str | None:
    env_key = template.get("board_env_key", "")
    return os.environ.get(env_key) or None


def build_pin_title(design_title: str | None, primary_keyword: str) -> str:
    base = design_title or primary_keyword
    title = f"{base} | {primary_keyword}" if design_title else primary_keyword
    return title[:100]


def build_pin_description(
    design_concept: str | None,
    keywords: list[str],
    cta: str,
) -> str:
    parts: list[str] = []
    if design_concept:
        parts.append(design_concept)
    parts.append(cta)
    hashtags = " ".join(f"#{kw.replace(' ', '')}" for kw in keywords[:8])
    parts.append(hashtags)
    desc = " | ".join(parts)
    return desc[:500]


def build_pin_image(
    design_filename: str,
    template: dict,
    headline: str | None = None,
    cta: str | None = None,
) -> Path:
    from .pin_layouts import build_layout

    PINS_DIR.mkdir(parents=True, exist_ok=True)
    pin_id = uuid.uuid4().hex
    output_path = PINS_DIR / f"{pin_id}.png"

    # Prepare template overrides
    tmpl = {**template}
    if headline:
        tmpl["headline_placeholder"] = headline
    if cta:
        tmpl["cta"] = cta

    layout_name = tmpl.get("layout", "card_dark")
    design_path = APPROVED_DIR / design_filename

    # Find mockup directory for tshirt_photo layout
    mockup_dir = None
    if layout_name == "tshirt_photo":
        design_stem = Path(design_filename).stem
        possible = WORKSPACE_DIR / "mockup_output" / design_stem
        if possible.exists():
            mockup_dir = possible

    canvas = build_layout(layout_name, design_path, tmpl, mockup_dir=mockup_dir)
    canvas.save(output_path, "PNG", quality=95)
    return output_path


def generate_pins_for_design(
    design_filename: str,
    template_ids: list[str] | None = None,
) -> list[PinResponse]:
    templates = _load_templates()
    if template_ids:
        templates = [t for t in templates if t["id"] in template_ids]

    if not templates:
        templates = _load_templates()

    results: list[PinResponse] = []
    conn = get_conn()

    for tmpl in templates:
        keywords = select_keywords(tmpl.get("keyword_categories", []), count=5)
        primary_kw = keywords[0] if keywords else "sneaker culture"

        design_name = _display_name_from_filename(design_filename)
        title = build_pin_title(design_name, primary_kw)
        description = build_pin_description(design_name, keywords, tmpl.get("cta", "Shop now"))

        image_path = build_pin_image(
            design_filename,
            tmpl,
            headline=tmpl.get("headline_placeholder"),
            cta=tmpl.get("cta"),
        )

        pin_id = uuid.uuid4().hex
        now = datetime.now().isoformat(timespec="seconds")
        board_id = _resolve_board(tmpl)
        keywords_str = ",".join(keywords)

        conn.execute(
            """INSERT INTO pins (id, design_filename, template_id, pin_type, title,
               description, board_id, image_path, status, link, keywords, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (pin_id, design_filename, tmpl["id"], tmpl["pin_type"], title,
             description, board_id, str(image_path), PinStatus.DRAFT.value,
             None, keywords_str, now),
        )

        results.append(PinResponse(
            id=pin_id,
            design_filename=design_filename,
            template_id=tmpl["id"],
            pin_type=tmpl["pin_type"],
            title=title,
            description=description,
            board_id=board_id,
            image_path=str(image_path),
            status=PinStatus.DRAFT.value,
            link=None,
            keywords=keywords_str,
            created_at=now,
        ))

    conn.commit()
    conn.close()
    return results


def generate_app_promo_pins(count: int = 30) -> list[PinResponse]:
    app_templates = _load_app_templates()
    if not app_templates:
        return []

    from .app_phase import get_current_phase
    phase = get_current_phase()

    results: list[PinResponse] = []
    conn = get_conn()

    # Get a design to use as background imagery
    from .spreadsheet_reader import get_approved_designs
    designs = get_approved_designs()

    pins_per_template = max(1, count // len(app_templates))
    generated = 0

    for tmpl in app_templates:
        phase_data = tmpl.get(phase.value, tmpl.get("pre_launch", {}))
        for i in range(pins_per_template):
            if generated >= count:
                break

            design_fn = designs[generated % len(designs)].filename if designs else ""
            keywords = select_keywords(tmpl.get("keyword_categories", []), count=5)
            primary_kw = keywords[0] if keywords else "sneaker culture"

            title = phase_data.get("title", build_pin_title(None, primary_kw))
            cta = phase_data.get("cta", "Learn more")
            description = phase_data.get("description", "")
            if keywords:
                hashtags = " ".join(f"#{kw.replace(' ', '')}" for kw in keywords[:5])
                description = f"{description} {hashtags}"[:500]

            if design_fn:
                image_path = build_pin_image(design_fn, tmpl, headline=tmpl.get("headline_placeholder"), cta=cta)
            else:
                PINS_DIR.mkdir(parents=True, exist_ok=True)
                image_path = PINS_DIR / f"{uuid.uuid4().hex}.png"
                canvas = Image.new("RGB", (WIDTH, HEIGHT), _hex_to_rgb(tmpl.get("background", BLACK)))
                canvas.save(image_path, "PNG")

            pin_id = uuid.uuid4().hex
            now = datetime.now().isoformat(timespec="seconds")
            keywords_str = ",".join(keywords)

            conn.execute(
                """INSERT INTO pins (id, design_filename, template_id, pin_type, title,
                   description, board_id, image_path, status, link, keywords, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (pin_id, design_fn, tmpl["id"], PinType.APP_PROMO.value, title,
                 description, _resolve_board(tmpl), str(image_path),
                 PinStatus.DRAFT.value, None, keywords_str, now),
            )

            results.append(PinResponse(
                id=pin_id,
                design_filename=design_fn,
                template_id=tmpl["id"],
                pin_type=PinType.APP_PROMO.value,
                title=title,
                description=description,
                board_id=_resolve_board(tmpl),
                image_path=str(image_path),
                status=PinStatus.DRAFT.value,
                keywords=keywords_str,
                created_at=now,
            ))
            generated += 1

    conn.commit()
    conn.close()
    return results
