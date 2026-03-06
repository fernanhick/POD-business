# DATA_MODELS.md
> Step 2 of 8 — Read before writing any backend or frontend code.
> Defines every data shape used across the entire Pinterest module.
> All field names here are canonical — use them exactly as written.

---

## SQLite DATABASE

Location: `workspace/pinterest/pinterest.db`
Created automatically on first backend startup using the schema below.
This is a separate database from `webapp/backend/app/app_state.db` — do not touch that file.

---

## DATABASE SCHEMA (create in models.py using sqlite3 or SQLAlchemy)

```sql
-- Pins table: one row per generated pin graphic
CREATE TABLE IF NOT EXISTS pins (
    id              TEXT PRIMARY KEY,       -- UUID, e.g. "a3f2b1c4-..."
    design_filename TEXT NOT NULL,          -- source file, e.g. "rotation_standard_001.png"
    design_title    TEXT NOT NULL,          -- from designs_front_a.xlsx "Title" column
    design_concept  TEXT NOT NULL,          -- from designs_front_a.xlsx "Concept" column
    product_url     TEXT,                   -- from listings.xlsx — the Printify product link
    template_id     TEXT NOT NULL,          -- e.g. "template_01"
    template_name   TEXT NOT NULL,          -- e.g. "The Bold Statement"
    pin_type        TEXT NOT NULL,          -- "product"|"lifestyle"|"quote"|"list"|"mood"
    title           TEXT NOT NULL,          -- Pinterest pin title, max 100 chars
    description     TEXT NOT NULL,          -- Pinterest pin description, max 500 chars
    keywords        TEXT NOT NULL,          -- JSON array of strings
    board_id        TEXT NOT NULL,          -- Pinterest board ID from env
    board_name      TEXT NOT NULL,          -- human label e.g. "Sneakerhead Streetwear"
    image_path      TEXT,                   -- absolute path to workspace/pinterest/pins/*.png
    pinterest_pin_id TEXT,                  -- returned by Pinterest API after posting
    status          TEXT NOT NULL DEFAULT 'draft',  -- "draft"|"scheduled"|"posted"|"failed"
    error_message   TEXT,
    created_at      TEXT NOT NULL,          -- ISO 8601
    scheduled_at    TEXT,                   -- ISO 8601, null until scheduled
    posted_at       TEXT                    -- ISO 8601, null until posted
);

-- Schedule jobs table: one row per posting slot
CREATE TABLE IF NOT EXISTS schedule_jobs (
    id           TEXT PRIMARY KEY,          -- UUID
    pin_id       TEXT NOT NULL REFERENCES pins(id),
    scheduled_at TEXT NOT NULL,             -- ISO 8601 datetime for posting
    status       TEXT NOT NULL DEFAULT 'pending',  -- "pending"|"running"|"done"|"failed"
    error        TEXT,
    ran_at       TEXT                       -- ISO 8601, set when job executes
);

-- Settings table: key-value store for Pinterest configuration
CREATE TABLE IF NOT EXISTS pinterest_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

---

## PYDANTIC SCHEMAS (webapp/backend/app/pinterest/models.py)

```python
from pydantic import BaseModel
from typing import Optional
from enum import Enum

class PinStatus(str, Enum):
    DRAFT     = "draft"
    SCHEDULED = "scheduled"
    POSTED    = "posted"
    FAILED    = "failed"

class PinType(str, Enum):
    PRODUCT   = "product"
    LIFESTYLE = "lifestyle"
    QUOTE     = "quote"
    LIST      = "list"
    MOOD      = "mood"
    APP_PROMO = "app_promo"    # mobile app promotion pins — behavior controlled by APP_PHASE env var

class AppPhase(str, Enum):
    PRE_LAUNCH = "pre_launch"  # pins link to website + email capture
    LAUNCHED   = "launched"    # pins link to App Store / Google Play

# ── Request schemas (frontend → backend) ──────────────────────────────────────

class GeneratePinsRequest(BaseModel):
    design_filename: str          # e.g. "rotation_standard_001.png"
    template_ids: Optional[list[str]] = None   # None = generate all 20 templates
    board_assignments: Optional[dict[str, str]] = None  # {template_id: board_id} overrides

class SchedulePinsRequest(BaseModel):
    pin_ids: list[str]            # UUIDs of pins to schedule
    start_from: Optional[str] = None  # ISO 8601 date, None = next available slot

class ScheduleSettingsRequest(BaseModel):
    pins_per_day: int = 5
    post_times: list[str] = ["08:00", "11:00", "14:00", "18:00", "21:00"]
    timezone: str = "America/New_York"
    active: bool = True

class PinterestAuthRequest(BaseModel):
    code: str                     # OAuth authorization code from Pinterest callback

# ── Response schemas (backend → frontend) ─────────────────────────────────────

class DesignOption(BaseModel):
    """One approved design available for pin generation."""
    filename: str                 # "rotation_standard_001.png"
    title: str                    # from designs_front_a.xlsx
    concept: str                  # from designs_front_a.xlsx
    product_url: Optional[str]    # from listings.xlsx — may be None if not yet listed
    image_url: str                # served via /api/pinterest/designs/image?filename=...

class PinResponse(BaseModel):
    id: str
    design_filename: str
    design_title: str
    template_id: str
    template_name: str
    pin_type: PinType
    title: str
    description: str
    keywords: list[str]
    board_id: str
    board_name: str
    image_url: Optional[str]      # served via /api/pinterest/pins/image?id=...
    pinterest_pin_id: Optional[str]
    status: PinStatus
    error_message: Optional[str]
    created_at: str
    scheduled_at: Optional[str]
    posted_at: Optional[str]

class ScheduleQueueItem(BaseModel):
    job_id: str
    pin_id: str
    pin_title: str
    pin_image_url: Optional[str]
    board_name: str
    scheduled_at: str
    status: str

class ScheduleQueueResponse(BaseModel):
    queue: list[ScheduleQueueItem]
    total_queued: int
    next_post_at: Optional[str]

class PinterestMetrics(BaseModel):
    pin_id: str
    pinterest_pin_id: str
    title: str
    impressions: int
    saves: int
    outbound_clicks: int
    ctr_pct: float                # outbound_clicks / impressions * 100

class AnalyticsSummary(BaseModel):
    total_pins_generated: int
    total_pins_posted: int
    total_pins_scheduled: int
    total_impressions: int
    total_saves: int
    total_clicks: int
    avg_ctr_pct: float
    top_pins: list[PinterestMetrics]
    scaling_candidates: list[PinterestMetrics]   # pins with CTR >= 3x average

class PinterestStatusResponse(BaseModel):
    connected: bool
    account_name: Optional[str]
    boards: Optional[list[dict]]  # [{id, name}] fetched from Pinterest API

class AppPhaseResponse(BaseModel):
    """Current state of the mobile app promotion phase."""
    phase: AppPhase                        # "pre_launch" or "launched"
    app_website_url: Optional[str]         # preview site — active in pre_launch
    app_email_capture_url: Optional[str]   # email signup page — active in pre_launch
    app_store_url: Optional[str]           # App Store link — active when launched
    play_store_url: Optional[str]          # Google Play link — active when launched
    launch_burst_total: int                # APP_LAUNCH_BURST_PINS env value
    launch_burst_generated: int            # how many burst pins exist in DB (status=draft, pin_type=app_promo)
    launch_burst_ready: bool               # True when launch_burst_generated >= launch_burst_total

class AppPhaseUpdateRequest(BaseModel):
    """Sent by the portal when the founder flips the phase toggle."""
    phase: AppPhase
    # When switching to "launched", the scheduler immediately releases
    # all draft app_promo pins into the posting queue.
    # This happens automatically — no extra field needed.
```

---

## SPREADSHEET COLUMN MAPPING

The spreadsheet reader must use these exact column names.
If the actual column names in the xlsx differ, map them here and update this doc.

### workspace/spreadsheets/designs_front_a.xlsx

| Column used | Mapped to |
|---|---|
| `Title` | `design_title` |
| `Concept` | `design_concept` |
| `Status` | filter: only read rows where Status == "approved" |
| `Filename` | `design_filename` — must match the .png filename in front_a_sneaker/approved/ |

### workspace/spreadsheets/listings.xlsx

| Column used | Mapped to |
|---|---|
| `Filename` | join key — match to design_filename |
| `Printify URL` | `product_url` — the store link each pin points to |

> If column names in the actual xlsx files differ from above, do not change the xlsx.
> Change only the column name strings in `spreadsheet_reader.py`.
