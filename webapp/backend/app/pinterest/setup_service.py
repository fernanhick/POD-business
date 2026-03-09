from __future__ import annotations

import os
from urllib.parse import urlencode

import httpx

from .models import get_conn

PINTEREST_API = "https://api.pinterest.com/v5"
REDIRECT_URI = "http://localhost:8000/api/pinterest/setup/callback"
OAUTH_SCOPES = "boards:read,boards:write,pins:read,pins:write,user_accounts:read"

CREDENTIAL_KEYS = [
    "PINTEREST_APP_ID",
    "PINTEREST_APP_SECRET",
    "PINTEREST_ACCESS_TOKEN",
    "PINTEREST_REFRESH_TOKEN",
]

DEFAULT_BOARDS = [
    {
        "env_key": "PINTEREST_BOARD_SNEAKER_CULTURE",
        "name": "Sneaker Collection Goals",
        "description": "Grails, rotation picks, shelf setups, collector displays",
    },
    {
        "env_key": "PINTEREST_BOARD_OUTFIT_IDEAS",
        "name": "Kicks & Fits",
        "description": "Sneaker-centered outfit ideas, how to style your kicks",
    },
    {
        "env_key": "PINTEREST_BOARD_ROOM_DECOR",
        "name": "Sneaker Cave Decor",
        "description": "Sneaker room setups, wall art, sneaker-themed decor",
    },
    {
        "env_key": "PINTEREST_BOARD_GIFTS",
        "name": "Gifts for Sneakerheads",
        "description": "Gift guides and holiday picks for sneaker collectors",
    },
    {
        "env_key": "PINTEREST_BOARD_STREETWEAR",
        "name": "Streetwear Culture",
        "description": "Street style, hustle mindset, sneaker culture quotes",
    },
]


def _db_get(key: str) -> str | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT value FROM pinterest_settings WHERE key = ?", (key,)
    ).fetchone()
    conn.close()
    return row["value"] if row else None


def _db_set(key: str, value: str) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO pinterest_settings (key, value) VALUES (?, ?)",
        (key, value),
    )
    conn.commit()
    conn.close()


def load_credentials_to_env() -> dict[str, bool]:
    """Load all credential keys from DB into os.environ. Returns presence map."""
    result: dict[str, bool] = {}
    all_keys = CREDENTIAL_KEYS + [b["env_key"] for b in DEFAULT_BOARDS]
    conn = get_conn()
    for key in all_keys:
        row = conn.execute(
            "SELECT value FROM pinterest_settings WHERE key = ?", (key,)
        ).fetchone()
        if row and row["value"]:
            os.environ[key] = row["value"]
            result[key] = True
        else:
            result[key] = False
    conn.close()
    return result


def save_app_credentials(app_id: str, app_secret: str) -> None:
    _db_set("PINTEREST_APP_ID", app_id)
    _db_set("PINTEREST_APP_SECRET", app_secret)
    load_credentials_to_env()


def get_oauth_authorize_url(app_id: str) -> str:
    params = {
        "client_id": app_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": OAUTH_SCOPES,
    }
    return f"https://www.pinterest.com/oauth/?{urlencode(params)}"


def exchange_code_for_tokens(code: str) -> dict:
    app_id = os.environ.get("PINTEREST_APP_ID") or _db_get("PINTEREST_APP_ID")
    app_secret = os.environ.get("PINTEREST_APP_SECRET") or _db_get("PINTEREST_APP_SECRET")
    if not app_id or not app_secret:
        raise RuntimeError("App credentials not configured")

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            f"{PINTEREST_API}/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
            },
            auth=(app_id, app_secret),
        )
        resp.raise_for_status()
        data = resp.json()

    access_token = data.get("access_token", "")
    refresh_token = data.get("refresh_token", "")

    if access_token:
        _db_set("PINTEREST_ACCESS_TOKEN", access_token)
    if refresh_token:
        _db_set("PINTEREST_REFRESH_TOKEN", refresh_token)

    load_credentials_to_env()
    return data


def refresh_access_token() -> dict:
    app_id = os.environ.get("PINTEREST_APP_ID") or _db_get("PINTEREST_APP_ID")
    app_secret = os.environ.get("PINTEREST_APP_SECRET") or _db_get("PINTEREST_APP_SECRET")
    refresh_token = os.environ.get("PINTEREST_REFRESH_TOKEN") or _db_get("PINTEREST_REFRESH_TOKEN")

    if not all([app_id, app_secret, refresh_token]):
        raise RuntimeError("Missing credentials for token refresh")

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            f"{PINTEREST_API}/oauth/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            auth=(app_id, app_secret),
        )
        resp.raise_for_status()
        data = resp.json()

    new_access = data.get("access_token", "")
    new_refresh = data.get("refresh_token", "")

    if new_access:
        _db_set("PINTEREST_ACCESS_TOKEN", new_access)
    if new_refresh:
        _db_set("PINTEREST_REFRESH_TOKEN", new_refresh)

    load_credentials_to_env()
    return data


def create_default_boards() -> list[dict]:
    token = os.environ.get("PINTEREST_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("Not connected — no access token")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    results: list[dict] = []

    with httpx.Client(base_url=PINTEREST_API, timeout=30.0) as client:
        # Fetch existing boards for 409 handling
        existing_boards: list[dict] = []
        try:
            resp = client.get("/boards", headers=headers)
            resp.raise_for_status()
            existing_boards = resp.json().get("items", [])
        except Exception:
            pass

        for board_def in DEFAULT_BOARDS:
            board_name = board_def["name"]
            env_key = board_def["env_key"]
            entry = {"env_key": env_key, "name": board_name, "status": "unknown", "board_id": None}

            try:
                resp = client.post(
                    "/boards",
                    headers=headers,
                    json={
                        "name": board_name,
                        "description": board_def["description"],
                        "privacy": "PUBLIC",
                    },
                )
                if resp.status_code == 409:
                    # Board already exists — find it by name
                    matched = next(
                        (b for b in existing_boards if b.get("name") == board_name),
                        None,
                    )
                    if matched:
                        board_id = matched["id"]
                        _db_set(env_key, board_id)
                        load_credentials_to_env()
                        entry.update(status="already_exists", board_id=board_id)
                    else:
                        entry["status"] = "conflict_not_found"
                else:
                    resp.raise_for_status()
                    data = resp.json()
                    board_id = data["id"]
                    _db_set(env_key, board_id)
                    load_credentials_to_env()
                    entry.update(status="created", board_id=board_id)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 409:
                    matched = next(
                        (b for b in existing_boards if b.get("name") == board_name),
                        None,
                    )
                    if matched:
                        board_id = matched["id"]
                        _db_set(env_key, board_id)
                        load_credentials_to_env()
                        entry.update(status="already_exists", board_id=board_id)
                    else:
                        entry["status"] = "conflict_not_found"
                else:
                    entry["status"] = f"error: {exc.response.status_code}"
            except Exception as exc:
                entry["status"] = f"error: {exc}"

            results.append(entry)

    return results


def get_setup_status() -> dict:
    has_app_id = bool(os.environ.get("PINTEREST_APP_ID") or _db_get("PINTEREST_APP_ID"))
    has_app_secret = bool(os.environ.get("PINTEREST_APP_SECRET") or _db_get("PINTEREST_APP_SECRET"))
    has_token = bool(os.environ.get("PINTEREST_ACCESS_TOKEN"))

    boards: list[dict] = []
    for board_def in DEFAULT_BOARDS:
        board_id = os.environ.get(board_def["env_key"]) or _db_get(board_def["env_key"])
        boards.append({
            "env_key": board_def["env_key"],
            "name": board_def["name"],
            "board_id": board_id or None,
            "created": bool(board_id),
        })

    all_boards_created = all(b["created"] for b in boards)

    return {
        "has_app_credentials": has_app_id and has_app_secret,
        "is_connected": has_token,
        "boards": boards,
        "all_boards_created": all_boards_created,
        "setup_complete": has_token and all_boards_created,
    }
