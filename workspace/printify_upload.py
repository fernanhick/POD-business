"""
printify_upload.py  --  Bulk Upload to Printify & Publish to Etsy

Uploads approved PNGs to Printify, creates products, and optionally
publishes them to your connected Etsy store. Writes back Printify
product IDs and image IDs to the design tracker spreadsheets.

Usage:
    python printify_upload.py --front A
    python printify_upload.py --front B
    python printify_upload.py --front A --draft          # upload but don't publish (for drops)
    python printify_upload.py --front A --dry-run        # preview what would be uploaded
    python printify_upload.py sync-ids --front A         # poll Printify for Etsy listing IDs

Setup:
    1. Get your Printify API token: Settings > Connections > Personal Access Token
    2. Get your shop ID from the Printify dashboard URL: /shop/{SHOP_ID}/
    3. Set environment variables or edit the config below:
       export PRINTIFY_TOKEN="your_token_here"
       export PRINTIFY_SHOP_ID="your_shop_id_here"
"""

import base64
import os
import sys
import time
import json
import argparse
import requests
from openpyxl import load_workbook
from dotenv import load_dotenv

# ── Load .env from workspace root ─────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# ── Configuration ─────────────────────────────────────────────────
TOKEN   = os.environ.get("PRINTIFY_TOKEN", "")
SHOP_ID = os.environ.get("PRINTIFY_SHOP_ID", "")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
BASE    = "https://api.printify.com/v1"

WORKSPACE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.join(WORKSPACE, "spreadsheets")

# ── Per-front product configuration ──────────────────────────────
# Update blueprint_id, provider_id, variant_ids after querying the
# Printify catalog API (see docs at bottom of this file).
FRONT_CONFIG = {
    "A": {
        "designs_dir":  os.path.join(WORKSPACE, "front_a_sneaker", "approved"),
        "spreadsheet":  os.path.join(SP, "designs_front_a.xlsx"),
        "sheet_name":   "Designs",
        "blueprint_id": 145,     # Unisex Heavy Blend Hoodie (Gildan 18500)
        "provider_id":  99,      # Monster Digital
        "variants": [
            # Black: S–5XL
            {"id": 38164, "size": "S"},
            {"id": 38178, "size": "M"},
            {"id": 38192, "size": "L"},
            {"id": 38206, "size": "XL"},
            {"id": 38220, "size": "2XL"},
            {"id": 42122, "size": "3XL"},
            {"id": 66213, "size": "4XL"},
            {"id": 95180, "size": "5XL"},
            # White: S–5XL
            {"id": 38163, "size": "S"},
            {"id": 38177, "size": "M"},
            {"id": 38191, "size": "L"},
            {"id": 38205, "size": "XL"},
            {"id": 38219, "size": "2XL"},
            {"id": 42120, "size": "3XL"},
            {"id": 66211, "size": "4XL"},
            {"id": 95175, "size": "5XL"},
        ],
        "base_cost_cents": 988,       # S–XL cost from Printify
        "oversize_costs": {            # cost for larger sizes
            "2XL": 1129, "3XL": 1248, "4XL": 1382, "5XL": 1502,
        },
        "shipping_cents": 399,         # US first-item shipping
        "tags": [
            "sneakerhead shirt", "sneaker collector tee", "streetwear graphic tee",
            "sneaker culture", "hypebeast clothing", "rotation tee",
            "sneaker lover gift", "kicks shirt", "sneakerhead gift",
            "streetwear hoodie", "sneaker hoodie", "urban streetwear",
            "sneaker graphic",
        ],
        "title_template": (
            "{name} | Sneakerhead Tee | Sneaker Collector Shirt "
            "| Streetwear Graphic Tee | Gift for Sneaker Lover"
        ),
        "description_template": (
            "This sneakerhead graphic celebrates sneaker culture and collector "
            "life. Designed for the daily rotation and the deadstock shelf "
            "alike.\n\n"
            "* Oversized streetwear fit -- size up for drop-shoulder silhouette\n"
            "* Premium heavyweight cotton\n"
            "* DTG printed, wash-resistant\n\n"
            "Perfect gift for sneakerheads, sneaker collectors, "
            "and streetwear fans."
        ),
    },
    "B": {
        "designs_dir":  os.path.join(WORKSPACE, "front_b_general", "approved"),
        "spreadsheet":  os.path.join(SP, "designs_front_b.xlsx"),
        "sheet_name":   "Designs",
        "blueprint_id": 5,       # Unisex Softstyle T-Shirt (Gildan 64000)
        "provider_id":  99,
        "variants": [
            # Solid Black: S–5XL
            {"id": 17427, "size": "S"},
            {"id": 17428, "size": "M"},
            {"id": 17429, "size": "L"},
            {"id": 17430, "size": "XL"},
            {"id": 17431, "size": "2XL"},
            {"id": 17432, "size": "3XL"},
            {"id": 17433, "size": "4XL"},
            {"id": 101781, "size": "5XL"},
            # Solid White: S–5XL
            {"id": 17643, "size": "S"},
            {"id": 17644, "size": "M"},
            {"id": 17645, "size": "L"},
            {"id": 17646, "size": "XL"},
            {"id": 17647, "size": "2XL"},
            {"id": 17648, "size": "3XL"},
            {"id": 17649, "size": "4XL"},
            {"id": 101810, "size": "5XL"},
        ],
        "base_cost_cents": 1163,      # S–XL cost from Printify
        "oversize_costs": {
            "2XL": 1409, "3XL": 1613, "4XL": 1796, "5XL": 1930,
        },
        "shipping_cents": 399,         # US first-item shipping
        "tags": [
            "graphic tee", "unique gift shirt", "funny tee", "quote shirt",
            "trendy tee", "minimalist graphic", "gift for him", "gift for her",
            "unisex tee", "casual shirt", "everyday tee", "cool graphic tee",
            "statement tee",
        ],
        "title_template": "{name} | Graphic Tee | Unique Gift",
        "description_template": (
            "A unique graphic tee perfect as a gift or for everyday wear.\n\n"
            "* Soft, lightweight cotton\n"
            "* DTG printed, wash-resistant\n"
            "* Available in multiple sizes and colors"
        ),
    },
}


def check_config():
    if not TOKEN:
        print("  Error: PRINTIFY_TOKEN not set.")
        print("  Set it via: export PRINTIFY_TOKEN='your_token_here'")
        print("  Or edit the TOKEN variable at the top of this script.")
        sys.exit(1)
    if not SHOP_ID:
        print("  Error: PRINTIFY_SHOP_ID not set.")
        print("  Set it via: export PRINTIFY_SHOP_ID='your_shop_id_here'")
        sys.exit(1)


def upload_image(filepath):
    """Upload a design PNG to Printify via base64 JSON. Returns the image ID."""
    with open(filepath, "rb") as f:
        contents = base64.b64encode(f.read()).decode("utf-8")
    resp = requests.post(
        f"{BASE}/uploads/images.json",
        headers={**HEADERS, "Content-Type": "application/json"},
        json={"file_name": os.path.basename(filepath), "contents": contents},
    )
    resp.raise_for_status()
    return resp.json()["id"]


def calc_price(cost_cents, shipping_cents):
    """40% profit margin including shipping: price = (cost + ship) / 0.60, rounded to .99"""
    raw = (cost_cents + shipping_cents) / 0.60
    dollars = int(raw / 100) + 1  # round up to next dollar
    return dollars * 100 - 1      # e.g. $23.99 = 2399


def create_product(image_id, title, description, cfg, design_name=None):
    """Create a product on Printify with the uploaded image. Returns product ID."""
    # Build tags: base tags + dynamic from design name, capped at 13 (Etsy max)
    base_tags = list(cfg.get("tags", []))
    if design_name:
        name_lower = design_name.lower().strip()
        dynamic = [name_lower]
        first_word = name_lower.split()[0] if name_lower.split() else None
        if first_word:
            dynamic.append(f"{first_word} tee")
        for tag in dynamic:
            if tag not in base_tags:
                base_tags.append(tag)
    tags = base_tags[:13]

    # Build variants with calculated per-size pricing
    base_cost = cfg["base_cost_cents"]
    shipping = cfg["shipping_cents"]
    oversize = cfg.get("oversize_costs", {})

    variants = []
    variant_ids = []
    for v in cfg["variants"]:
        cost = oversize.get(v["size"], base_cost)
        price = calc_price(cost, shipping)
        variants.append({"id": v["id"], "price": price, "is_enabled": True})
        variant_ids.append(v["id"])

    payload = {
        "title": title,
        "description": description,
        "tags": tags,
        "blueprint_id": cfg["blueprint_id"],
        "print_provider_id": cfg["provider_id"],
        "variants": variants,
        "print_areas": [{
            "variant_ids": variant_ids,
            "placeholders": [{
                "position": "front",
                "images": [{
                    "id": image_id,
                    "x": 0.5, "y": 0.5,
                    "scale": 1.0, "angle": 0,
                }],
            }],
        }],
    }
    resp = requests.post(
        f"{BASE}/shops/{SHOP_ID}/products.json",
        headers={**HEADERS, "Content-Type": "application/json"},
        json=payload,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def publish_product(product_id):
    """Publish a Printify product to the connected Etsy store."""
    resp = requests.post(
        f"{BASE}/shops/{SHOP_ID}/products/{product_id}/publish.json",
        headers={**HEADERS, "Content-Type": "application/json"},
        json={
            "title": True, "description": True, "images": True,
            "variants": True, "tags": True, "keyFeatures": True,
            "shipping_template": True,
        },
    )
    resp.raise_for_status()


def get_product(product_id):
    """Fetch product details from Printify (used to get Etsy listing ID)."""
    resp = requests.get(
        f"{BASE}/shops/{SHOP_ID}/products/{product_id}.json",
        headers=HEADERS,
    )
    resp.raise_for_status()
    return resp.json()


def update_spreadsheet_ids(spreadsheet_path, sheet_name, filename,
                           image_id=None, product_id=None, etsy_id=None,
                           status=None):
    """
    Find a design row by filename and update its Printify/Etsy IDs.
    Columns searched: B (Filename), columns updated vary by front.
    """
    wb = load_workbook(spreadsheet_path)
    ws = wb[sheet_name]

    # Find the filename column (B=2) and ID columns
    # Front A: O=Printify Image ID, P=Printify Product ID, Q=Etsy Listing ID, R=Status
    # Front B: M=Printify Image ID, N=Printify Product ID, O=Etsy Listing ID, P=Status
    header_row = 2  # row 1 is the title banner
    headers = {ws.cell(row=header_row, column=c).value: c
               for c in range(1, ws.max_column + 1)}

    filename_col = headers.get("Filename", 2)
    img_col = headers.get("Printify Image ID")
    prod_col = headers.get("Printify Product ID")
    etsy_col = headers.get("Etsy Listing ID")
    status_col = headers.get("Status")

    updated = False
    for row in range(3, ws.max_row + 1):
        cell_val = ws.cell(row=row, column=filename_col).value
        if cell_val and cell_val.strip() == filename.strip():
            if image_id and img_col:
                ws.cell(row=row, column=img_col, value=image_id)
            if product_id and prod_col:
                ws.cell(row=row, column=prod_col, value=product_id)
            if etsy_id and etsy_col:
                ws.cell(row=row, column=etsy_col, value=etsy_id)
            if status and status_col:
                ws.cell(row=row, column=status_col, value=status)
            updated = True
            break

    if updated:
        wb.save(spreadsheet_path)
    else:
        print(f"    Warning: '{filename}' not found in spreadsheet")
    wb.close()
    return updated


def run_upload(front, draft=False, dry_run=False):
    """Main upload loop for a front."""
    cfg = FRONT_CONFIG[front]
    designs_dir = cfg["designs_dir"]

    if not os.path.isdir(designs_dir):
        print(f"  Designs folder not found: {designs_dir}")
        print(f"  Place approved PNGs there first.")
        sys.exit(1)

    files = sorted(f for f in os.listdir(designs_dir) if f.lower().endswith(".png"))
    if not files:
        print(f"  No PNG files in {designs_dir}")
        return

    action = "publish to Etsy" if not draft else "create as draft (no publish)"
    print(f"  Front {front}: {len(files)} designs to upload ({action})\n")

    results = []
    for filename in files:
        filepath = os.path.join(designs_dir, filename)
        base_name = os.path.splitext(filename)[0].replace("_", " ").title()
        title = cfg["title_template"].format(name=base_name)
        desc = cfg["description_template"]

        if dry_run:
            print(f"  [DRY] {filename} -> '{title[:60]}...'")
            continue

        try:
            # Step 1: Upload image
            image_id = upload_image(filepath)
            print(f"  [1/3] Uploaded image: {filename} (id={image_id})")

            # Step 2: Create product
            product_id = create_product(image_id, title, desc, cfg, design_name=base_name)
            print(f"  [2/3] Created product: {product_id}")

            # Step 3: Publish (unless draft mode for drops)
            if not draft:
                publish_product(product_id)
                print(f"  [3/3] Published to Etsy")
                status = "Published"
            else:
                print(f"  [3/3] Kept as draft (drop mode)")
                status = "Draft on Printify"

            # Step 4: Write IDs back to spreadsheet
            update_spreadsheet_ids(
                cfg["spreadsheet"], cfg["sheet_name"], filename,
                image_id=image_id, product_id=product_id, status=status,
            )

            results.append({
                "filename": filename, "image_id": image_id,
                "product_id": product_id, "status": status,
            })
            print(f"  [OK]  {title[:60]}...\n")

        except requests.HTTPError as e:
            print(f"  [ERR] {filename}: HTTP {e.response.status_code} "
                  f"-- {e.response.text[:200]}\n")
        except Exception as e:
            print(f"  [ERR] {filename}: {e}\n")

        time.sleep(1.5)  # ~40 uploads/min, well under Printify rate limit

    if not dry_run:
        # Save upload log
        log_path = os.path.join(WORKSPACE, "logs",
                                f"upload_{front}_{int(time.time())}.json")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"  Upload log: {log_path}")
        print(f"  Done: {len(results)}/{len(files)} uploaded successfully")


def sync_etsy_ids(front):
    """
    Poll Printify for Etsy listing IDs on products that have been published
    but don't yet have an Etsy ID in the spreadsheet.
    """
    cfg = FRONT_CONFIG[front]
    wb = load_workbook(cfg["spreadsheet"])
    ws = wb[cfg["sheet_name"]]

    header_row = 2
    headers = {ws.cell(row=header_row, column=c).value: c
               for c in range(1, ws.max_column + 1)}

    prod_col = headers.get("Printify Product ID")
    etsy_col = headers.get("Etsy Listing ID")

    if not prod_col or not etsy_col:
        print("  Could not find ID columns in spreadsheet")
        wb.close()
        return

    synced = 0
    for row in range(3, ws.max_row + 1):
        product_id = ws.cell(row=row, column=prod_col).value
        etsy_id = ws.cell(row=row, column=etsy_col).value

        if product_id and not etsy_id:
            try:
                product = get_product(str(product_id))
                external = product.get("external", {})
                eid = external.get("id")
                if eid:
                    ws.cell(row=row, column=etsy_col, value=str(eid))
                    fname = ws.cell(row=row, column=2).value or "?"
                    print(f"  [SYNC] {fname}: Etsy ID = {eid}")
                    synced += 1
                time.sleep(0.5)
            except Exception as e:
                print(f"  [ERR] Product {product_id}: {e}")

    if synced:
        wb.save(cfg["spreadsheet"])
    wb.close()
    print(f"  Synced {synced} Etsy listing IDs")


def main():
    parser = argparse.ArgumentParser(
        description="Bulk upload designs to Printify and publish to Etsy"
    )
    sub = parser.add_subparsers(dest="command")

    # ── upload command (default) ──
    up = sub.add_parser("upload", help="Upload and publish designs")
    up.add_argument("--front", required=True, choices=["A", "B"],
                    help="A = Sneaker Culture, B = Generalized")
    up.add_argument("--draft", action="store_true",
                    help="Create on Printify but don't publish to Etsy (for drops)")
    up.add_argument("--dry-run", action="store_true",
                    help="Preview what would be uploaded without doing it")

    # ── sync-ids command ──
    sync = sub.add_parser("sync-ids",
                          help="Poll Printify for Etsy listing IDs")
    sync.add_argument("--front", required=True, choices=["A", "B"])

    # ── catalog command (helper) ──
    cat = sub.add_parser("catalog",
                         help="Browse Printify catalog to find blueprint/variant IDs")
    cat.add_argument("--blueprints", action="store_true",
                     help="List all available blueprints")
    cat.add_argument("--providers", type=int, metavar="BLUEPRINT_ID",
                     help="List print providers for a blueprint")
    cat.add_argument("--variants", nargs=2, type=int,
                     metavar=("BLUEPRINT_ID", "PROVIDER_ID"),
                     help="List variants for a blueprint + provider")

    args = parser.parse_args()

    if args.command == "upload":
        if not args.dry_run:
            check_config()
        run_upload(args.front, draft=args.draft, dry_run=args.dry_run)

    elif args.command == "sync-ids":
        check_config()
        sync_etsy_ids(args.front)

    elif args.command == "catalog":
        check_config()
        if args.blueprints:
            resp = requests.get(f"{BASE}/catalog/blueprints.json",
                                headers=HEADERS)
            resp.raise_for_status()
            for bp in resp.json():
                print(f"  [{bp['id']}] {bp['title']}")
        elif args.providers:
            resp = requests.get(
                f"{BASE}/catalog/blueprints/{args.providers}/print_providers.json",
                headers=HEADERS)
            resp.raise_for_status()
            for pp in resp.json():
                print(f"  [{pp['id']}] {pp['title']}")
        elif args.variants:
            bid, pid = args.variants
            resp = requests.get(
                f"{BASE}/catalog/blueprints/{bid}/print_providers/{pid}/variants.json",
                headers=HEADERS)
            resp.raise_for_status()
            for v in resp.json().get("variants", []):
                print(f"  [{v['id']}] {v['title']} "
                      f"(size={v.get('options', {}).get('size', '?')}, "
                      f"color={v.get('options', {}).get('color', '?')})")
        else:
            cat.print_help()

    else:
        # Default to upload if --front is provided without subcommand
        parser.print_help()


if __name__ == "__main__":
    main()
