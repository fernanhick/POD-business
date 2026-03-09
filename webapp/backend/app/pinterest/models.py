from __future__ import annotations

import enum
import sqlite3
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


# ── Enums ──────────────────────────────────────────────────────────

class PinStatus(str, enum.Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    POSTING = "posting"
    POSTED = "posted"
    FAILED = "failed"


class PinType(str, enum.Enum):
    LIFESTYLE = "lifestyle"
    QUOTE = "quote"
    LIST = "list"
    MOOD = "mood"
    PRODUCT = "product"
    APP_PROMO = "app_promo"


class AppPhase(str, enum.Enum):
    PRE_LAUNCH = "pre_launch"
    LAUNCHED = "launched"


# ── Database ───────────────────────────────────────────────────────

def get_db_path() -> Path:
    base = Path(__file__).resolve().parents[4]
    return base / "workspace" / "pinterest" / "pinterest.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS pins (
            id TEXT PRIMARY KEY,
            design_filename TEXT NOT NULL,
            template_id TEXT,
            pin_type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            board_id TEXT,
            image_path TEXT NOT NULL,
            pinterest_pin_id TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            impressions INTEGER DEFAULT 0,
            saves INTEGER DEFAULT 0,
            clicks INTEGER DEFAULT 0,
            link TEXT,
            keywords TEXT,
            created_at TEXT NOT NULL,
            posted_at TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS schedule_jobs (
            id TEXT PRIMARY KEY,
            pin_id TEXT NOT NULL,
            scheduled_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            attempted_at TEXT,
            error TEXT,
            FOREIGN KEY (pin_id) REFERENCES pins(id)
        );

        CREATE TABLE IF NOT EXISTS pinterest_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


# ── Pydantic Request Models ────────────────────────────────────────

class GeneratePinsRequest(BaseModel):
    design_filename: str
    template_ids: Optional[list[str]] = None


class SchedulePinsRequest(BaseModel):
    pin_ids: list[str]
    start_from: Optional[str] = None


class ScheduleSettingsRequest(BaseModel):
    pins_per_day: Optional[int] = None
    post_times: Optional[list[str]] = None
    timezone: Optional[str] = None


class AppPhaseUpdateRequest(BaseModel):
    phase: str


class SaveCredentialsRequest(BaseModel):
    app_id: str
    app_secret: str


# ── Pydantic Response Models ──────────────────────────────────────

class DesignOption(BaseModel):
    filename: str
    name: Optional[str] = None
    design_id: Optional[str] = None
    phrase: Optional[str] = None
    style: Optional[str] = None
    status: Optional[str] = None
    product_url: Optional[str] = None
    image_path: Optional[str] = None


class PinResponse(BaseModel):
    id: str
    design_filename: str
    template_id: Optional[str] = None
    pin_type: str
    title: str
    description: str
    board_id: Optional[str] = None
    image_path: str
    status: str
    link: Optional[str] = None
    keywords: Optional[str] = None
    created_at: str
    posted_at: Optional[str] = None
    impressions: int = 0
    saves: int = 0
    clicks: int = 0


class ScheduleQueueItem(BaseModel):
    id: str
    pin_id: str
    scheduled_at: str
    status: str
    pin: Optional[PinResponse] = None


class ScheduleQueueResponse(BaseModel):
    items: list[ScheduleQueueItem]
    total: int


class PinterestMetrics(BaseModel):
    impressions: int = 0
    saves: int = 0
    clicks: int = 0
    ctr: float = 0.0


class AnalyticsSummary(BaseModel):
    total_pins: int = 0
    posted_pins: int = 0
    scheduled_pins: int = 0
    draft_pins: int = 0
    metrics: PinterestMetrics = PinterestMetrics()
    top_pins: list[PinResponse] = []
    scaling_candidates: list[PinResponse] = []


class PinterestStatusResponse(BaseModel):
    configured: bool
    has_token: bool
    pins_generated: int
    pins_posted: int
    pins_scheduled: int


class AppPhaseResponse(BaseModel):
    phase: str
    app_link: Optional[str] = None
    burst_total: int = 0
    burst_released: int = 0
