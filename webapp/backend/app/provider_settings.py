from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[3] / "workspace" / "pinterest" / "pinterest.db"

PRINTIFY_KEYS = ["PRINTIFY_TOKEN", "PRINTIFY_SHOP_ID"]
PRINTFUL_KEYS = ["PRINTFUL_API_KEY", "PRINTFUL_STORE_ID", "PRINTFUL_API_BASE"]
GENERATION_KEYS = ["OPENAI_API_KEY", "IDEOGRAM_API_KEY", "HF_API_TOKEN", "LEONARDO_API_KEY"]
ALL_KEYS = PRINTIFY_KEYS + PRINTFUL_KEYS + GENERATION_KEYS


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )


def _db_get(key: str) -> str | None:
    conn = _get_conn()
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None


def _db_set(key: str, value: str) -> None:
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
        (key, value),
    )
    conn.commit()
    conn.close()


def _db_delete(key: str) -> None:
    conn = _get_conn()
    conn.execute("DELETE FROM app_settings WHERE key = ?", (key,))
    conn.commit()
    conn.close()


def _mask(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def _refresh_workspace_module_globals() -> None:
    printify_mod = sys.modules.get("printify_upload")
    if printify_mod:
        token = os.environ.get("PRINTIFY_TOKEN", "")
        shop_id = os.environ.get("PRINTIFY_SHOP_ID", "")
        setattr(printify_mod, "TOKEN", token)
        setattr(printify_mod, "SHOP_ID", shop_id)
        setattr(printify_mod, "HEADERS", {"Authorization": f"Bearer {token}"})

    printful_mod = sys.modules.get("printful_upload")
    if printful_mod:
        api_key = os.environ.get("PRINTFUL_API_KEY", "")
        store_id = os.environ.get("PRINTFUL_STORE_ID", "")
        api_base = os.environ.get("PRINTFUL_API_BASE", "https://api.printful.com").rstrip("/")
        setattr(printful_mod, "PRINTFUL_API_KEY", api_key)
        setattr(printful_mod, "PRINTFUL_STORE_ID", store_id)
        setattr(printful_mod, "PRINTFUL_API_BASE", api_base)


def load_credentials_to_env() -> dict[str, bool]:
    result: dict[str, bool] = {}
    conn = _get_conn()
    for key in ALL_KEYS:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        if row and row["value"]:
            os.environ[key] = row["value"]
            result[key] = True
        else:
            os.environ.pop(key, None)
            result[key] = False
    conn.close()
    _refresh_workspace_module_globals()
    return result


def save_printify_credentials(token: str, shop_id: str) -> None:
    clean_token = token.strip()
    clean_shop_id = shop_id.strip()
    if not clean_token or not clean_shop_id:
        raise ValueError("PRINTIFY_TOKEN and PRINTIFY_SHOP_ID are required")
    _db_set("PRINTIFY_TOKEN", clean_token)
    _db_set("PRINTIFY_SHOP_ID", clean_shop_id)
    load_credentials_to_env()


def save_printful_credentials(api_key: str, store_id: str, api_base: str | None = None) -> None:
    clean_api_key = api_key.strip()
    clean_store_id = store_id.strip()
    if not clean_api_key or not clean_store_id:
        raise ValueError("PRINTFUL_API_KEY and PRINTFUL_STORE_ID are required")
    _db_set("PRINTFUL_API_KEY", clean_api_key)
    _db_set("PRINTFUL_STORE_ID", clean_store_id)

    clean_base = (api_base or "").strip()
    if clean_base:
        _db_set("PRINTFUL_API_BASE", clean_base)
    else:
        _db_delete("PRINTFUL_API_BASE")

    load_credentials_to_env()


def save_generation_credentials(
    openai_api_key: str | None = None,
    ideogram_api_key: str | None = None,
    hf_api_token: str | None = None,
    leonardo_api_key: str | None = None,
) -> None:
    updates = {
        "OPENAI_API_KEY": openai_api_key,
        "IDEOGRAM_API_KEY": ideogram_api_key,
        "HF_API_TOKEN": hf_api_token,
        "LEONARDO_API_KEY": leonardo_api_key,
    }

    for key, value in updates.items():
        if value is None:
            continue
        clean = value.strip()
        if clean:
            _db_set(key, clean)
        else:
            _db_delete(key)

    load_credentials_to_env()


def get_keys_status() -> dict[str, object]:
    def key_status(key: str) -> dict[str, object]:
        value = os.environ.get(key) or _db_get(key)
        return {
            "set": bool(value),
            "masked": _mask(value),
        }

    printify = {k: key_status(k) for k in PRINTIFY_KEYS}
    printful = {k: key_status(k) for k in PRINTFUL_KEYS}
    generation = {k: key_status(k) for k in GENERATION_KEYS}

    return {
        "groups": {
            "printify": {
                "configured": all(printify[k]["set"] for k in PRINTIFY_KEYS),
                "keys": printify,
            },
            "printful": {
                "configured": all(printful[k]["set"] for k in ["PRINTFUL_API_KEY", "PRINTFUL_STORE_ID"]),
                "keys": printful,
            },
            "generation": {
                "configured": any(generation[k]["set"] for k in GENERATION_KEYS),
                "keys": generation,
            },
        }
    }
