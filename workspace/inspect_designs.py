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
from PIL import Image, ImageStat, ImageDraw, ImageFont

# ── Quality thresholds (match Printify requirements) ──────────────
MIN_WIDTH = 3600
MIN_HEIGHT = 4800
MIN_CONTRAST = 35       # avg channel stddev — below this the design is too flat
TARGET_DPI = 300


def inspect_design(filepath):
    """
    Validate a single PNG for print readiness.
    Returns dict with pass/fail, size, contrast, and any issues found.
    """
    issues = []
    img = Image.open(filepath).convert("RGB")
    w, h = img.size

    if w < MIN_WIDTH or h < MIN_HEIGHT:
        issues.append(f"Too small: {w}x{h}px (need {MIN_WIDTH}x{MIN_HEIGHT})")

    stat = ImageStat.Stat(img)
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


def add_text_overlay(base_image_path, phrase, output_path,
                     font_path=None, font_size=None,
                     text_color=None):
    """
    Composite a phrase over an AI-generated base image.
    Resizes to print resolution, auto-sizes text to fill the design area,
    adds a dark drop shadow for contrast on any background.
    """
    img = Image.open(base_image_path).convert("RGBA")
    img = img.resize((MIN_WIDTH, MIN_HEIGHT), Image.LANCZOS)

    # Resolve font
    resolved_font = font_path or _find_default_font()

    # Auto-size: scale font to fill ~85% of image width
    max_text_width = int(MIN_WIDTH * 0.85)
    if font_size:
        size = font_size
    else:
        # Start large and shrink until text fits — streetwear = bold and big
        size = 600
        while size > 40:
            test_font = ImageFont.truetype(resolved_font, size) if resolved_font else ImageFont.load_default(size=size)
            test_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
            bbox = test_draw.textbbox((0, 0), phrase, font=test_font)
            if (bbox[2] - bbox[0]) <= max_text_width:
                break
            size -= 10

    if resolved_font:
        font = ImageFont.truetype(resolved_font, size)
    else:
        font = ImageFont.load_default(size=size)

    # Calculate centered position
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), phrase, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (MIN_WIDTH - text_w) // 2
    y = (MIN_HEIGHT - text_h) // 2

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
    shadow_offset = max(3, size // 50)
    draw.text((x + shadow_offset, y + shadow_offset), phrase,
              font=font, fill=shadow_color)

    # Main text
    draw.text((x, y), phrase, font=font, fill=text_color)

    img.save(output_path, "PNG", dpi=(TARGET_DPI, TARGET_DPI))
    print(f"  Text overlay saved: {output_path}")


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

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
