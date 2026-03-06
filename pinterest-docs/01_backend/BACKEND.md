# BACKEND.md
> Step 3 of 8 — Implement after DATA_MODELS.md is clear.
> Covers every backend file in webapp/backend/app/pinterest/
> and the exact 2-line change to the existing main.py.

---

## THE ONLY CHANGE TO main.py

Open `webapp/backend/app/main.py`. Add exactly these 2 lines.
Do not change anything else in that file.

```python
# ADD this import near the top, alongside any existing router imports:
from .pinterest import router as pinterest_router

# ADD this line after the existing app.include_router() calls (or app = FastAPI() block):
app.include_router(pinterest_router, prefix="/api/pinterest", tags=["pinterest"])
```

That's it. Every Pinterest route is now mounted under `/api/pinterest/`
with zero collision against existing routes.

---

## FILE: webapp/backend/app/pinterest/__init__.py

```python
from .router import router
__all__ = ["router"]
```

---

## FILE: webapp/backend/app/pinterest/models.py

Contains all Pydantic schemas and the DB initialization function.
Full definitions are in `00_start/DATA_MODELS.md` — copy them here.

Additionally add this DB init function:

```python
import sqlite3
import os
from pathlib import Path

def get_db_path() -> str:
    storage = os.getenv("PINTEREST_STORAGE_PATH", "./workspace/pinterest")
    Path(storage).mkdir(parents=True, exist_ok=True)
    return str(Path(storage) / "pinterest.db")

def init_db() -> None:
    """Create tables if they don't exist. Safe to call on every startup."""
    conn = sqlite3.connect(get_db_path())
    # Execute the CREATE TABLE IF NOT EXISTS statements from DATA_MODELS.md
    conn.close()

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn
```

---

## FILE: webapp/backend/app/pinterest/spreadsheet_reader.py

Reads `workspace/spreadsheets/` files. Read-only — never writes.

```python
import openpyxl
import os
from pathlib import Path
from typing import Optional
from .models import DesignOption

def _spreadsheets_path() -> Path:
    workspace = os.getenv("WORKSPACE_PATH", "./workspace")
    return Path(workspace) / "spreadsheets"

def _approved_images_path() -> Path:
    workspace = os.getenv("WORKSPACE_PATH", "./workspace")
    return Path(workspace) / "front_a_sneaker" / "approved"

def get_approved_designs() -> list[DesignOption]:
    """
    Read designs_front_a.xlsx, filter rows where Status == 'approved'.
    Cross-reference listings.xlsx to get product_url per design.
    Only return designs whose .png file exists in front_a_sneaker/approved/.
    """
    designs_path = _spreadsheets_path() / "designs_front_a.xlsx"
    listings_path = _spreadsheets_path() / "listings.xlsx"
    approved_dir = _approved_images_path()

    # Load product URLs from listings.xlsx keyed by filename
    product_urls: dict[str, str] = {}
    if listings_path.exists():
        wb = openpyxl.load_workbook(listings_path, read_only=True, data_only=True)
        ws = wb.active
        headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
        filename_col = headers.index("Filename")
        url_col = headers.index("Printify URL")
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[filename_col]:
                product_urls[row[filename_col]] = row[url_col] or ""
        wb.close()

    # Load approved designs from designs_front_a.xlsx
    results: list[DesignOption] = []
    if not designs_path.exists():
        return results

    wb = openpyxl.load_workbook(designs_path, read_only=True, data_only=True)
    ws = wb.active
    headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    title_col    = headers.index("Title")
    concept_col  = headers.index("Concept")
    status_col   = headers.index("Status")
    filename_col = headers.index("Filename")

    for row in ws.iter_rows(min_row=2, values_only=True):
        status   = row[status_col]
        filename = row[filename_col]
        if str(status).lower() != "approved" or not filename:
            continue
        image_file = approved_dir / filename
        if not image_file.exists():
            continue
        results.append(DesignOption(
            filename=filename,
            title=row[title_col] or filename,
            concept=row[concept_col] or "",
            product_url=product_urls.get(filename),
            image_url=f"/api/pinterest/designs/image?filename={filename}",
        ))
    wb.close()
    return results

def get_design_by_filename(filename: str) -> Optional[DesignOption]:
    """Return a single DesignOption or None if not found/not approved."""
    designs = get_approved_designs()
    return next((d for d in designs if d.filename == filename), None)
```

---

## FILE: webapp/backend/app/pinterest/keyword_service.py

```python
import json
import random
from pathlib import Path

_KEYWORDS: dict = {}

def load_keywords() -> None:
    """Called once at startup. Loads keywords.json into memory."""
    global _KEYWORDS
    kw_path = Path(__file__).parent.parent.parent.parent.parent / "workspace" / "pinterest" / "keywords.json"
    # Fallback: try relative to workspace env var
    import os
    workspace = os.getenv("WORKSPACE_PATH", "./workspace")
    kw_path = Path(workspace) / "pinterest" / "keywords.json"
    if kw_path.exists():
        with open(kw_path) as f:
            _KEYWORDS = json.load(f)

def select_keywords(
    category_names: list[str],
    count: int = 5,
    exclude: list[str] | None = None,
) -> list[str]:
    """
    Pick `count` keywords from the given categories.
    Primary keyword (index 0 of return) is from category_names[0].
    Rotates to avoid repetition. Excludes any in `exclude` list.
    """
    if not _KEYWORDS:
        load_keywords()

    exclude_set = set(exclude or [])
    pool: list[str] = []
    for cat in category_names:
        pool.extend(_KEYWORDS.get("categories", {}).get(cat, []))

    available = [k for k in pool if k not in exclude_set]
    if not available:
        available = pool  # reset if all excluded

    selected = random.sample(available, min(count, len(available)))
    # Always add one long-tail keyword if pin is product type
    long_tail = _KEYWORDS.get("long_tail", [])
    if long_tail:
        selected.append(random.choice([k for k in long_tail if k not in exclude_set] or long_tail))

    return selected[:count]

def get_all_keywords() -> dict:
    """Return the full keyword database. Used by /api/pinterest/keywords route."""
    if not _KEYWORDS:
        load_keywords()
    return _KEYWORDS
```

---

## FILE: webapp/backend/app/pinterest/pin_factory.py

Generates the 1000×1500px pin graphics using Pillow.

```python
import uuid
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime, timezone
from .models import PinResponse, PinStatus, PinType, get_conn
from .keyword_service import select_keywords
from .spreadsheet_reader import get_design_by_filename

# Canvas size — Pinterest standard
PIN_W, PIN_H = 1000, 1500

# Brand colors
COLOR_BLACK  = (26, 26, 26)
COLOR_ORANGE = (232, 80, 10)
COLOR_WHITE  = (255, 255, 255)
COLOR_GRAY   = (85, 85, 85)
COLOR_LIGHT  = (245, 245, 245)

def _load_templates() -> list[dict]:
    workspace = os.getenv("WORKSPACE_PATH", "./workspace")
    path = Path(workspace) / "pinterest" / "pin_templates.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []

def _pins_output_dir() -> Path:
    storage = os.getenv("PINTEREST_STORAGE_PATH", "./workspace/pinterest")
    p = Path(storage) / "pins"
    p.mkdir(parents=True, exist_ok=True)
    return p

def _approved_image_path(filename: str) -> Path:
    workspace = os.getenv("WORKSPACE_PATH", "./workspace")
    return Path(workspace) / "front_a_sneaker" / "approved" / filename

def build_pin_image(design_filename: str, template: dict) -> str:
    """
    Composite a 1000x1500 pin image.
    Returns absolute path to the saved PNG.
    Layout:
      - Top zone (0–200px): headline text
      - Middle zone (200–1200px): design image centered with padding
      - Bottom zone (1200–1500px): brand/CTA footer
    """
    img = Image.new("RGB", (PIN_W, PIN_H), COLOR_BLACK)
    draw = ImageDraw.Draw(img)
    bg_color = _resolve_background(template.get("background", "dark"))

    # Fill background
    img.paste(bg_color if isinstance(bg_color, tuple) else COLOR_BLACK, [0, 0, PIN_W, PIN_H])

    # Place design image in middle zone
    design_path = _approved_image_path(design_filename)
    if design_path.exists():
        design_img = Image.open(design_path).convert("RGBA")
        design_img.thumbnail((PIN_W - 80, 1000), Image.LANCZOS)
        x = (PIN_W - design_img.width) // 2
        y = 200 + (1000 - design_img.height) // 2
        img.paste(design_img, (x, y), design_img)

    # Headline (top zone) — template provides the text pattern
    # Font loading: use default PIL font as fallback if system fonts unavailable
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
    except OSError:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    headline = template.get("headline_placeholder", "SNEAKER CULTURE")
    draw.text((PIN_W // 2, 100), headline, fill=COLOR_WHITE, font=font_large, anchor="mm")

    # Footer zone
    footer_bg = COLOR_ORANGE if template.get("footer_accent") else COLOR_BLACK
    draw.rectangle([0, 1200, PIN_W, PIN_H], fill=footer_bg)
    draw.text((PIN_W // 2, 1350), "SOLE THEORY", fill=COLOR_WHITE, font=font_large, anchor="mm")
    draw.text((PIN_W // 2, 1430), "streetwear for sneaker collectors", fill=COLOR_LIGHT, font=font_small, anchor="mm")

    # Save
    pin_id = str(uuid.uuid4())
    output_path = _pins_output_dir() / f"{pin_id}_pin.png"
    img.save(str(output_path), "PNG")
    return str(output_path)

def _resolve_background(bg_name: str) -> tuple | str:
    mapping = {
        "dark":   COLOR_BLACK,
        "light":  COLOR_LIGHT,
        "orange": COLOR_ORANGE,
    }
    return mapping.get(bg_name, COLOR_BLACK)

def build_pin_title(design_title: str, primary_keyword: str) -> str:
    """Max 100 chars. Primary keyword first, then design title."""
    base = f"{primary_keyword.title()} | {design_title}"
    return base[:100]

def build_pin_description(design_concept: str, keywords: list[str], cta: str) -> str:
    """Max 500 chars. Reads naturally, 3–5 keywords woven in."""
    kw_str = ", ".join(f"#{k.replace(' ', '')}" for k in keywords[:3])
    desc = (
        f"{keywords[0].title()} — {design_concept}. "
        f"Designed for the culture, built for collectors. "
        f"{cta} {kw_str}"
    )
    return desc[:500]

def generate_pins_for_design(
    design_filename: str,
    template_ids: list[str] | None = None,
) -> list[PinResponse]:
    """
    Main entry point. Generates pin graphics + DB records for one design.
    Returns list of PinResponse objects.
    """
    design = get_design_by_filename(design_filename)
    if not design:
        raise ValueError(f"Design not found or not approved: {design_filename}")

    templates = _load_templates()
    if template_ids:
        templates = [t for t in templates if t["id"] in template_ids]

    results: list[PinResponse] = []
    conn = get_conn()

    for template in templates:
        pin_id = str(uuid.uuid4())
        categories = template.get("keyword_categories", ["sneaker_culture"])
        keywords = select_keywords(categories, count=5)
        primary_kw = keywords[0]

        title       = build_pin_title(design.title, primary_kw)
        description = build_pin_description(design.concept, keywords, template.get("cta", ""))
        board_id    = _resolve_board(template.get("pin_type", "lifestyle"))
        board_name  = _resolve_board_name(board_id)
        image_path  = build_pin_image(design_filename, template)

        conn.execute("""
            INSERT INTO pins
              (id, design_filename, design_title, design_concept, product_url,
               template_id, template_name, pin_type, title, description,
               keywords, board_id, board_name, image_path, status, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            pin_id, design.filename, design.title, design.concept, design.product_url,
            template["id"], template["name"], template.get("pin_type", "lifestyle"),
            title, description, json.dumps(keywords),
            board_id, board_name, image_path, PinStatus.DRAFT,
            datetime.now(timezone.utc).isoformat(),
        ))
        conn.commit()

        results.append(PinResponse(
            id=pin_id,
            design_filename=design.filename,
            design_title=design.title,
            template_id=template["id"],
            template_name=template["name"],
            pin_type=PinType(template.get("pin_type", "lifestyle")),
            title=title,
            description=description,
            keywords=keywords,
            board_id=board_id,
            board_name=board_name,
            image_url=f"/api/pinterest/pins/image?id={pin_id}",
            pinterest_pin_id=None,
            status=PinStatus.DRAFT,
            error_message=None,
            created_at=datetime.now(timezone.utc).isoformat(),
            scheduled_at=None,
            posted_at=None,
        ))

    conn.close()
    return results

def _resolve_board(pin_type: str) -> str:
    """Map pin type to Pinterest board ID from environment."""
    mapping = {
        "product":   os.getenv("PINTEREST_BOARD_SNEAKER_CULTURE", ""),
        "lifestyle": os.getenv("PINTEREST_BOARD_OUTFIT_IDEAS", ""),
        "quote":     os.getenv("PINTEREST_BOARD_STREETWEAR", ""),
        "list":      os.getenv("PINTEREST_BOARD_GIFTS", ""),
        "mood":      os.getenv("PINTEREST_BOARD_ROOM_DECOR", ""),
    }
    return mapping.get(pin_type, os.getenv("PINTEREST_BOARD_SNEAKER_CULTURE", ""))

def _resolve_board_name(board_id: str) -> str:
    board_map = {
        os.getenv("PINTEREST_BOARD_SNEAKER_CULTURE", ""): "Sneakerhead Streetwear",
        os.getenv("PINTEREST_BOARD_OUTFIT_IDEAS", ""):    "Sneaker Outfit Ideas",
        os.getenv("PINTEREST_BOARD_STREETWEAR", ""):      "Streetwear Aesthetic",
        os.getenv("PINTEREST_BOARD_GIFTS", ""):           "Sneaker Gifts",
        os.getenv("PINTEREST_BOARD_ROOM_DECOR", ""):      "Sneaker Room Decor",
    }
    return board_map.get(board_id, "Sneakerhead Streetwear")
```

---

## FILE: webapp/backend/app/pinterest/pinterest_client.py

```python
import httpx
import os
from pathlib import Path

PINTEREST_API = "https://api.pinterest.com/v5"

def _headers() -> dict:
    token = os.getenv("PINTEREST_ACCESS_TOKEN", "")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

async def upload_media(image_path: str) -> str:
    """
    Register image with Pinterest media upload API.
    Returns media_id string.
    Pinterest requires this before pin creation.
    """
    async with httpx.AsyncClient() as client:
        # Step 1: register upload
        r = await client.post(
            f"{PINTEREST_API}/media",
            headers=_headers(),
            json={"media_type": "image"}
        )
        r.raise_for_status()
        data = r.json()
        upload_url = data["upload_url"]
        media_id   = data["media_id"]
        upload_params = data.get("upload_parameters", {})

        # Step 2: PUT the actual image file
        with open(image_path, "rb") as f:
            image_data = f.read()
        await client.put(upload_url, content=image_data,
                         headers={"Content-Type": "image/png", **upload_params})

        return media_id

async def create_pin(
    board_id: str,
    title: str,
    description: str,
    link: str,
    media_id: str,
) -> str:
    """Create a pin on Pinterest. Returns pinterest_pin_id."""
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{PINTEREST_API}/pins",
            headers=_headers(),
            json={
                "board_id": board_id,
                "title": title[:100],
                "description": description[:500],
                "link": link or "",
                "media_source": {
                    "source_type": "media_id",
                    "media_id": media_id,
                }
            }
        )
        r.raise_for_status()
        return r.json()["id"]

async def get_pin_metrics(pinterest_pin_id: str) -> dict:
    """
    GET /v5/pins/{id}/analytics
    Returns: {impressions, saves, outbound_clicks}
    """
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{PINTEREST_API}/pins/{pinterest_pin_id}/analytics",
            headers=_headers(),
            params={"metric_types": "IMPRESSION,SAVE,OUTBOUND_CLICK", "app_types": "ALL"}
        )
        if r.status_code == 200:
            data = r.json()
            return {
                "impressions":      data.get("all", {}).get("daily_metrics", [{}])[-1].get("IMPRESSION", 0),
                "saves":            data.get("all", {}).get("daily_metrics", [{}])[-1].get("SAVE", 0),
                "outbound_clicks":  data.get("all", {}).get("daily_metrics", [{}])[-1].get("OUTBOUND_CLICK", 0),
            }
        return {"impressions": 0, "saves": 0, "outbound_clicks": 0}

async def get_boards() -> list[dict]:
    """Return user's boards as [{id, name}]. Used by Settings page."""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{PINTEREST_API}/boards", headers=_headers())
        if r.status_code == 200:
            return [{"id": b["id"], "name": b["name"]} for b in r.json().get("items", [])]
        return []

async def refresh_access_token() -> str:
    """Use PINTEREST_REFRESH_TOKEN to get a new access token."""
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.pinterest.com/v5/oauth/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": os.getenv("PINTEREST_REFRESH_TOKEN", ""),
            },
            auth=(os.getenv("PINTEREST_APP_ID", ""), os.getenv("PINTEREST_APP_SECRET", ""))
        )
        r.raise_for_status()
        return r.json()["access_token"]
```

---

## FILE: webapp/backend/app/pinterest/scheduler.py

```python
import os
import uuid
import logging
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from .models import get_conn, PinStatus
from .pinterest_client import upload_media, create_pin

logger = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None

def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler

def start(app_scheduler: AsyncIOScheduler) -> None:
    """Register all jobs. Call from main.py startup event."""
    tz = os.getenv("PINTEREST_TIMEZONE", "America/New_York")

    post_times = os.getenv("PINTEREST_POST_TIMES", "08:00,11:00,14:00,18:00,21:00").split(",")
    for pt in post_times:
        hour, minute = pt.strip().split(":")
        app_scheduler.add_job(
            post_next_pin,
            CronTrigger(hour=int(hour), minute=int(minute), timezone=tz),
            id=f"pinterest_post_{pt}",
            replace_existing=True,
            max_instances=1,
        )

    app_scheduler.add_job(
        sync_analytics,
        CronTrigger(hour=6, minute=0, timezone=tz),
        id="pinterest_sync_analytics",
        replace_existing=True,
    )
    logger.info("Pinterest scheduler jobs registered.")

async def post_next_pin() -> None:
    """
    Pull the next pending schedule_job whose scheduled_at <= now.
    Upload image, create Pinterest pin, update DB.
    """
    if os.getenv("PINTEREST_ACTIVE", "true").lower() != "true":
        return

    conn = get_conn()
    now = datetime.now(timezone.utc).isoformat()

    row = conn.execute("""
        SELECT sj.id as job_id, sj.pin_id, p.image_path, p.board_id,
               p.title, p.description, p.product_url
        FROM schedule_jobs sj
        JOIN pins p ON p.id = sj.pin_id
        WHERE sj.status = 'pending' AND sj.scheduled_at <= ?
        ORDER BY sj.scheduled_at ASC
        LIMIT 1
    """, (now,)).fetchone()

    if not row:
        conn.close()
        return

    job_id  = row["job_id"]
    pin_id  = row["pin_id"]

    conn.execute("UPDATE schedule_jobs SET status='running' WHERE id=?", (job_id,))
    conn.commit()

    try:
        media_id = await upload_media(row["image_path"])
        pinterest_pin_id = await create_pin(
            board_id=row["board_id"],
            title=row["title"],
            description=row["description"],
            link=row["product_url"] or "",
            media_id=media_id,
        )
        posted_at = datetime.now(timezone.utc).isoformat()
        conn.execute("UPDATE pins SET status=?, pinterest_pin_id=?, posted_at=? WHERE id=?",
                     (PinStatus.POSTED, pinterest_pin_id, posted_at, pin_id))
        conn.execute("UPDATE schedule_jobs SET status='done', ran_at=? WHERE id=?",
                     (posted_at, job_id))
        logger.info(f"Pin posted: {pin_id} → Pinterest ID {pinterest_pin_id}")
    except Exception as e:
        logger.error(f"Pin post failed: {pin_id} — {e}")
        conn.execute("UPDATE pins SET status=?, error_message=? WHERE id=?",
                     (PinStatus.FAILED, str(e), pin_id))
        conn.execute("UPDATE schedule_jobs SET status='failed', error=? WHERE id=?",
                     (str(e), job_id))

    conn.commit()
    conn.close()

async def sync_analytics() -> None:
    """Pull metrics for all posted pins. Runs daily at 6 AM."""
    from .pinterest_client import get_pin_metrics
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, pinterest_pin_id FROM pins WHERE status='posted' AND pinterest_pin_id IS NOT NULL"
    ).fetchall()

    for row in rows:
        try:
            metrics = await get_pin_metrics(row["pinterest_pin_id"])
            conn.execute("""
                UPDATE pins SET impressions=?, saves=?, outbound_clicks=? WHERE id=?
            """, (metrics["impressions"], metrics["saves"], metrics["outbound_clicks"], row["id"]))
        except Exception as e:
            logger.warning(f"Analytics sync failed for pin {row['id']}: {e}")

    conn.commit()
    conn.close()

def add_pins_to_queue(pin_ids: list[str], start_from: str | None = None) -> list[dict]:
    """
    Distribute pins across future posting slots.
    Rules: max pins_per_day per day, spread across configured post_times.
    Returns list of created schedule_job dicts.
    """
    pins_per_day = int(os.getenv("PINTEREST_PINS_PER_DAY", "5"))
    post_times   = os.getenv("PINTEREST_POST_TIMES", "08:00,11:00,14:00,18:00,21:00").split(",")
    tz_name      = os.getenv("PINTEREST_TIMEZONE", "America/New_York")

    conn = get_conn()

    # Find the next available slot
    start_dt = datetime.fromisoformat(start_from) if start_from else datetime.now(timezone.utc)
    jobs = []

    for pin_id in pin_ids:
        slot_dt = _next_available_slot(conn, start_dt, pins_per_day, post_times)
        job_id  = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO schedule_jobs (id, pin_id, scheduled_at, status)
            VALUES (?,?,?,?)
        """, (job_id, pin_id, slot_dt.isoformat(), "pending"))
        conn.execute("UPDATE pins SET status='scheduled', scheduled_at=? WHERE id=?",
                     (slot_dt.isoformat(), pin_id))
        jobs.append({"job_id": job_id, "pin_id": pin_id, "scheduled_at": slot_dt.isoformat()})
        start_dt = slot_dt + timedelta(minutes=1)  # advance cursor

    conn.commit()
    conn.close()
    return jobs

def _next_available_slot(conn, from_dt: datetime, max_per_day: int, post_times: list[str]) -> datetime:
    """Find next post_time slot that hasn't hit max_per_day pins."""
    check_dt = from_dt
    for _ in range(60):  # look up to 60 days ahead
        day_str = check_dt.strftime("%Y-%m-%d")
        count = conn.execute(
            "SELECT COUNT(*) FROM schedule_jobs WHERE scheduled_at LIKE ? AND status != 'failed'",
            (f"{day_str}%",)
        ).fetchone()[0]

        if count < max_per_day:
            # Find the next available time slot on this day
            for pt in sorted(post_times):
                hour, minute = pt.strip().split(":")
                slot = check_dt.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
                if slot > datetime.now(timezone.utc):
                    slot_taken = conn.execute(
                        "SELECT COUNT(*) FROM schedule_jobs WHERE scheduled_at=? AND status != 'failed'",
                        (slot.isoformat(),)
                    ).fetchone()[0]
                    if not slot_taken:
                        return slot
        check_dt = (check_dt + timedelta(days=1)).replace(hour=0, minute=0)

    return from_dt + timedelta(days=1)  # hard fallback
```

---

## FILE: webapp/backend/app/pinterest/router.py

All `/api/pinterest/*` routes. No overlap with existing routes.

```python
import os
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from datetime import datetime, timezone

from .models import (
    GeneratePinsRequest, SchedulePinsRequest, ScheduleSettingsRequest,
    PinResponse, ScheduleQueueResponse, ScheduleQueueItem,
    AnalyticsSummary, PinterestMetrics, PinterestStatusResponse,
    DesignOption, get_conn, init_db, PinStatus
)
from .spreadsheet_reader import get_approved_designs, get_design_by_filename
from .pin_factory import generate_pins_for_design
from .keyword_service import get_all_keywords, load_keywords
from .scheduler import add_pins_to_queue, post_next_pin
from .pinterest_client import get_boards, refresh_access_token

router = APIRouter()

@router.on_event("startup")
async def on_startup():
    init_db()
    load_keywords()

# ── Approved Designs (read from workspace) ────────────────────────────────────

@router.get("/designs", response_model=list[DesignOption])
async def list_approved_designs():
    """List all approved sneaker designs available for pin generation."""
    return get_approved_designs()

@router.get("/designs/image")
async def get_design_image(filename: str):
    """Serve approved design PNG from workspace/front_a_sneaker/approved/."""
    workspace = os.getenv("WORKSPACE_PATH", "./workspace")
    path = Path(workspace) / "front_a_sneaker" / "approved" / filename
    if not path.exists():
        raise HTTPException(404, f"Design image not found: {filename}")
    return FileResponse(str(path), media_type="image/png")

# ── Pin Generation ────────────────────────────────────────────────────────────

@router.post("/pins/generate", response_model=list[PinResponse])
async def generate_pins(req: GeneratePinsRequest, background_tasks: BackgroundTasks):
    """Generate pin graphics for an approved design. Runs synchronously (Pillow is fast)."""
    design = get_design_by_filename(req.design_filename)
    if not design:
        raise HTTPException(404, f"Approved design not found: {req.design_filename}")
    return generate_pins_for_design(req.design_filename, req.template_ids)

@router.get("/pins", response_model=list[PinResponse])
async def list_pins(
    design_filename: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 50,
):
    conn = get_conn()
    query = "SELECT * FROM pins WHERE 1=1"
    params: list = []
    if design_filename:
        query += " AND design_filename=?"; params.append(design_filename)
    if status:
        query += " AND status=?"; params.append(status)
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params += [limit, skip]
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [_row_to_pin_response(r) for r in rows]

@router.get("/pins/image")
async def get_pin_image(id: str):
    """Serve a generated pin graphic PNG."""
    conn = get_conn()
    row = conn.execute("SELECT image_path FROM pins WHERE id=?", (id,)).fetchone()
    conn.close()
    if not row or not row["image_path"] or not Path(row["image_path"]).exists():
        raise HTTPException(404, "Pin image not found")
    return FileResponse(row["image_path"], media_type="image/png")

# ── Scheduling ────────────────────────────────────────────────────────────────

@router.post("/schedule")
async def schedule_pins(req: SchedulePinsRequest):
    """Add selected pins to the posting queue."""
    jobs = add_pins_to_queue(req.pin_ids, req.start_from)
    return {"scheduled": len(jobs), "jobs": jobs}

@router.get("/schedule/queue", response_model=ScheduleQueueResponse)
async def get_queue(days: int = 14):
    conn = get_conn()
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    rows = conn.execute("""
        SELECT sj.id as job_id, sj.pin_id, sj.scheduled_at, sj.status,
               p.title, p.board_name, p.image_path
        FROM schedule_jobs sj JOIN pins p ON p.id = sj.pin_id
        WHERE sj.scheduled_at <= ? AND sj.status = 'pending'
        ORDER BY sj.scheduled_at ASC
    """, (cutoff,)).fetchall()
    conn.close()

    items = [ScheduleQueueItem(
        job_id=r["job_id"], pin_id=r["pin_id"],
        pin_title=r["title"],
        pin_image_url=f"/api/pinterest/pins/image?id={r['pin_id']}",
        board_name=r["board_name"],
        scheduled_at=r["scheduled_at"],
        status=r["status"],
    ) for r in rows]

    return ScheduleQueueResponse(
        queue=items,
        total_queued=len(items),
        next_post_at=items[0].scheduled_at if items else None,
    )

@router.post("/schedule/run")
async def run_now():
    """Manually trigger the next pending pin post."""
    await post_next_pin()
    return {"triggered": True}

@router.get("/schedule/settings")
async def get_schedule_settings():
    return {
        "pins_per_day": int(os.getenv("PINTEREST_PINS_PER_DAY", "5")),
        "post_times":   os.getenv("PINTEREST_POST_TIMES", "08:00,11:00,14:00,18:00,21:00").split(","),
        "timezone":     os.getenv("PINTEREST_TIMEZONE", "America/New_York"),
        "active":       os.getenv("PINTEREST_ACTIVE", "true").lower() == "true",
    }

# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get("/analytics", response_model=AnalyticsSummary)
async def get_analytics():
    conn = get_conn()
    total_gen  = conn.execute("SELECT COUNT(*) FROM pins").fetchone()[0]
    total_post = conn.execute("SELECT COUNT(*) FROM pins WHERE status='posted'").fetchone()[0]
    total_sched= conn.execute("SELECT COUNT(*) FROM pins WHERE status='scheduled'").fetchone()[0]

    posted_rows = conn.execute("""
        SELECT id, title, pinterest_pin_id,
               COALESCE(impressions,0) as impressions,
               COALESCE(saves,0) as saves,
               COALESCE(outbound_clicks,0) as outbound_clicks
        FROM pins WHERE status='posted'
    """).fetchall()
    conn.close()

    total_imp    = sum(r["impressions"] for r in posted_rows)
    total_saves  = sum(r["saves"] for r in posted_rows)
    total_clicks = sum(r["outbound_clicks"] for r in posted_rows)
    avg_ctr      = (total_clicks / total_imp * 100) if total_imp > 0 else 0.0

    def to_metric(r) -> PinterestMetrics:
        imp = r["impressions"] or 1
        return PinterestMetrics(
            pin_id=r["id"], pinterest_pin_id=r["pinterest_pin_id"] or "",
            title=r["title"], impressions=r["impressions"], saves=r["saves"],
            outbound_clicks=r["outbound_clicks"],
            ctr_pct=round(r["outbound_clicks"] / imp * 100, 2),
        )

    metrics = [to_metric(r) for r in posted_rows]
    top_pins = sorted(metrics, key=lambda m: m.outbound_clicks, reverse=True)[:10]
    candidates = [m for m in metrics if m.ctr_pct >= avg_ctr * 3]

    return AnalyticsSummary(
        total_pins_generated=total_gen, total_pins_posted=total_post,
        total_pins_scheduled=total_sched,
        total_impressions=total_imp, total_saves=total_saves,
        total_clicks=total_clicks, avg_ctr_pct=round(avg_ctr, 2),
        top_pins=top_pins, scaling_candidates=candidates,
    )

# ── Keywords ──────────────────────────────────────────────────────────────────

@router.get("/keywords")
async def get_keywords(category: str | None = None):
    db = get_all_keywords()
    if category:
        return {"keywords": db.get("categories", {}).get(category, []), "category": category}
    return db

# ── Pinterest Account / Auth ──────────────────────────────────────────────────

@router.get("/status", response_model=PinterestStatusResponse)
async def pinterest_status():
    token = os.getenv("PINTEREST_ACCESS_TOKEN", "")
    if not token:
        return PinterestStatusResponse(connected=False, account_name=None, boards=None)
    boards = await get_boards()
    return PinterestStatusResponse(connected=bool(boards), account_name=None, boards=boards)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _row_to_pin_response(r) -> PinResponse:
    return PinResponse(
        id=r["id"], design_filename=r["design_filename"], design_title=r["design_title"],
        template_id=r["template_id"], template_name=r["template_name"],
        pin_type=r["pin_type"], title=r["title"], description=r["description"],
        keywords=json.loads(r["keywords"]) if r["keywords"] else [],
        board_id=r["board_id"], board_name=r["board_name"],
        image_url=f"/api/pinterest/pins/image?id={r['id']}",
        pinterest_pin_id=r["pinterest_pin_id"], status=r["status"],
        error_message=r["error_message"], created_at=r["created_at"],
        scheduled_at=r["scheduled_at"], posted_at=r["posted_at"],
    )
```

---

## PYTHON DEPENDENCIES TO ADD

Add these lines to `webapp/backend/requirements.txt`:

```
apscheduler>=3.10.0
httpx>=0.27.0
openpyxl>=3.1.0
Pillow>=10.0.0
```

These are likely already partially installed. Check before adding duplicates.

---

## FILE: webapp/backend/app/pinterest/app_phase.py

New service file. Manages the mobile app promotion phase and launch burst logic.
The phase is stored in `pinterest_settings` DB table (key = `app_phase`)
so it survives restarts and is editable from the portal without touching `.env`.

```python
import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from .models import AppPhase, AppPhaseResponse, get_conn

logger = logging.getLogger(__name__)

# ── Phase read/write ──────────────────────────────────────────────────────────

def get_current_phase() -> AppPhase:
    """Read phase from DB. Falls back to APP_PHASE env var, then pre_launch."""
    conn = get_conn()
    row = conn.execute(
        "SELECT value FROM pinterest_settings WHERE key='app_phase'"
    ).fetchone()
    conn.close()
    if row:
        return AppPhase(row["value"])
    # Fall back to env var on first run
    return AppPhase(os.getenv("APP_PHASE", "pre_launch"))

def set_phase(new_phase: AppPhase) -> None:
    """Write phase to DB. Triggers launch burst if switching to launched."""
    conn = get_conn()
    conn.execute("""
        INSERT INTO pinterest_settings (key, value) VALUES ('app_phase', ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (new_phase.value,))
    conn.commit()
    conn.close()

    if new_phase == AppPhase.LAUNCHED:
        _release_launch_burst()

# ── Phase-aware link resolution ───────────────────────────────────────────────

def get_app_link() -> str:
    """
    Returns the correct URL for app-promotion pins based on current phase.
    pre_launch → email capture page
    launched   → App Store URL (falls back to Play Store if App Store not set)
    Called by pin_factory.py when building app_promo pins.
    """
    phase = get_current_phase()
    if phase == AppPhase.PRE_LAUNCH:
        return (
            os.getenv("APP_EMAIL_CAPTURE_URL") or
            os.getenv("APP_WEBSITE_URL") or
            ""
        )
    else:
        return (
            os.getenv("APP_STORE_URL") or
            os.getenv("PLAY_STORE_URL") or
            ""
        )

def get_app_cta(template_cta_pre: str, template_cta_post: str) -> str:
    """Return the phase-appropriate CTA string from a template."""
    phase = get_current_phase()
    return template_cta_pre if phase == AppPhase.PRE_LAUNCH else template_cta_post

# ── Launch burst ──────────────────────────────────────────────────────────────

def get_burst_status() -> dict:
    """Return how many burst pins exist and whether the burst is ready."""
    burst_target = int(os.getenv("APP_LAUNCH_BURST_PINS", "30"))
    conn = get_conn()
    count = conn.execute(
        "SELECT COUNT(*) FROM pins WHERE pin_type='app_promo' AND status='draft'"
    ).fetchone()[0]
    conn.close()
    return {
        "launch_burst_total": burst_target,
        "launch_burst_generated": count,
        "launch_burst_ready": count >= burst_target,
    }

def _release_launch_burst() -> None:
    """
    Called automatically when phase switches to launched.
    Moves all draft app_promo pins into the scheduling queue immediately.
    They are distributed across the next 7 days at 3 extra pins/day on top of normal schedule.
    """
    from .scheduler import add_pins_to_queue
    conn = get_conn()
    rows = conn.execute(
        "SELECT id FROM pins WHERE pin_type='app_promo' AND status='draft' ORDER BY created_at ASC"
    ).fetchall()
    conn.close()

    pin_ids = [r["id"] for r in rows]
    if not pin_ids:
        logger.warning("Launch burst triggered but no draft app_promo pins found. Generate them first.")
        return

    jobs = add_pins_to_queue(pin_ids, start_from=None)
    logger.info(f"Launch burst released: {len(jobs)} app_promo pins scheduled.")

# ── Status summary ────────────────────────────────────────────────────────────

def get_phase_response() -> AppPhaseResponse:
    burst = get_burst_status()
    return AppPhaseResponse(
        phase=get_current_phase(),
        app_website_url=os.getenv("APP_WEBSITE_URL"),
        app_email_capture_url=os.getenv("APP_EMAIL_CAPTURE_URL"),
        app_store_url=os.getenv("APP_STORE_URL"),
        play_store_url=os.getenv("PLAY_STORE_URL"),
        **burst,
    )
```

---

## ROUTER ADDITIONS FOR APP PHASE

Add these routes to the bottom of `router.py` (before the `_row_to_pin_response` helper):

```python
# ── App Phase (mobile app promotion) ─────────────────────────────────────────
from .app_phase import get_phase_response, set_phase, get_app_link
from .models import AppPhaseUpdateRequest, AppPhase

@router.get("/app-phase", response_model=AppPhaseResponse)
async def get_app_phase():
    """Return current app promotion phase and burst readiness status."""
    return get_phase_response()

@router.post("/app-phase")
async def update_app_phase(req: AppPhaseUpdateRequest):
    """
    Switch between pre_launch and launched.
    When switching to launched, automatically releases the draft launch burst pins
    into the posting queue. This is the activation button in the portal.
    """
    set_phase(req.phase)
    return get_phase_response()

@router.post("/app-phase/generate-burst")
async def generate_launch_burst(background_tasks: BackgroundTasks):
    """
    Pre-generate the launch burst pin set while still in pre_launch phase.
    Generates APP_LAUNCH_BURST_PINS app_promo pins and holds them as draft.
    Call this 1–2 weeks before launch so they are ready to release instantly.
    """
    from .pin_factory import generate_app_promo_pins
    burst_target = int(os.getenv("APP_LAUNCH_BURST_PINS", "30"))
    background_tasks.add_task(generate_app_promo_pins, count=burst_target, phase="pre_launch")
    return {"message": f"Generating {burst_target} launch burst pins in background."}
```

---

## ADDITION TO pin_factory.py — App Promo Pin Generation

Add this function to the existing `pin_factory.py` file.
It generates app-promotion pins using templates from `app_pin_templates.json`
(defined in `APP_PHASE.md`). The link and CTA automatically reflect the current phase.

```python
def generate_app_promo_pins(count: int = 30, phase: str = "pre_launch") -> list:
    """
    Generate `count` app-promotion pin graphics.
    Uses app_pin_templates.json. Links and CTAs are phase-aware.
    All pins created with status=draft and pin_type=app_promo.
    Called as a BackgroundTask — returns nothing, writes directly to DB.
    """
    from .app_phase import get_app_link, get_app_cta

    workspace = os.getenv("WORKSPACE_PATH", "./workspace")
    templates_path = Path(workspace) / "pinterest" / "app_pin_templates.json"
    if not templates_path.exists():
        logger.error("app_pin_templates.json not found. See APP_PHASE.md to create it.")
        return []

    with open(templates_path) as f:
        templates = json.load(f)

    conn = get_conn()
    results = []
    for i in range(count):
        template = templates[i % len(templates)]  # cycle through templates
        pin_id    = str(uuid.uuid4())
        keywords  = select_keywords(["sneaker_culture", "outfits_style"], count=4)
        link      = get_app_link()
        cta       = get_app_cta(template["cta_pre_launch"], template["cta_launched"])
        title     = template["title_pre_launch"] if phase == "pre_launch" else template["title_launched"]
        desc      = f"{template['description']} {cta}"[:500]
        image_path = build_pin_image_for_app(template)  # see below

        conn.execute("""
            INSERT INTO pins
              (id, design_filename, design_title, design_concept, product_url,
               template_id, template_name, pin_type, title, description,
               keywords, board_id, board_name, image_path, status, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            pin_id, "app_promo", template["name"], template["description"], link,
            template["id"], template["name"], "app_promo",
            title[:100], desc,
            json.dumps(keywords),
            os.getenv("PINTEREST_BOARD_SNEAKER_CULTURE", ""),
            "Sneakerhead Streetwear",
            image_path, "draft",
            datetime.now(timezone.utc).isoformat(),
        ))
        results.append(pin_id)

    conn.commit()
    conn.close()
    logger.info(f"Generated {len(results)} app_promo pins (phase={phase})")
    return results

def build_pin_image_for_app(template: dict) -> str:
    """
    Build a 1000x1500 pin graphic for app promotion.
    Uses the same Pillow compositor as build_pin_image() but with app-specific layout.
    Returns absolute path to saved PNG.
    """
    img   = Image.new("RGB", (PIN_W, PIN_H), COLOR_BLACK)
    draw  = ImageDraw.Draw(img)

    try:
        font_xl = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64)
        font_lg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
        font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
    except OSError:
        font_xl = font_lg = font_sm = ImageFont.load_default()

    # Top zone — app name / headline
    draw.text((PIN_W // 2, 120), template.get("headline", "TRACK YOUR COLLECTION"),
              fill=COLOR_WHITE, font=font_xl, anchor="mm")

    # Middle zone — app feature description
    draw.rectangle([60, 240, PIN_W - 60, 1180], outline=COLOR_ORANGE, width=3)
    draw.text((PIN_W // 2, 710), template.get("feature_text", "Sneaker Portfolio Manager"),
              fill=COLOR_ORANGE, font=font_lg, anchor="mm")

    # Bottom zone — CTA
    draw.rectangle([0, 1200, PIN_W, PIN_H], fill=COLOR_ORANGE)
    draw.text((PIN_W // 2, 1320), template.get("cta_visual", "JOIN THE WAITLIST"),
              fill=COLOR_WHITE, font=font_lg, anchor="mm")
    draw.text((PIN_W // 2, 1420), "sneaker portfolio manager",
              fill=COLOR_WHITE, font=font_sm, anchor="mm")

    pin_id      = str(uuid.uuid4())
    output_path = _pins_output_dir() / f"{pin_id}_app_pin.png"
    img.save(str(output_path), "PNG")
    return str(output_path)
```
