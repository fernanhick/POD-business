"""
inspect_designs.py  --  Design Quality Gate

Validates PNGs for print-readiness: resolution, contrast, and DPI.
Optionally moves passing/failing designs into approved/rejected folders.
Also provides text overlay compositing for fully automated batches.

Usage:
    python inspect_designs.py --folder front_a_sneaker/designs
    python inspect_designs.py --folder front_b_general/designs --move
    python inspect_designs.py --file path/to/design.png
    python inspect_designs.py --overlay input.png "PHRASE HERE" output.png --font path/to/font.ttf
"""

import os
import sys
import json
import shutil
import argparse
from PIL import Image, ImageStat, ImageDraw, ImageFont, ImageChops

# ── Quality thresholds (match Printify requirements) ──────────────
MIN_WIDTH = 3600
MIN_HEIGHT = 4800
MIN_CONTRAST = 35       # avg channel stddev — below this the design is too flat
TARGET_DPI = 300
DEFAULT_MIN_PHRASE_VISIBILITY = 0.90


def inspect_design(filepath):
    """
    Validate a single PNG for print readiness.
    Returns dict with pass/fail, size, contrast, and any issues found.
    """
    issues = []
    img = Image.open(filepath)
    w, h = img.size

    if w < MIN_WIDTH or h < MIN_HEIGHT:
        issues.append(f"Too small: {w}x{h}px (need {MIN_WIDTH}x{MIN_HEIGHT})")

    # For RGBA images, use the alpha channel as mask so transparent
    # pixels (removed background) don't skew the contrast stats.
    rgb = img.convert("RGB")
    if img.mode == "RGBA":
        alpha = img.split()[3]
        mask = alpha.point(lambda a: 255 if a > 128 else 0)
        stat = ImageStat.Stat(rgb, mask=mask)
    else:
        stat = ImageStat.Stat(rgb)

    avg_std = sum(stat.stddev) / len(stat.stddev)
    if avg_std < MIN_CONTRAST:
        issues.append(f"Low contrast: stddev={avg_std:.1f} (need {MIN_CONTRAST})")

    # Check if image is essentially blank (all white or all black)
    avg_mean = sum(stat.mean) / len(stat.mean)
    if avg_mean > 250:
        issues.append("Nearly blank (all white)")
    elif avg_mean < 5:
        issues.append("Nearly blank (all black)")

    return {
        "file": os.path.basename(filepath),
        "path": filepath,
        "ok": len(issues) == 0,
        "issues": issues,
        "size": f"{w}x{h}",
        "width": w,
        "height": h,
        "contrast": round(avg_std, 1),
    }


def batch_inspect(folder, move=False):
    """
    Inspect all PNGs in a folder.
    If move=True, passing designs go to ../approved/, failing to ../rejected/.
    Returns list of result dicts.
    """
    if not os.path.isdir(folder):
        print(f"  Folder not found: {folder}")
        sys.exit(1)

    files = sorted(f for f in os.listdir(folder) if f.lower().endswith(".png"))
    if not files:
        print(f"  No PNG files found in {folder}")
        return []

    print(f"  Inspecting {len(files)} designs in {folder}/\n")
    results = []

    for fname in files:
        filepath = os.path.join(folder, fname)
        result = inspect_design(filepath)
        results.append(result)

        icon = "PASS" if result["ok"] else "FAIL"
        detail = ", ".join(result["issues"]) or f'{result["size"]} contrast={result["contrast"]}'
        print(f"  [{icon}] {result['file']}: {detail}")

        if move:
            parent = os.path.dirname(os.path.abspath(folder))
            dest_dir = os.path.join(parent, "approved" if result["ok"] else "rejected")
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, fname)
            shutil.move(filepath, dest_path)
            print(f"         -> moved to {os.path.basename(dest_dir)}/")

    passed = sum(1 for r in results if r["ok"])
    failed = len(results) - passed
    print(f"\n  Results: {passed} passed, {failed} failed out of {len(results)} designs")
    return results


def upscale_if_needed(filepath, output_path=None):
    """
    Upscale a design to minimum print resolution if it's too small.
    Uses LANCZOS resampling. For best results, use Real-ESRGAN before this.
    """
    img = Image.open(filepath)
    w, h = img.size

    if w >= MIN_WIDTH and h >= MIN_HEIGHT:
        print(f"  Already adequate: {w}x{h}")
        return filepath

    # Scale up proportionally to meet minimums
    scale = max(MIN_WIDTH / w, MIN_HEIGHT / h)
    new_w = int(w * scale)
    new_h = int(h * scale)

    img = img.resize((new_w, new_h), Image.LANCZOS)
    out = output_path or filepath
    img.save(out, "PNG", dpi=(TARGET_DPI, TARGET_DPI))
    print(f"  Upscaled {w}x{h} -> {new_w}x{new_h}: {out}")
    return out


def _find_default_font():
    """Find a bold condensed system font suitable for streetwear text."""
    candidates = [
        "C:/Windows/Fonts/impact.ttf",     # Impact — bold condensed, ideal
        "C:/Windows/Fonts/arialbd.ttf",     # Arial Bold — fallback
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
        "/System/Library/Fonts/Helvetica.ttc",  # macOS
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _foreground_mask_for_overlap(img):
    """Return an L mask where 255 marks likely foreground graphics."""
    rgba = img.convert("RGBA")
    rgb = rgba.convert("RGB")
    r, g, b = rgb.split()

    # Most renders use bright magenta chroma background before removal.
    magenta_r = r.point(lambda v: 255 if v >= 220 else 0)
    magenta_g = g.point(lambda v: 255 if v <= 95 else 0)
    magenta_b = b.point(lambda v: 255 if v >= 220 else 0)
    magenta_mask = ImageChops.multiply(ImageChops.multiply(magenta_r, magenta_g), magenta_b)
    non_magenta = ImageChops.invert(magenta_mask)

    alpha = rgba.split()[3]
    solid_alpha = alpha.point(lambda v: 255 if v > 20 else 0)
    return ImageChops.multiply(non_magenta, solid_alpha)


def _bbox_overlap_ratio(mask_l, bbox):
    x1, y1, x2, y2 = bbox
    x1 = max(0, min(MIN_WIDTH - 1, x1))
    y1 = max(0, min(MIN_HEIGHT - 1, y1))
    x2 = max(x1 + 1, min(MIN_WIDTH, x2))
    y2 = max(y1 + 1, min(MIN_HEIGHT, y2))
    region = mask_l.crop((x1, y1, x2, y2))
    stat = ImageStat.Stat(region)
    return max(0.0, min(1.0, (stat.mean[0] / 255.0) if stat.mean else 0.0))


def _candidate_positions(text_w, text_h):
    margin_x = int(MIN_WIDTH * 0.06)
    top_band = (int(MIN_HEIGHT * 0.05), int(MIN_HEIGHT * 0.32))
    bottom_band = (int(MIN_HEIGHT * 0.68), int(MIN_HEIGHT * 0.95))

    x = max(margin_x, min(MIN_WIDTH - text_w - margin_x, (MIN_WIDTH - text_w) // 2))

    top_y = max(top_band[0], min(top_band[1] - text_h, (top_band[0] + top_band[1] - text_h) // 2))
    bottom_y = max(bottom_band[0], min(bottom_band[1] - text_h, (bottom_band[0] + bottom_band[1] - text_h) // 2))

    return [
        ("top", x, top_y),
        ("bottom", x, bottom_y),
    ]


def add_text_overlay(base_image_path, phrase, output_path,
                     font_path=None, font_size=None,
                     text_color=None,
                     min_visibility=DEFAULT_MIN_PHRASE_VISIBILITY,
                     layout_mode="safe_zone"):
    """
    Composite a phrase over an AI-generated base image.
    Resizes to print resolution, auto-sizes text to fill the design area,
    adds a dark drop shadow for contrast on any background.
    """
    img = Image.open(base_image_path).convert("RGBA")
    img = img.resize((MIN_WIDTH, MIN_HEIGHT), Image.LANCZOS)

    # Resolve font
    resolved_font = font_path or _find_default_font()

    # Auto-size and placement: prefer safe top/bottom bands with minimal overlap.
    max_text_width = int(MIN_WIDTH * 0.88)
    start_size = font_size if font_size else 600
    draw = ImageDraw.Draw(img)
    fg_mask = _foreground_mask_for_overlap(img)

    best = None
    for size in range(start_size, 39, -10):
        test_font = ImageFont.truetype(resolved_font, size) if resolved_font else ImageFont.load_default(size=size)
        bbox = draw.textbbox((0, 0), phrase, font=test_font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        if text_w > max_text_width:
            continue

        if layout_mode == "safe_zone":
            candidates = _candidate_positions(text_w, text_h)
        else:
            candidates = [
                ("center", (MIN_WIDTH - text_w) // 2, (MIN_HEIGHT - text_h) // 2),
            ]

        local_best = None
        for zone, x, y in candidates:
            text_bbox = (x, y, x + text_w, y + text_h)
            overlap = _bbox_overlap_ratio(fg_mask, text_bbox)
            visibility = 1.0 - overlap
            candidate = {
                "font": test_font,
                "size": size,
                "x": x,
                "y": y,
                "text_w": text_w,
                "text_h": text_h,
                "zone": zone,
                "overlap": overlap,
                "visibility": visibility,
            }
            if local_best is None or candidate["visibility"] > local_best["visibility"]:
                local_best = candidate

        if local_best is None:
            continue

        if best is None or local_best["visibility"] > best["visibility"]:
            best = local_best

        if local_best["visibility"] >= min_visibility:
            best = local_best
            break

    if best is None:
        # Fallback: original centered placement if everything else failed
        fallback_size = max(40, min(start_size, 220))
        font = ImageFont.truetype(resolved_font, fallback_size) if resolved_font else ImageFont.load_default(size=fallback_size)
        bbox = draw.textbbox((0, 0), phrase, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        best = {
            "font": font,
            "size": fallback_size,
            "x": (MIN_WIDTH - text_w) // 2,
            "y": (MIN_HEIGHT - text_h) // 2,
            "text_w": text_w,
            "text_h": text_h,
            "zone": "center",
            "visibility": 0.0,
            "overlap": 1.0,
        }

    font = best["font"]
    x = best["x"]
    y = best["y"]
    text_w = best["text_w"]
    text_h = best["text_h"]

    # Auto-detect text color: sample background brightness at text center
    if text_color is None:
        sample_region = img.crop((
            max(0, x), max(0, y),
            min(MIN_WIDTH, x + text_w), min(MIN_HEIGHT, y + text_h)
        )).convert("RGB")
        avg_brightness = sum(ImageStat.Stat(sample_region).mean) / 3
        # Light background -> dark text; dark background -> light text
        text_color = (255, 255, 255) if avg_brightness < 128 else (20, 20, 20)

    # Shadow for contrast (offset 4px down-right)
    shadow_color = (0, 0, 0, 180) if text_color[0] > 128 else (255, 255, 255, 120)
    shadow_offset = max(3, best["size"] // 50)
    draw.text((x + shadow_offset, y + shadow_offset), phrase,
              font=font, fill=shadow_color)

    # Main text
    draw.text((x, y), phrase, font=font, fill=text_color)

    img.save(output_path, "PNG", dpi=(TARGET_DPI, TARGET_DPI))
    print(
        f"  Text overlay saved: {output_path} "
        f"(zone={best['zone']}, visibility={best['visibility']:.2f})"
    )
    return {
        "zone": best["zone"],
        "visibility": best["visibility"],
        "font_size": best["size"],
        "overlap": best["overlap"],
    }


def trim_and_fill(filepath, target_w=4500, target_h=5400, padding_pct=0.05):
    """
    Trim transparent edges from a PNG and resize the content to fill
    the target canvas, preserving aspect ratio. Centers on a transparent canvas.
    """
    img = Image.open(filepath).convert("RGBA")
    bbox = img.getbbox()
    if bbox is None:
        print(f"  [SKIP] Fully transparent: {os.path.basename(filepath)}")
        return filepath

    cropped = img.crop(bbox)
    cw, ch = cropped.size

    pad_x = int(target_w * padding_pct)
    pad_y = int(target_h * padding_pct)
    avail_w = target_w - 2 * pad_x
    avail_h = target_h - 2 * pad_y

    scale = min(avail_w / cw, avail_h / ch)
    new_w = int(cw * scale)
    new_h = int(ch * scale)

    resized = cropped.resize((new_w, new_h), Image.LANCZOS)

    canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    paste_x = (target_w - new_w) // 2
    paste_y = (target_h - new_h) // 2
    canvas.paste(resized, (paste_x, paste_y))

    canvas.save(filepath, "PNG")
    print(f"  [TRIM] {cw}x{ch} -> {new_w}x{new_h} on {target_w}x{target_h} canvas: {os.path.basename(filepath)}")
    return filepath


def main():
    parser = argparse.ArgumentParser(
        description="Design quality gate — validate PNGs for print readiness"
    )
    sub = parser.add_subparsers(dest="command")

    # ── inspect command ──
    insp = sub.add_parser("inspect", help="Inspect designs for quality")
    insp.add_argument("--folder", help="Folder of PNGs to inspect")
    insp.add_argument("--file", help="Single PNG to inspect")
    insp.add_argument("--move", action="store_true",
                      help="Move passing to approved/, failing to rejected/")
    insp.add_argument("--json", dest="json_out",
                      help="Write results to JSON file")

    # ── overlay command ──
    ovr = sub.add_parser("overlay", help="Add text overlay to a design")
    ovr.add_argument("input", help="Input PNG path")
    ovr.add_argument("phrase", help="Text phrase to overlay")
    ovr.add_argument("output", help="Output PNG path")
    ovr.add_argument("--font", help="Path to .ttf font file")
    ovr.add_argument("--font-size", type=int, default=180)
    ovr.add_argument("--color", default="30,30,30",
                     help="Text color as R,G,B (default: 30,30,30)")

    # ── upscale command ──
    usc = sub.add_parser("upscale", help="Upscale undersized designs")
    usc.add_argument("input", help="Input PNG or folder")
    usc.add_argument("--output", help="Output path (default: overwrite)")

    # ── trim command ──
    trm = sub.add_parser("trim", help="Trim transparent edges and fill print area")
    trm.add_argument("--input", required=True, help="Input PNG file")
    trm.add_argument("--width", type=int, default=4500, help="Target width (default: 4500)")
    trm.add_argument("--height", type=int, default=5400, help="Target height (default: 5400)")
    trm.add_argument("--padding", type=float, default=0.05, help="Padding as fraction (default: 0.05)")

    args = parser.parse_args()

    if args.command == "inspect":
        if args.file:
            result = inspect_design(args.file)
            icon = "PASS" if result["ok"] else "FAIL"
            print(f"  [{icon}] {result['file']}: "
                  f"{', '.join(result['issues']) or 'OK'}")
        elif args.folder:
            results = batch_inspect(args.folder, move=args.move)
            if args.json_out:
                with open(args.json_out, "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=2)
                print(f"  Results written to {args.json_out}")
        else:
            insp.print_help()

    elif args.command == "overlay":
        color = tuple(int(c) for c in args.color.split(","))
        add_text_overlay(args.input, args.phrase, args.output,
                         font_path=args.font, font_size=args.font_size,
                         text_color=color)

    elif args.command == "upscale":
        if os.path.isdir(args.input):
            for f in sorted(os.listdir(args.input)):
                if f.lower().endswith(".png"):
                    upscale_if_needed(os.path.join(args.input, f))
        else:
            upscale_if_needed(args.input, args.output)

    elif args.command == "trim":
        trim_and_fill(args.input, args.width, args.height, args.padding)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
