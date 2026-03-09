from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

router = APIRouter()


class SaveCredentialsRequest(BaseModel):
    api_key: str
    shared_secret: str


class AssignSectionRequest(BaseModel):
    listing_id: str
    section_name: str


# ── Setup ─────────────────────────────────────────────────────────

@router.get("/setup/status")
def setup_status():
    from .setup_service import get_setup_status
    return get_setup_status()


@router.post("/setup/credentials")
def save_credentials(payload: SaveCredentialsRequest):
    from .setup_service import save_app_credentials, get_oauth_authorize_url
    save_app_credentials(payload.api_key, payload.shared_secret)
    authorize_url = get_oauth_authorize_url(payload.api_key)
    return {"authorize_url": authorize_url}


@router.get("/setup/callback")
def oauth_callback(
    code: str = Query(default=None),
    state: str = Query(default=None),
    error: str = Query(default=None),
):
    if error or not code:
        return RedirectResponse(url="http://localhost:5173/?etsy_setup=error")
    try:
        from .setup_service import exchange_code_for_tokens
        exchange_code_for_tokens(code, state or "")
        return RedirectResponse(url="http://localhost:5173/?etsy_setup=success")
    except Exception:
        return RedirectResponse(url="http://localhost:5173/?etsy_setup=error")


@router.post("/setup/create-sections")
def create_sections():
    from .setup_service import create_shop_sections
    sections = create_shop_sections()
    return {"sections": sections}


@router.post("/setup/refresh-token")
def refresh_token():
    from .setup_service import refresh_access_token
    data = refresh_access_token()
    return {"refreshed": True, "has_access_token": bool(data.get("access_token"))}


# ── Sections ──────────────────────────────────────────────────────

@router.get("/sections")
def list_sections():
    from .setup_service import get_shop_sections
    return {"sections": get_shop_sections()}


@router.post("/sections/assign")
def assign_section(payload: AssignSectionRequest):
    from .setup_service import assign_listing_to_section
    success = assign_listing_to_section(payload.listing_id, payload.section_name)
    if not success:
        raise HTTPException(status_code=400, detail=f"Could not assign section '{payload.section_name}'")
    return {"assigned": True, "listing_id": payload.listing_id, "section": payload.section_name}


@router.post("/sections/auto-assign")
def auto_assign(listing_id: str = Query(...), front: str = Query(...), product_type: str = Query(...)):
    from .setup_service import auto_assign_section
    result = auto_assign_section(listing_id, front, product_type)
    if not result:
        raise HTTPException(status_code=400, detail="Could not auto-assign section")
    return {"assigned": True, "listing_id": listing_id, "section": result}
