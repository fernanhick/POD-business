from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta

from .models import PinStatus, get_conn

logger = logging.getLogger("pinterest.scheduler")

# Holiday windows with surge multipliers
HOLIDAY_WINDOWS = [
    {"name": "Valentine's Day", "start": "02-01", "end": "02-14", "multiplier": 1.5},
    {"name": "Easter", "start": "03-20", "end": "04-01", "multiplier": 1.3},
    {"name": "Mother's Day", "start": "04-25", "end": "05-12", "multiplier": 1.4},
    {"name": "Father's Day", "start": "06-01", "end": "06-15", "multiplier": 1.4},
    {"name": "Back to School", "start": "07-15", "end": "09-01", "multiplier": 1.5},
    {"name": "Halloween", "start": "10-01", "end": "10-31", "multiplier": 1.3},
    {"name": "Black Friday", "start": "11-15", "end": "12-02", "multiplier": 2.0},
    {"name": "Christmas", "start": "12-01", "end": "12-25", "multiplier": 2.0},
    {"name": "New Year", "start": "12-26", "end": "01-05", "multiplier": 1.3},
    {"name": "Sneaker Day", "start": "10-01", "end": "10-07", "multiplier": 1.5},
]


def _get_pins_per_day() -> int:
    return int(os.environ.get("PINTEREST_PINS_PER_DAY", "5"))


def _get_post_times() -> list[str]:
    raw = os.environ.get("PINTEREST_POST_TIMES", "08:00,11:00,14:00,18:00,21:00")
    return [t.strip() for t in raw.split(",") if t.strip()]


def _get_holiday_multiplier() -> float:
    today = datetime.now().strftime("%m-%d")
    for h in HOLIDAY_WINDOWS:
        if h["start"] <= today <= h["end"]:
            return h["multiplier"]
    return 1.0


def add_pins_to_queue(pin_ids: list[str], start_from: str | None = None) -> int:
    if not pin_ids:
        return 0

    pins_per_day = _get_pins_per_day()
    post_times = _get_post_times()
    multiplier = _get_holiday_multiplier()
    effective_per_day = int(pins_per_day * multiplier)

    start_date = datetime.fromisoformat(start_from) if start_from else datetime.now()
    conn = get_conn()

    # Find the latest scheduled slot to continue from
    row = conn.execute(
        "SELECT MAX(scheduled_at) as last_slot FROM schedule_jobs WHERE status='pending'"
    ).fetchone()
    if row and row["last_slot"]:
        last_dt = datetime.fromisoformat(row["last_slot"])
        if last_dt > start_date:
            start_date = last_dt + timedelta(minutes=1)

    scheduled_count = 0
    day_offset = 0
    time_idx = 0

    for pin_id in pin_ids:
        if time_idx >= min(effective_per_day, len(post_times)):
            time_idx = 0
            day_offset += 1

        target_date = start_date + timedelta(days=day_offset)
        time_str = post_times[time_idx % len(post_times)]
        hour, minute = time_str.split(":")
        scheduled_dt = target_date.replace(
            hour=int(hour), minute=int(minute), second=0, microsecond=0
        )

        job_id = uuid.uuid4().hex
        conn.execute(
            "INSERT INTO schedule_jobs (id, pin_id, scheduled_at, status) VALUES (?, ?, ?, ?)",
            (job_id, pin_id, scheduled_dt.isoformat(), "pending"),
        )
        time_idx += 1
        scheduled_count += 1

        # Update pin status to queued
        conn.execute(
            "UPDATE pins SET status = ? WHERE id = ? AND status = ?",
            (PinStatus.QUEUED.value, pin_id, PinStatus.DRAFT.value),
        )

    conn.commit()
    conn.close()
    return scheduled_count


async def post_next_pin() -> dict | None:
    from . import pinterest_client

    if not pinterest_client.is_configured():
        logger.info("Pinterest not configured, skipping post")
        return None

    conn = get_conn()
    now = datetime.now().isoformat()

    # Get next pending job that's due
    job = conn.execute(
        """SELECT sj.*, p.image_path, p.title, p.description, p.board_id, p.link
           FROM schedule_jobs sj
           JOIN pins p ON sj.pin_id = p.id
           WHERE sj.status = 'pending' AND sj.scheduled_at <= ?
           ORDER BY sj.scheduled_at ASC LIMIT 1""",
        (now,),
    ).fetchone()

    if not job:
        conn.close()
        return None

    job_id = job["id"]
    pin_id = job["pin_id"]

    try:
        # Update status to posting
        conn.execute("UPDATE schedule_jobs SET status='posting', attempted_at=? WHERE id=?", (now, job_id))
        conn.execute("UPDATE pins SET status=? WHERE id=?", (PinStatus.POSTING.value, pin_id))
        conn.commit()

        # Create pin with inline image
        board_id = job["board_id"]
        if not board_id:
            raise ValueError("No board_id configured for this pin")

        pinterest_pin_id = await pinterest_client.create_pin(
            board_id=board_id,
            title=job["title"],
            description=job["description"],
            link=job["link"],
            image_path=job["image_path"],
        )

        # Success
        posted_at = datetime.now().isoformat()
        conn.execute("UPDATE schedule_jobs SET status='posted' WHERE id=?", (job_id,))
        conn.execute(
            "UPDATE pins SET status=?, pinterest_pin_id=?, posted_at=? WHERE id=?",
            (PinStatus.POSTED.value, pinterest_pin_id, posted_at, pin_id),
        )
        conn.commit()
        conn.close()
        return {"job_id": job_id, "pin_id": pin_id, "pinterest_pin_id": pinterest_pin_id}

    except Exception as exc:
        error_msg = str(exc)
        conn.execute("UPDATE schedule_jobs SET status='failed', error=? WHERE id=?", (error_msg, job_id))
        conn.execute("UPDATE pins SET status=? WHERE id=?", (PinStatus.FAILED.value, pin_id))
        conn.commit()
        conn.close()
        logger.error("Failed to post pin %s: %s", pin_id, error_msg)
        return {"job_id": job_id, "pin_id": pin_id, "error": error_msg}


async def sync_analytics() -> int:
    from . import pinterest_client

    if not pinterest_client.is_configured():
        return 0

    conn = get_conn()
    pins = conn.execute(
        "SELECT id, pinterest_pin_id FROM pins WHERE pinterest_pin_id IS NOT NULL"
    ).fetchall()

    updated = 0
    for pin in pins:
        try:
            metrics = await pinterest_client.get_pin_metrics(pin["pinterest_pin_id"])
            conn.execute(
                "UPDATE pins SET impressions=?, saves=?, clicks=?, updated_at=? WHERE id=?",
                (metrics["impressions"], metrics["saves"], metrics["clicks"],
                 datetime.now().isoformat(), pin["id"]),
            )
            updated += 1
        except Exception as exc:
            logger.warning("Failed to sync analytics for pin %s: %s", pin["id"], exc)

    conn.commit()
    conn.close()
    return updated


def get_schedule_queue(days: int = 14) -> list[dict]:
    conn = get_conn()
    cutoff = (datetime.now() + timedelta(days=days)).isoformat()
    rows = conn.execute(
        """SELECT sj.id, sj.pin_id, sj.scheduled_at, sj.status, sj.error,
                  p.title, p.pin_type, p.board_id, p.image_path, p.design_filename,
                  p.description, p.status as pin_status, p.keywords, p.created_at,
                  p.posted_at, p.impressions, p.saves, p.clicks
           FROM schedule_jobs sj
           JOIN pins p ON sj.pin_id = p.id
           WHERE sj.scheduled_at <= ?
           ORDER BY sj.scheduled_at ASC""",
        (cutoff,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_schedule_settings() -> dict:
    return {
        "pins_per_day": _get_pins_per_day(),
        "post_times": _get_post_times(),
        "timezone": os.environ.get("PINTEREST_TIMEZONE", "America/New_York"),
        "holiday_multiplier": _get_holiday_multiplier(),
    }
