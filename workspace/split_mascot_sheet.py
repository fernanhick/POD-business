#!/usr/bin/env python3
"""Split a mascot expression sheet into individual transparent PNGs.

Takes the 4x3 character sheet, crops each expression, removes the
magenta background, trims transparent edges, and saves as individual files.
"""

import os
import sys
import numpy as np
from PIL import Image

# ── Config ────────────────────────────────────────────────────────
INPUT_PATH = sys.argv[1] if len(sys.argv) > 1 else (
    os.path.join(os.path.dirname(__file__),
                 "branding", "mascot", "chimp_expression_sheet.png")
)
OUTPUT_DIR = os.path.join(os.path.dirname(INPUT_PATH), "expressions")

# Grid layout: 4 columns x 3 rows
COLS, ROWS = 4, 3
LABELS = [
    "stern",     "happy",     "surprised",    "laughing",
    "annoyed",   "thinking",  "wink",         "nervous",
    "huh",       "sleepy",    "shocked_gasp", "calm",
]


def remove_chroma_bg(img, tolerance=80):
    """Remove magenta chroma-key background from an RGBA image."""
    arr = np.array(img)
    # Target: magenta (#FF00FF) and nearby shades
    color_dist = (
        (arr[:, :, 0].astype(int) - 255) ** 2
        + (arr[:, :, 1].astype(int) - 0) ** 2
        + (arr[:, :, 2].astype(int) - 255) ** 2
    )
    bg_mask = color_dist < (tolerance * tolerance * 3)
    arr[bg_mask, 3] = 0

    removed_pct = bg_mask.sum() / (img.width * img.height) * 100
    return Image.fromarray(arr), removed_pct


def trim_transparent(img, padding=4):
    """Trim transparent edges and add optional padding."""
    arr = np.array(img)
    alpha = arr[:, :, 3]
    rows_with_content = np.any(alpha > 0, axis=1)
    cols_with_content = np.any(alpha > 0, axis=0)

    if not rows_with_content.any():
        return img

    top = np.argmax(rows_with_content)
    bottom = len(rows_with_content) - np.argmax(rows_with_content[::-1])
    left = np.argmax(cols_with_content)
    right = len(cols_with_content) - np.argmax(cols_with_content[::-1])

    # Add padding
    top = max(0, top - padding)
    bottom = min(img.height, bottom + padding)
    left = max(0, left - padding)
    right = min(img.width, right + padding)

    return img.crop((left, top, right, bottom))


def main():
    print(f"Loading: {INPUT_PATH}")
    sheet = Image.open(INPUT_PATH).convert("RGBA")
    w, h = sheet.size
    print(f"  Sheet size: {w}x{h}")

    cell_w = w // COLS
    cell_h = h // ROWS
    print(f"  Cell size: {cell_w}x{cell_h}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for row in range(ROWS):
        for col in range(COLS):
            idx = row * COLS + col
            label = LABELS[idx]

            # Crop this cell, trimming bottom ~12% to exclude text labels
            x0 = col * cell_w
            y0 = row * cell_h
            x1 = x0 + cell_w
            y1 = y0 + int(cell_h * 0.88)
            cell = sheet.crop((x0, y0, x1, y1))

            # Remove magenta background
            cell, pct = remove_chroma_bg(cell)

            # Trim transparent edges
            cell = trim_transparent(cell)

            # Save
            out_path = os.path.join(OUTPUT_DIR, f"mascot_{label}.png")
            cell.save(out_path, "PNG")
            print(f"  [{idx+1:2d}/12] {label:15s} -> {cell.width}x{cell.height}  "
                  f"({pct:.0f}% bg removed)")

    print(f"\nDone! {len(LABELS)} expressions saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
