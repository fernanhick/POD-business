"""
printful_upload.py -- Printful upload + publish helpers

Implements a provider-compatible interface for the web API orchestration layer.

Required env vars:
    PRINTFUL_API_KEY
    PRINTFUL_STORE_ID
    PRINTFUL_TSHIRT_VARIANT_IDS   (comma-separated variant IDs)
    PRINTFUL_HOODIE_VARIANT_IDS   (comma-separated variant IDs)

Optional env vars:
    PRINTFUL_API_BASE             (defaults to https://api.printful.com)
    PRINTFUL_A_TSHIRT_VARIANT_IDS / PRINTFUL_B_TSHIRT_VARIANT_IDS
    PRINTFUL_A_HOODIE_VARIANT_IDS / PRINTFUL_B_HOODIE_VARIANT_IDS
"""

from __future__ import annotations

import base64
import os
from typing import Any

import requests
from dotenv import load_dotenv

try:
    from pod_pricing import get_profile_for_provider_market, calc_price_cents
except ImportError:
    from workspace.pod_pricing import get_profile_for_provider_market, calc_price_cents

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

PRINTFUL_API_KEY = os.environ.get("PRINTFUL_API_KEY", "")
PRINTFUL_STORE_ID = os.environ.get("PRINTFUL_STORE_ID", "")
PRINTFUL_API_BASE = os.environ.get("PRINTFUL_API_BASE", "https://api.printful.com").rstrip("/")


def _headers() -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {PRINTFUL_API_KEY}",
    }
    if PRINTFUL_STORE_ID:
        headers["X-PF-Store-Id"] = str(PRINTFUL_STORE_ID)
    return headers


def _wait_for_file_ready(file_id: str, timeout_seconds: int = 45) -> dict[str, Any]:
    import time

    deadline = time.time() + timeout_seconds
    last_payload: dict[str, Any] = {}
    while time.time() < deadline:
        response = requests.get(
            f"{PRINTFUL_API_BASE}/files/{int(file_id)}",
            headers=_headers(),
            timeout=20,
        )
        if not response.ok:
            time.sleep(1)
            continue
        payload = _extract_result(response.json())
        if not isinstance(payload, dict):
            time.sleep(1)
            continue
        last_payload = payload
        status = str(payload.get("status") or "").lower()
        if status == "ok":
            return payload
        if status == "failed":
            raise RuntimeError(f"Printful file processing failed for id={file_id}: {payload}")
        time.sleep(1)

    raise RuntimeError(
        f"Printful file {file_id} was not ready before timeout; last status={last_payload.get('status')}"
    )


def _parse_variant_ids(value: str | None) -> list[int]:
    if not value:
        return []
    result: list[int] = []
    for item in value.split(","):
        text = item.strip()
        if not text:
            continue
        result.append(int(text))
    return result


def _variant_ids_for(front_code: str, product_type: str) -> list[int]:
    scoped_key = f"PRINTFUL_{front_code}_{product_type.upper()}_VARIANT_IDS"
    default_key = f"PRINTFUL_{product_type.upper()}_VARIANT_IDS"
    return _parse_variant_ids(os.environ.get(scoped_key) or os.environ.get(default_key))


def _base_template(product_type: str) -> dict[str, Any]:
    if product_type == "hoodie":
        return {
            "base_cost_cents": 2224,
            "oversize_costs": {"2XL": 2437, "3XL": 2558, "4XL": 2618, "5XL": 2618},
            "shipping_cents": 769,
        }
    return {
        "base_cost_cents": 1129,
        "oversize_costs": {"2XL": 1382, "3XL": 1612, "4XL": 1863},
        "shipping_cents": 429,
    }


def _size_cycle(product_type: str) -> list[str]:
    if product_type == "hoodie":
        return ["S", "M", "L", "XL", "2XL", "3XL", "4XL", "5XL"]
    return ["S", "M", "L", "XL", "2XL", "3XL", "4XL"]


def _build_front_config() -> dict[str, Any]:
    from printify_upload import FRONT_CONFIG as PRINTIFY_FRONT_CONFIG

    result: dict[str, Any] = {}
    for front_code in ("A", "B"):
        result[front_code] = {"products": {}}
        for product_type in ("tshirt", "hoodie"):
            source = PRINTIFY_FRONT_CONFIG[front_code]["products"][product_type]
            result[front_code]["products"][product_type] = {
                "title_template": source["title_template"],
                "description_template": source["description_template"],
                "tags": list(source.get("tags", [])),
                **_base_template(product_type),
                "variant_ids": _variant_ids_for(front_code, product_type),
                "product_type": product_type,
            }
    return result


FRONT_CONFIG = _build_front_config()


def get_product_config(front_code: str, product_type: str) -> dict[str, Any]:
    if front_code not in FRONT_CONFIG:
        raise ValueError(f"Unknown front code: {front_code}")
    products = FRONT_CONFIG[front_code]["products"]
    if product_type not in products:
        raise ValueError(f"Unknown product type: {product_type}")
    return products[product_type]


def check_config() -> bool:
    if not PRINTFUL_API_KEY:
        return False
    if not PRINTFUL_STORE_ID:
        return False
    has_tshirt = bool(_parse_variant_ids(os.environ.get("PRINTFUL_TSHIRT_VARIANT_IDS")))
    has_hoodie = bool(_parse_variant_ids(os.environ.get("PRINTFUL_HOODIE_VARIANT_IDS")))
    return has_tshirt and has_hoodie


def _extract_result(resp_json: dict[str, Any]) -> dict[str, Any]:
    if "result" in resp_json and isinstance(resp_json["result"], dict):
        return resp_json["result"]
    return resp_json


def upload_image(filepath: str) -> str:
    if not PRINTFUL_API_KEY:
        raise RuntimeError("PRINTFUL_API_KEY not configured")
    if not PRINTFUL_STORE_ID:
        raise RuntimeError("PRINTFUL_STORE_ID not configured")

    file_name = os.path.basename(filepath)
    with open(filepath, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("ascii")

    response = requests.post(
        f"{PRINTFUL_API_BASE}/files",
        headers={**_headers(), "Content-Type": "application/json"},
        json={
            "type": "default",
            "filename": file_name,
            "visible": True,
            "data": encoded,
        },
        timeout=60,
    )

    if not response.ok:
        raise RuntimeError(
            f"Printful file upload failed [{response.status_code}]: {response.text[:400]}"
        )
    payload = _extract_result(response.json())
    file_id = payload.get("id")
    if not file_id:
        raise RuntimeError(f"Unexpected Printful file upload response: {payload}")
    file_info = _wait_for_file_ready(str(file_id))
    print(
        f"[printful] file uploaded: id={file_id} name={file_name} status={file_info.get('status')}"
    )
    return str(file_id)


def create_product(image_id: str, title: str, description: str, cfg: dict, design_name: str | None = None) -> str:
    if not PRINTFUL_API_KEY:
        raise RuntimeError("PRINTFUL_API_KEY not configured")
    if not PRINTFUL_STORE_ID:
        raise RuntimeError("PRINTFUL_STORE_ID not configured")

    variant_ids: list[int] = list(cfg.get("variant_ids") or [])
    if not variant_ids:
        product_type = cfg.get("product_type", "tshirt")
        raise RuntimeError(
            f"No Printful variant IDs configured for {product_type}. Set PRINTFUL_{product_type.upper()}_VARIANT_IDS."
        )

    file_info = _wait_for_file_ready(str(image_id))
    thumbnail_url = (
        file_info.get("preview_url")
        or file_info.get("thumbnail_url")
        or file_info.get("url")
    )
    print(
        f"[printful] file ready for product: id={image_id} status={file_info.get('status')} thumbnail={bool(thumbnail_url)}"
    )

    profile = get_profile_for_provider_market("printful", "EU")
    sizes = _size_cycle(cfg.get("product_type", "tshirt"))
    oversize_costs = cfg.get("oversize_costs", {})

    sync_variants = []
    for index, variant_id in enumerate(variant_ids):
        size = sizes[index % len(sizes)]
        price_cents, _ = calc_price_cents(
            base_cost_cents=cfg["base_cost_cents"],
            shipping_cents=cfg["shipping_cents"],
            profile=profile,
            size_tier=size,
            oversize_costs_cents=oversize_costs,
        )
        retail_price = f"{price_cents / 100:.2f}"
        sync_variants.append(
            {
                "variant_id": int(variant_id),
                "retail_price": retail_price,
                "files": [{"id": int(image_id), "type": "default"}],
            }
        )

    primary_payload = {
            "store_id": int(PRINTFUL_STORE_ID),
        "sync_product": {
            "name": title,
            "thumbnail": thumbnail_url,
            "is_ignored": False,
        },
        "sync_variants": sync_variants,
    }

    fallback_variants = []
    for item in sync_variants:
        copy = dict(item)
        copy["files"] = [{"id": int(image_id), "type": "default"}]
        fallback_variants.append(copy)
    fallback_payload = {
            "store_id": int(PRINTFUL_STORE_ID),
        "sync_product": {
            "name": title,
            "thumbnail": thumbnail_url,
            "is_ignored": False,
        },
        "sync_variants": fallback_variants,
    }

    errors: list[str] = []
    for attempt, payload in enumerate((primary_payload, fallback_payload), start=1):
        response = requests.post(
            f"{PRINTFUL_API_BASE}/store/products",
            headers={**_headers(), "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        print(f"[printful] create_product attempt {attempt}: status={response.status_code}")
        if response.ok:
            result = _extract_result(response.json())
            sync_product = result.get("sync_product", {}) if isinstance(result, dict) else {}
            product_id = sync_product.get("id") or result.get("id")
            if not product_id:
                raise RuntimeError(f"Unexpected Printful product response: {result}")
            print(f"[printful] product created: id={product_id} (attempt {attempt})")
            return str(product_id)
        errors.append(f"[attempt {attempt}] {response.status_code}: {response.text[:300]}")

    raise RuntimeError("Printful product creation failed: " + " | ".join(errors))


def publish_product(product_id: str) -> None:
    if not PRINTFUL_API_KEY:
        raise RuntimeError("PRINTFUL_API_KEY not configured")

    response = requests.put(
        f"{PRINTFUL_API_BASE}/store/products/{product_id}",
        headers={**_headers(), "Content-Type": "application/json"},
        json={"sync_product": {"is_ignored": False}},
        timeout=30,
    )
    if response.status_code in (200, 201):
        return
    if response.status_code in (404, 405):
        return
    response.raise_for_status()


def get_product(product_id: str) -> dict[str, Any]:
    if not PRINTFUL_API_KEY:
        raise RuntimeError("PRINTFUL_API_KEY not configured")

    response = requests.get(
        f"{PRINTFUL_API_BASE}/store/products/{product_id}",
        headers=_headers(),
        timeout=30,
    )
    response.raise_for_status()
    result = _extract_result(response.json())
    if not isinstance(result, dict):
        return {"external": {}}

    external_id = result.get("external_id")
    if not external_id:
        sync_product = result.get("sync_product", {})
        if isinstance(sync_product, dict):
            external_id = sync_product.get("external_id")

    normalized = dict(result)
    normalized["external"] = {"id": external_id} if external_id else {}
    return normalized


def _header_map(ws) -> dict[str, int]:
    return {
        (cell.value or "").strip(): idx
        for idx, cell in enumerate(ws[2], start=1)
        if isinstance(cell.value, str)
    }


def _ensure_header_column(ws, headers: dict[str, int], name: str) -> int:
    column = headers.get(name)
    if column:
        return column
    column = ws.max_column + 1
    ws.cell(row=2, column=column, value=name)
    headers[name] = column
    return column


def update_spreadsheet_ids(
    spreadsheet_path: str,
    sheet_name: str,
    filename: str,
    image_id: str | None = None,
    product_id: str | None = None,
    etsy_id: str | None = None,
    status: str | None = None,
    provider: str = "printful",
    market: str = "EU",
) -> bool:
    try:
        from printify_upload import update_spreadsheet_ids as shared_update
    except Exception:
        return False

    return bool(
        shared_update(
            spreadsheet_path,
            sheet_name,
            filename,
            image_id=image_id,
            product_id=product_id,
            etsy_id=etsy_id,
            status=status,
        )
    )
