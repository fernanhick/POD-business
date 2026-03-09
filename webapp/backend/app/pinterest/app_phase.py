from __future__ import annotations

import os

from .models import AppPhase, PinStatus, PinType, get_conn


def get_current_phase() -> AppPhase:
    conn = get_conn()
    row = conn.execute(
        "SELECT value FROM pinterest_settings WHERE key='app_phase'"
    ).fetchone()
    conn.close()
    if row:
        return AppPhase(row["value"])
    return AppPhase(os.environ.get("APP_PHASE", "pre_launch"))


def set_phase(new_phase: str) -> AppPhase:
    phase = AppPhase(new_phase)
    old_phase = get_current_phase()

    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO pinterest_settings (key, value) VALUES ('app_phase', ?)",
        (phase.value,),
    )
    conn.commit()
    conn.close()

    # Trigger launch burst if transitioning to launched
    if old_phase == AppPhase.PRE_LAUNCH and phase == AppPhase.LAUNCHED:
        _release_launch_burst()

    return phase


def get_app_link() -> str | None:
    phase = get_current_phase()
    if phase == AppPhase.PRE_LAUNCH:
        return os.environ.get("APP_EMAIL_CAPTURE_URL") or os.environ.get("APP_WEBSITE_URL") or None
    else:
        return os.environ.get("APP_STORE_URL") or os.environ.get("APP_WEBSITE_URL") or None


def get_app_cta(template_cta_pre: str, template_cta_post: str) -> str:
    phase = get_current_phase()
    return template_cta_pre if phase == AppPhase.PRE_LAUNCH else template_cta_post


def _release_launch_burst() -> int:
    from .scheduler import add_pins_to_queue

    conn = get_conn()
    draft_app_pins = conn.execute(
        "SELECT id FROM pins WHERE pin_type = ? AND status = ?",
        (PinType.APP_PROMO.value, PinStatus.DRAFT.value),
    ).fetchall()
    conn.close()

    pin_ids = [row["id"] for row in draft_app_pins]
    if pin_ids:
        return add_pins_to_queue(pin_ids)
    return 0


def get_burst_stats() -> dict:
    conn = get_conn()
    total = conn.execute(
        "SELECT COUNT(*) as c FROM pins WHERE pin_type = ?",
        (PinType.APP_PROMO.value,),
    ).fetchone()["c"]
    released = conn.execute(
        "SELECT COUNT(*) as c FROM pins WHERE pin_type = ? AND status != ?",
        (PinType.APP_PROMO.value, PinStatus.DRAFT.value),
    ).fetchone()["c"]
    conn.close()
    return {"burst_total": total, "burst_released": released}
