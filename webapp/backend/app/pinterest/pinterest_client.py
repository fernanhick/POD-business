from __future__ import annotations

import base64
import os
from pathlib import Path

import httpx

BASE_URL = "https://api.pinterest.com/v5"


def _get_token() -> str | None:
    return os.environ.get("PINTEREST_ACCESS_TOKEN") or None


def is_configured() -> bool:
    return bool(_get_token())


def _headers() -> dict[str, str]:
    token = _get_token()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


async def create_pin(
    board_id: str,
    title: str,
    description: str,
    link: str | None,
    image_path: str,
) -> str:
    """Create a pin with an inline base64 image (no /media upload needed)."""
    if not is_configured():
        raise RuntimeError("Pinterest API not configured")

    image_bytes = Path(image_path).read_bytes()
    image_b64 = base64.standard_b64encode(image_bytes).decode("ascii")

    payload: dict = {
        "board_id": board_id,
        "title": title,
        "description": description,
        "media_source": {
            "source_type": "image_base64",
            "content_type": "image/png",
            "data": image_b64,
        },
    }
    if link:
        payload["link"] = link

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
        resp = await client.post("/pins", headers=_headers(), json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["id"]


async def get_pin_metrics(pinterest_pin_id: str) -> dict:
    if not is_configured():
        raise RuntimeError("Pinterest API not configured")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        resp = await client.get(
            f"/pins/{pinterest_pin_id}/analytics",
            headers=_headers(),
            params={
                "start_date": "2020-01-01",
                "end_date": "2099-12-31",
                "metric_types": "IMPRESSION,SAVE,PIN_CLICK",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    metrics = {"impressions": 0, "saves": 0, "clicks": 0}
    if "all" in data:
        summary = data["all"].get("lifetime_metrics", data["all"])
        metrics["impressions"] = summary.get("IMPRESSION", 0)
        metrics["saves"] = summary.get("SAVE", 0)
        metrics["clicks"] = summary.get("PIN_CLICK", 0)
    return metrics


async def get_boards() -> list[dict]:
    if not is_configured():
        raise RuntimeError("Pinterest API not configured")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        resp = await client.get("/boards", headers=_headers())
        resp.raise_for_status()
        data = resp.json()
        return data.get("items", [])


async def refresh_access_token() -> str | None:
    app_id = os.environ.get("PINTEREST_APP_ID")
    app_secret = os.environ.get("PINTEREST_APP_SECRET")
    refresh_token = os.environ.get("PINTEREST_REFRESH_TOKEN")

    if not all([app_id, app_secret, refresh_token]):
        return None

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.pinterest.com/v5/oauth/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            auth=(app_id, app_secret),
        )
        resp.raise_for_status()
        data = resp.json()
        new_token = data.get("access_token")
        if new_token:
            os.environ["PINTEREST_ACCESS_TOKEN"] = new_token
        return new_token
