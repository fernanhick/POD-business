from __future__ import annotations

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


async def upload_media(image_path: str) -> str:
    if not is_configured():
        raise RuntimeError("Pinterest API not configured")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
        # Step 1: Register media
        resp = await client.post(
            "/media",
            headers=_headers(),
            json={"media_type": "image"},
        )
        resp.raise_for_status()
        media_data = resp.json()
        media_id = media_data["media_id"]
        upload_url = media_data["upload_url"]

        # Step 2: Upload image binary
        image_bytes = Path(image_path).read_bytes()
        upload_resp = await client.put(
            upload_url,
            content=image_bytes,
            headers={"Content-Type": "image/png"},
        )
        upload_resp.raise_for_status()

    return media_id


async def create_pin(
    board_id: str,
    title: str,
    description: str,
    link: str | None,
    media_id: str,
) -> str:
    if not is_configured():
        raise RuntimeError("Pinterest API not configured")

    payload: dict = {
        "board_id": board_id,
        "title": title,
        "description": description,
        "media_source": {
            "source_type": "media_id",
            "media_id": media_id,
        },
    }
    if link:
        payload["link"] = link

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
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
