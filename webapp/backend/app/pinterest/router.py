from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse

from .models import (
    AnalyticsSummary,
    AppPhaseResponse,
    AppPhaseUpdateRequest,
    GeneratePinsRequest,
    PinResponse,
    PinterestMetrics,
    PinterestStatusResponse,
    SaveCredentialsRequest,
    SchedulePinsRequest,
    ScheduleQueueResponse,
    ScheduleQueueItem,
    init_db,
    get_conn,
)

router = APIRouter()


# ── Designs ────────────────────────────────────────────────────────

@router.get("/designs")
def list_designs():
    from .spreadsheet_reader import get_approved_designs
    designs = get_approved_designs()
    return {"items": [d.model_dump() for d in designs], "count": len(designs)}


@router.get("/designs/image")
def get_design_image(filename: str = Query(...)):
    from .spreadsheet_reader import get_approved_designs

    safe_name = Path(filename).name
    if safe_name != filename or not safe_name.lower().endswith(".png"):
        raise HTTPException(status_code=400, detail="Invalid filename")

    base_dir = Path(__file__).resolve().parents[4]
    image_path = base_dir / "workspace" / "front_a_sneaker" / "approved" / safe_name
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(path=image_path, media_type="image/png", filename=safe_name)


# ── Pins ───────────────────────────────────────────────────────────

@router.post("/pins/generate")
def generate_pins(payload: GeneratePinsRequest):
    from .pin_factory import generate_pins_for_design
    pins = generate_pins_for_design(payload.design_filename, payload.template_ids)
    return {"items": [p.model_dump() for p in pins], "count": len(pins)}


@router.get("/pins")
def list_pins(
    status: str | None = Query(default=None),
    pin_type: str | None = Query(default=None),
    limit: int = Query(default=100),
):
    conn = get_conn()
    query = "SELECT * FROM pins"
    conditions: list[str] = []
    params: list = []

    if status:
        conditions.append("status = ?")
        params.append(status)
    if pin_type:
        conditions.append("pin_type = ?")
        params.append(pin_type)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    items = [dict(r) for r in rows]
    return {"items": items, "count": len(items)}


@router.get("/pins/image")
def get_pin_image(id: str = Query(...)):
    conn = get_conn()
    row = conn.execute("SELECT image_path FROM pins WHERE id = ?", (id,)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Pin not found")

    image_path = Path(row["image_path"])
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Pin image not found on disk")

    return FileResponse(path=image_path, media_type="image/png")


# ── Schedule ───────────────────────────────────────────────────────

@router.post("/schedule")
def schedule_pins(payload: SchedulePinsRequest):
    from .scheduler import add_pins_to_queue
    count = add_pins_to_queue(payload.pin_ids, payload.start_from)
    return {"scheduled": count}


@router.get("/schedule/queue")
def get_queue(days: int = Query(default=14)):
    from .scheduler import get_schedule_queue
    raw = get_schedule_queue(days)

    items: list[dict] = []
    for r in raw:
        pin = PinResponse(
            id=r["pin_id"],
            design_filename=r["design_filename"],
            pin_type=r["pin_type"],
            title=r["title"],
            description=r["description"],
            board_id=r["board_id"],
            image_path=r["image_path"],
            status=r["pin_status"],
            keywords=r.get("keywords"),
            created_at=r["created_at"],
            posted_at=r.get("posted_at"),
            impressions=r.get("impressions", 0),
            saves=r.get("saves", 0),
            clicks=r.get("clicks", 0),
        )
        items.append({
            "id": r["id"],
            "pin_id": r["pin_id"],
            "scheduled_at": r["scheduled_at"],
            "status": r["status"],
            "pin": pin.model_dump(),
        })

    return {"items": items, "total": len(items)}


@router.post("/schedule/run")
async def run_now():
    from .scheduler import post_next_pin
    result = await post_next_pin()
    if result is None:
        return {"message": "No pending pins to post"}
    return result


@router.get("/schedule/settings")
def schedule_settings():
    from .scheduler import get_schedule_settings
    return get_schedule_settings()


# ── Analytics ──────────────────────────────────────────────────────

@router.get("/analytics")
def get_analytics():
    conn = get_conn()

    total = conn.execute("SELECT COUNT(*) as c FROM pins").fetchone()["c"]
    posted = conn.execute(
        "SELECT COUNT(*) as c FROM pins WHERE status = 'posted'"
    ).fetchone()["c"]
    scheduled = conn.execute(
        "SELECT COUNT(*) as c FROM pins WHERE status = 'queued'"
    ).fetchone()["c"]
    draft = conn.execute(
        "SELECT COUNT(*) as c FROM pins WHERE status = 'draft'"
    ).fetchone()["c"]

    agg = conn.execute(
        "SELECT COALESCE(SUM(impressions),0) as imp, COALESCE(SUM(saves),0) as sav, "
        "COALESCE(SUM(clicks),0) as clk FROM pins WHERE status = 'posted'"
    ).fetchone()
    impressions = agg["imp"]
    saves = agg["sav"]
    clicks = agg["clk"]
    ctr = (clicks / impressions * 100) if impressions > 0 else 0.0

    # Top pins by impressions
    top_rows = conn.execute(
        "SELECT * FROM pins WHERE status = 'posted' ORDER BY impressions DESC LIMIT 10"
    ).fetchall()
    top_pins = [PinResponse(**dict(r)).model_dump() for r in top_rows]

    # Scaling candidates: CTR >= 3x average
    scaling = []
    if ctr > 0:
        threshold = ctr * 3
        candidates = conn.execute(
            "SELECT * FROM pins WHERE status = 'posted' AND impressions > 0"
        ).fetchall()
        for row in candidates:
            r = dict(row)
            pin_ctr = (r["clicks"] / r["impressions"] * 100) if r["impressions"] > 0 else 0
            if pin_ctr >= threshold:
                scaling.append(PinResponse(**r).model_dump())

    conn.close()

    return AnalyticsSummary(
        total_pins=total,
        posted_pins=posted,
        scheduled_pins=scheduled,
        draft_pins=draft,
        metrics=PinterestMetrics(
            impressions=impressions,
            saves=saves,
            clicks=clicks,
            ctr=round(ctr, 2),
        ),
        top_pins=top_pins,
        scaling_candidates=scaling,
    ).model_dump()


# ── Keywords ───────────────────────────────────────────────────────

@router.get("/keywords")
def get_keywords(category: str | None = Query(default=None)):
    from .keyword_service import get_all_keywords
    all_kw = get_all_keywords()
    if category:
        return {"category": category, "keywords": all_kw.get(category, [])}
    return all_kw


# ── Status ─────────────────────────────────────────────────────────

@router.get("/status")
def get_status():
    from . import pinterest_client

    conn = get_conn()
    generated = conn.execute("SELECT COUNT(*) as c FROM pins").fetchone()["c"]
    posted = conn.execute(
        "SELECT COUNT(*) as c FROM pins WHERE status = 'posted'"
    ).fetchone()["c"]
    scheduled = conn.execute(
        "SELECT COUNT(*) as c FROM pins WHERE status = 'queued'"
    ).fetchone()["c"]
    conn.close()

    return PinterestStatusResponse(
        configured=pinterest_client.is_configured(),
        has_token=bool(os.environ.get("PINTEREST_ACCESS_TOKEN")),
        pins_generated=generated,
        pins_posted=posted,
        pins_scheduled=scheduled,
    ).model_dump()


# ── App Phase ──────────────────────────────────────────────────────

@router.get("/app-phase")
def get_app_phase():
    from .app_phase import get_current_phase, get_app_link, get_burst_stats

    phase = get_current_phase()
    link = get_app_link()
    burst = get_burst_stats()

    return AppPhaseResponse(
        phase=phase.value,
        app_link=link,
        burst_total=burst["burst_total"],
        burst_released=burst["burst_released"],
    ).model_dump()


@router.post("/app-phase")
def update_app_phase(payload: AppPhaseUpdateRequest):
    from .app_phase import set_phase
    phase = set_phase(payload.phase)
    return {"phase": phase.value}


# ── Setup ─────────────────────────────────────────────────────────

@router.get("/setup/status")
def setup_status():
    from .setup_service import get_setup_status
    return get_setup_status()


@router.post("/setup/credentials")
def save_credentials(payload: SaveCredentialsRequest):
    from .setup_service import save_app_credentials, get_oauth_authorize_url
    save_app_credentials(payload.app_id, payload.app_secret)
    authorize_url = get_oauth_authorize_url(payload.app_id)
    return {"authorize_url": authorize_url}


@router.get("/setup/callback")
def oauth_callback(code: str = Query(default=None), error: str = Query(default=None)):
    if error or not code:
        return RedirectResponse(url="http://localhost:5173/?pinterest_setup=error")
    try:
        from .setup_service import exchange_code_for_tokens
        exchange_code_for_tokens(code)
        return RedirectResponse(url="http://localhost:5173/?pinterest_setup=success")
    except Exception:
        return RedirectResponse(url="http://localhost:5173/?pinterest_setup=error")


@router.post("/setup/create-boards")
def create_boards():
    from .setup_service import create_default_boards
    boards = create_default_boards()
    return {"boards": boards}


@router.post("/setup/refresh-token")
def refresh_token():
    from .setup_service import refresh_access_token
    data = refresh_access_token()
    return {"refreshed": True, "has_access_token": bool(data.get("access_token"))}


@router.post("/app-phase/generate-burst")
def generate_burst():
    from .pin_factory import generate_app_promo_pins

    burst_count = int(os.environ.get("APP_LAUNCH_BURST_PINS", "30"))
    pins = generate_app_promo_pins(count=burst_count)
    return {"items": [p.model_dump() for p in pins], "count": len(pins)}
