from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from base64 import urlsafe_b64encode
from pathlib import Path
from urllib.parse import urlencode

import httpx

ETSY_API_BASE = "https://api.etsy.com/v3"
ETSY_OAUTH_BASE = "https://www.etsy.com/oauth/connect"
ETSY_TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
REDIRECT_URI = "http://localhost:8000/api/etsy/setup/callback"
SCOPES = "listings_r listings_w shops_r shops_w email_r transactions_r"

CREDENTIAL_KEYS = [
    "ETSY_API_KEY",
    "ETSY_SHARED_SECRET",
    "ETSY_ACCESS_TOKEN",
    "ETSY_REFRESH_TOKEN",
    "ETSY_SHOP_ID",
    "ETSY_NUMERIC_SHOP_ID",
]

# Section name -> product type mapping
DEFAULT_SECTIONS = [
    {"name": "Sneaker Culture Tees", "front": "A", "product_type": "tshirt"},
    {"name": "Sneakerhead Hoodies", "front": "A", "product_type": "hoodie"},
    {"name": "Gifts for Sneakerheads", "front": "A", "product_type": "gift"},
    {"name": "New Drops", "front": "A", "product_type": "drop"},
]

DB_PATH = Path(__file__).resolve().parents[4] / "workspace" / "pinterest" / "pinterest.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS etsy_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def _db_get(key: str) -> str | None:
    conn = _get_conn()
    row = conn.execute(
        "SELECT value FROM etsy_settings WHERE key = ?", (key,)
    ).fetchone()
    conn.close()
    return row["value"] if row else None


def _db_set(key: str, value: str) -> None:
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO etsy_settings (key, value) VALUES (?, ?)",
        (key, value),
    )
    conn.commit()
    conn.close()


def load_credentials_to_env() -> dict[str, bool]:
    """Load all Etsy credential keys from DB into os.environ."""
    result: dict[str, bool] = {}
    section_keys = [f"ETSY_SECTION_{s['name'].upper().replace(' ', '_')}" for s in DEFAULT_SECTIONS]
    all_keys = CREDENTIAL_KEYS + section_keys
    conn = _get_conn()
    for key in all_keys:
        row = conn.execute(
            "SELECT value FROM etsy_settings WHERE key = ?", (key,)
        ).fetchone()
        if row and row["value"]:
            os.environ[key] = row["value"]
            result[key] = True
        else:
            result[key] = False
    conn.close()
    return result


def save_app_credentials(api_key: str, shared_secret: str) -> None:
    _db_set("ETSY_API_KEY", api_key)
    _db_set("ETSY_SHARED_SECRET", shared_secret)
    load_credentials_to_env()


# ── PKCE helpers ──────────────────────────────────────────────────

def _generate_pkce() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge."""
    code_verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


def get_oauth_authorize_url(api_key: str) -> str:
    """Build Etsy OAuth URL with PKCE. Stores code_verifier in DB."""
    code_verifier, code_challenge = _generate_pkce()
    state = secrets.token_urlsafe(16)

    # Store for callback
    _db_set("ETSY_OAUTH_CODE_VERIFIER", code_verifier)
    _db_set("ETSY_OAUTH_STATE", state)

    params = {
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "client_id": api_key,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{ETSY_OAUTH_BASE}?{urlencode(params)}"


def exchange_code_for_tokens(code: str, state: str) -> dict:
    """Exchange authorization code for access + refresh tokens."""
    api_key = os.environ.get("ETSY_API_KEY") or _db_get("ETSY_API_KEY")
    stored_state = _db_get("ETSY_OAUTH_STATE")
    code_verifier = _db_get("ETSY_OAUTH_CODE_VERIFIER")

    if not api_key:
        raise RuntimeError("Etsy API key not configured")
    if state != stored_state:
        raise RuntimeError("OAuth state mismatch")
    if not code_verifier:
        raise RuntimeError("Missing PKCE code_verifier")

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            ETSY_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": api_key,
                "redirect_uri": REDIRECT_URI,
                "code": code,
                "code_verifier": code_verifier,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    access_token = data.get("access_token", "")
    refresh_token = data.get("refresh_token", "")

    if access_token:
        _db_set("ETSY_ACCESS_TOKEN", access_token)
    if refresh_token:
        _db_set("ETSY_REFRESH_TOKEN", refresh_token)

    # Clean up PKCE values
    _db_set("ETSY_OAUTH_CODE_VERIFIER", "")
    _db_set("ETSY_OAUTH_STATE", "")

    load_credentials_to_env()

    # Fetch numeric shop ID
    _resolve_numeric_shop_id()

    return data


def refresh_access_token() -> dict:
    """Refresh an expired Etsy access token."""
    api_key = os.environ.get("ETSY_API_KEY") or _db_get("ETSY_API_KEY")
    refresh_token = os.environ.get("ETSY_REFRESH_TOKEN") or _db_get("ETSY_REFRESH_TOKEN")

    if not api_key or not refresh_token:
        raise RuntimeError("Missing credentials for token refresh")

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            ETSY_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": api_key,
                "refresh_token": refresh_token,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    new_access = data.get("access_token", "")
    new_refresh = data.get("refresh_token", "")

    if new_access:
        _db_set("ETSY_ACCESS_TOKEN", new_access)
    if new_refresh:
        _db_set("ETSY_REFRESH_TOKEN", new_refresh)

    load_credentials_to_env()
    return data


# ── Shop helpers ──────────────────────────────────────────────────

def _headers() -> dict[str, str]:
    token = os.environ.get("ETSY_ACCESS_TOKEN") or _db_get("ETSY_ACCESS_TOKEN")
    api_key = os.environ.get("ETSY_API_KEY") or _db_get("ETSY_API_KEY")
    return {
        "Authorization": f"Bearer {token}",
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }


def _resolve_numeric_shop_id() -> str | None:
    """Look up numeric shop ID from shop name via Etsy API."""
    shop_name = os.environ.get("ETSY_SHOP_ID") or _db_get("ETSY_SHOP_ID") or "RotationClub"
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{ETSY_API_BASE}/application/shops/{shop_name}",
                headers=_headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            numeric_id = str(data.get("shop_id", ""))
            if numeric_id:
                _db_set("ETSY_NUMERIC_SHOP_ID", numeric_id)
                _db_set("ETSY_SHOP_ID", shop_name)
                load_credentials_to_env()
                return numeric_id
    except Exception:
        pass
    return None


def get_numeric_shop_id() -> str:
    """Get the numeric shop ID, resolving if needed."""
    numeric = os.environ.get("ETSY_NUMERIC_SHOP_ID") or _db_get("ETSY_NUMERIC_SHOP_ID")
    if numeric:
        return numeric
    resolved = _resolve_numeric_shop_id()
    if resolved:
        return resolved
    raise RuntimeError("Could not resolve Etsy numeric shop ID")


# ── Sections ──────────────────────────────────────────────────────

def get_shop_sections() -> list[dict]:
    """Fetch existing shop sections from Etsy."""
    shop_id = get_numeric_shop_id()
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            f"{ETSY_API_BASE}/application/shops/{shop_id}/sections",
            headers=_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
    return data.get("results", [])


def create_shop_sections() -> list[dict]:
    """Create default shop sections. Skips any that already exist."""
    shop_id = get_numeric_shop_id()
    existing = get_shop_sections()
    existing_names = {s["title"] for s in existing}

    results: list[dict] = []
    for section_def in DEFAULT_SECTIONS:
        name = section_def["name"]
        entry = {"name": name, "status": "unknown", "section_id": None}

        if name in existing_names:
            matched = next(s for s in existing if s["title"] == name)
            section_id = str(matched["shop_section_id"])
            env_key = f"ETSY_SECTION_{name.upper().replace(' ', '_')}"
            _db_set(env_key, section_id)
            entry.update(status="already_exists", section_id=section_id)
        else:
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(
                        f"{ETSY_API_BASE}/application/shops/{shop_id}/sections",
                        headers=_headers(),
                        json={"title": name},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    section_id = str(data["shop_section_id"])
                    env_key = f"ETSY_SECTION_{name.upper().replace(' ', '_')}"
                    _db_set(env_key, section_id)
                    entry.update(status="created", section_id=section_id)
            except Exception as exc:
                entry["status"] = f"error: {exc}"

        results.append(entry)

    load_credentials_to_env()
    return results


def assign_listing_to_section(listing_id: str, section_name: str) -> bool:
    """Assign an Etsy listing to a shop section by name."""
    env_key = f"ETSY_SECTION_{section_name.upper().replace(' ', '_')}"
    section_id = os.environ.get(env_key) or _db_get(env_key)

    if not section_id:
        # Try to find it from existing sections
        sections = get_shop_sections()
        matched = next((s for s in sections if s["title"] == section_name), None)
        if matched:
            section_id = str(matched["shop_section_id"])
            _db_set(env_key, section_id)
        else:
            return False

    shop_id = get_numeric_shop_id()
    with httpx.Client(timeout=30.0) as client:
        resp = client.put(
            f"{ETSY_API_BASE}/application/listings/{listing_id}",
            headers=_headers(),
            json={"shop_section_id": int(section_id)},
        )
        resp.raise_for_status()
    return True


def auto_assign_section(listing_id: str, front: str, product_type: str) -> str | None:
    """Auto-assign a listing to the correct section based on front + product type."""
    section_map = {
        ("A", "tshirt"): "Sneaker Culture Tees",
        ("A", "hoodie"): "Sneakerhead Hoodies",
        ("B", "tshirt"): "Sneaker Culture Tees",
        ("B", "hoodie"): "Sneakerhead Hoodies",
    }
    section_name = section_map.get((front, product_type))
    if section_name and assign_listing_to_section(listing_id, section_name):
        return section_name
    return None


def get_setup_status() -> dict:
    has_api_key = bool(os.environ.get("ETSY_API_KEY") or _db_get("ETSY_API_KEY"))
    has_secret = bool(os.environ.get("ETSY_SHARED_SECRET") or _db_get("ETSY_SHARED_SECRET"))
    has_token = bool(os.environ.get("ETSY_ACCESS_TOKEN") or _db_get("ETSY_ACCESS_TOKEN"))
    has_shop_id = bool(os.environ.get("ETSY_NUMERIC_SHOP_ID") or _db_get("ETSY_NUMERIC_SHOP_ID"))

    sections: list[dict] = []
    for section_def in DEFAULT_SECTIONS:
        env_key = f"ETSY_SECTION_{section_def['name'].upper().replace(' ', '_')}"
        section_id = os.environ.get(env_key) or _db_get(env_key)
        sections.append({
            "name": section_def["name"],
            "section_id": section_id or None,
            "created": bool(section_id),
        })

    all_sections_created = all(s["created"] for s in sections)

    return {
        "has_app_credentials": has_api_key and has_secret,
        "is_connected": has_token,
        "has_shop_id": has_shop_id,
        "shop_name": os.environ.get("ETSY_SHOP_ID") or _db_get("ETSY_SHOP_ID") or "",
        "sections": sections,
        "all_sections_created": all_sections_created,
        "setup_complete": has_token and all_sections_created,
    }
