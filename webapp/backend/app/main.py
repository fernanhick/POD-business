from __future__ import annotations

import csv
import io
import json
import os
import random
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from openpyxl import load_workbook

BASE_DIR = Path(__file__).resolve().parents[3]
WORKSPACE_DIR = BASE_DIR / "workspace"
SPREADSHEETS_DIR = WORKSPACE_DIR / "spreadsheets"
LOGS_DIR = WORKSPACE_DIR / "logs"
DB_PATH = BASE_DIR / "webapp" / "backend" / "app" / "app_state.db"

FRONT_CONFIG = {
    "sneaker": {
        "code": "A",
        "design_folder": WORKSPACE_DIR / "front_a_sneaker" / "designs",
        "approved_folder": WORKSPACE_DIR / "front_a_sneaker" / "approved",
        "rejected_folder": WORKSPACE_DIR / "front_a_sneaker" / "rejected",
        "spreadsheet": SPREADSHEETS_DIR / "designs_front_a.xlsx",
        "phrase_col": "Slogan / Typography",
    },
    "general": {
        "code": "B",
        "design_folder": WORKSPACE_DIR / "front_b_general" / "designs",
        "approved_folder": WORKSPACE_DIR / "front_b_general" / "approved",
        "rejected_folder": WORKSPACE_DIR / "front_b_general" / "rejected",
        "spreadsheet": SPREADSHEETS_DIR / "designs_front_b.xlsx",
        "phrase_col": "Phrase / Concept",
    },
}

FINANCIALS_FILE = SPREADSHEETS_DIR / "financials.xlsx"
TM_LOG_FILE = SPREADSHEETS_DIR / "trademark_log.xlsx"


app = FastAPI(title="POD Business Local API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerationRequest(BaseModel):
    mode: Literal["single", "batch"]
    designType: Literal["general", "sneaker"]
    generationStyle: Literal["random", "detailed"] = "detailed"
    randomVisualMode: Literal["mixed", "text_only", "text_plus_image"] = "mixed"
    dropId: str | None = None
    phrase: str | None = None
    niche: str | None = None
    subNiche: str | None = None
    style: str | None = None
    render: Literal["ideogram", "leonardo", "hf", "huggingface"] | None = None
    skipApi: bool = False


class ApprovalRequest(BaseModel):
    designType: Literal["general", "sneaker"]
    filename: str
    approved: bool
    notes: str | None = None


class ExpenseCreate(BaseModel):
    date: str
    front: str = Field(description="A, B, or BOTH")
    category: str
    description: str
    amount: float
    taxDeductible: Literal["Yes", "No"] = "Yes"
    receipt: Literal["Yes", "No"] = "No"
    notes: str = ""


class ExpenseUpdate(ExpenseCreate):
    expenseId: str


def _unique_values_from_sheet(file_path: Path, sheet_name: str, column_name: str) -> list[str]:
    if not file_path.exists():
        return []
    wb = load_workbook(file_path)
    ws = wb[sheet_name]
    headers = _header_map(ws)
    column = headers.get(column_name)
    values: set[str] = set()
    if column:
        for row in range(3, ws.max_row + 1):
            value = ws.cell(row=row, column=column).value
            if value:
                values.add(str(value).strip())
    wb.close()
    return sorted([v for v in values if v])


def _get_drop_ids() -> list[str]:
    drops_dir = WORKSPACE_DIR / "front_a_sneaker" / "drops"
    drop_ids: set[str] = set()
    if drops_dir.exists():
        for file_path in drops_dir.glob("*.json"):
            drop_ids.add(file_path.stem)
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict) and payload.get("drop_id"):
                    drop_ids.add(str(payload["drop_id"]).strip())
            except Exception:
                continue
    if not drop_ids:
        drop_ids.add("DROP-01")
    return sorted(drop_ids)


def _get_phrase_bank() -> list[str]:
    phrase_file = SPREADSHEETS_DIR / "niches_front_b.xlsx"
    return _unique_values_from_sheet(phrase_file, "Phrase Bank", "Phrase")


def _build_random_phrase_samples(count: int) -> list[str]:
    samples = _get_phrase_bank()
    token_pool: list[str] = []
    for text in samples:
        token_pool.extend(re.findall(r"[A-Za-z]{3,}", text.lower()))

    token_pool = list({token for token in token_pool if len(token) >= 3})
    if not token_pool:
        token_pool = [
            "collectors",
            "street",
            "culture",
            "hustle",
            "vibes",
            "energy",
            "legacy",
            "daily",
            "club",
            "archive",
        ]

    templates = [
        "{a} {b}",
        "{a} {b} {c}",
        "{a} & {b}",
        "{a} over {b}",
        "{a} never {b}",
    ]

    phrases: list[str] = []
    for _ in range(max(1, count)):
        a, b, c = random.sample(token_pool, k=3)
        phrase = random.choice(templates).format(a=a.title(), b=b.title(), c=c.title())
        phrases.append(phrase)
    return phrases


def _build_generation_options() -> dict[str, Any]:
    niche_file = SPREADSHEETS_DIR / "niches_front_b.xlsx"
    design_b_file = SPREADSHEETS_DIR / "designs_front_b.xlsx"

    niches = _unique_values_from_sheet(niche_file, "Niches", "Niche")
    sub_niches = _unique_values_from_sheet(niche_file, "Niches", "Sub-Niche")
    styles = _unique_values_from_sheet(design_b_file, "Designs", "Style")
    phrases = _get_phrase_bank()
    if not phrases:
        phrases = _unique_values_from_sheet(design_b_file, "Designs", "Phrase / Concept")
    if not phrases:
        phrases = _build_random_phrase_samples(50)

    return {
        "sneaker": {
            "dropIds": _get_drop_ids(),
        },
        "general": {
            "niches": niches,
            "subNiches": sub_niches,
            "styles": styles or ["minimalist line art"],
            "phrases": phrases[:200],
        },
        "renderers": ["hf", "ideogram", "leonardo"],
    }


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                design_type TEXT NOT NULL,
                mode TEXT NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                output TEXT
            )
            """
        )
        con.commit()


@contextmanager
def _db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()


def _list_pngs(path: Path) -> list[str]:
    if not path.exists():
        return []
    return sorted([p.name for p in path.iterdir() if p.suffix.lower() == ".png"])


def _header_map(ws) -> dict[str, int]:
    return {
        (cell.value or "").strip(): idx
        for idx, cell in enumerate(ws[2], start=1)
        if isinstance(cell.value, str)
    }


def _read_design_rows(design_type: str) -> list[dict[str, Any]]:
    cfg = FRONT_CONFIG[design_type]
    wb = load_workbook(cfg["spreadsheet"])
    ws = wb["Designs"]
    headers = _header_map(ws)

    rows: list[dict[str, Any]] = []
    for row in range(3, ws.max_row + 1):
        filename = ws.cell(row=row, column=headers.get("Filename", 2)).value
        if not filename:
            continue
        row_data = {
            "designId": ws.cell(row=row, column=headers.get("Design ID", 1)).value,
            "filename": filename,
            "designType": design_type,
            "name": ws.cell(row=row, column=headers.get("Design Name", headers.get(cfg["phrase_col"], 5))).value,
            "phrase": ws.cell(row=row, column=headers.get(cfg["phrase_col"], 5)).value,
            "style": ws.cell(row=row, column=headers.get("Style", 6)).value,
            "dateCreated": ws.cell(row=row, column=headers.get("Date Created", 7)).value,
            "ipRisk": ws.cell(row=row, column=headers.get("IP Risk", 11)).value,
            "approved": ws.cell(row=row, column=headers.get("Approved?", 12)).value,
            "status": ws.cell(row=row, column=headers.get("Status", ws.max_column)).value,
            "rowNumber": row,
        }
        rows.append(row_data)

    wb.close()
    return rows


def _get_design_location(design_type: str, filename: str) -> tuple[Path | None, str | None]:
    cfg = FRONT_CONFIG[design_type]
    locations = {
        "generated": cfg["design_folder"],
        "approved": cfg["approved_folder"],
        "rejected": cfg["rejected_folder"],
    }
    for state, folder in locations.items():
        path = folder / filename
        if path.exists():
            return path, state
    return None, None


def _update_design_sheet_approval(design_type: str, filename: str, approved: bool) -> str | None:
    cfg = FRONT_CONFIG[design_type]
    wb = load_workbook(cfg["spreadsheet"])
    ws = wb["Designs"]
    headers = _header_map(ws)
    filename_col = headers.get("Filename", 2)
    approved_col = headers.get("Approved?")
    status_col = headers.get("Status")
    design_id_col = headers.get("Design ID", 1)

    design_id = None
    for row in range(3, ws.max_row + 1):
        value = ws.cell(row=row, column=filename_col).value
        if str(value or "").strip() == filename.strip():
            if approved_col:
                ws.cell(row=row, column=approved_col, value="YES" if approved else "REVIEW")
            if status_col:
                ws.cell(row=row, column=status_col, value="Approved" if approved else "Rejected")
            design_id = ws.cell(row=row, column=design_id_col).value
            break

    wb.save(cfg["spreadsheet"])
    wb.close()
    return design_id


def _update_tm_log(design_id: str | None, front_code: str, approved: bool, notes: str | None) -> None:
    wb = load_workbook(TM_LOG_FILE)
    ws = wb["Clearance Log"]
    headers = _header_map(ws)
    decision_col = headers.get("Decision")
    notes_col = headers.get("Notes")
    front_col = headers.get("Front")
    design_col = headers.get("Design ID")

    if not decision_col:
        wb.close()
        return

    decision = "APPROVED" if approved else "MANUAL REVIEW"
    for row in range(3, ws.max_row + 1):
        same_front = str(ws.cell(row=row, column=front_col).value or "").strip().upper() == front_code
        if not same_front:
            continue
        if design_id:
            same_design = str(ws.cell(row=row, column=design_col).value or "").strip() == str(design_id).strip()
            if not same_design:
                continue
        ws.cell(row=row, column=decision_col, value=decision)
        if notes and notes_col:
            ws.cell(row=row, column=notes_col, value=notes)

    wb.save(TM_LOG_FILE)
    wb.close()


def _update_logs(filename: str, approved: bool, notes: str | None) -> int:
    updated = 0
    for log_path in LOGS_DIR.glob("*.json"):
        try:
            data = json.loads(log_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        changed = False
        records = data if isinstance(data, list) else [data]
        for record in records:
            if str(record.get("filename", "")).strip() == filename.strip():
                record["approved"] = approved
                record["status"] = "Approved" if approved else "Rejected"
                if notes:
                    record["tm_notes"] = notes
                changed = True

        if changed:
            log_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            updated += 1

    return updated


def _next_expense_id(ws) -> str:
    max_num = 0
    for row in range(3, ws.max_row + 1):
        val = ws.cell(row=row, column=1).value
        if not val:
            continue
        text = str(val)
        if text.startswith("EXP-"):
            try:
                max_num = max(max_num, int(text.split("-")[-1]))
            except ValueError:
                continue
    return f"EXP-{max_num + 1:04d}"


def _read_expenses() -> list[dict[str, Any]]:
    wb = load_workbook(FINANCIALS_FILE)
    ws = wb["Expenses"]
    headers = _header_map(ws)

    out: list[dict[str, Any]] = []
    for row in range(3, ws.max_row + 1):
        expense_id = ws.cell(row=row, column=headers.get("Expense ID", 1)).value
        if not expense_id:
            continue
        out.append(
            {
                "expenseId": expense_id,
                "date": ws.cell(row=row, column=headers.get("Date", 2)).value,
                "front": ws.cell(row=row, column=headers.get("Front", 3)).value,
                "category": ws.cell(row=row, column=headers.get("Category", 4)).value,
                "description": ws.cell(row=row, column=headers.get("Description", 5)).value,
                "amount": ws.cell(row=row, column=headers.get("Amount ($)", 6)).value,
                "taxDeductible": ws.cell(row=row, column=headers.get("Tax Deductible?", 7)).value,
                "receipt": ws.cell(row=row, column=headers.get("Receipt?", 8)).value,
                "notes": ws.cell(row=row, column=headers.get("Notes", 9)).value,
            }
        )
    wb.close()
    return out


def _upsert_expense(payload: ExpenseCreate | ExpenseUpdate, update: bool = False) -> str:
    wb = load_workbook(FINANCIALS_FILE)
    ws = wb["Expenses"]
    headers = _header_map(ws)

    if update:
        row_target = None
        for row in range(3, ws.max_row + 1):
            if str(ws.cell(row=row, column=headers.get("Expense ID", 1)).value) == str(payload.expenseId):
                row_target = row
                break
        if row_target is None:
            wb.close()
            raise HTTPException(status_code=404, detail="Expense not found")
        expense_id = payload.expenseId
    else:
        row_target = ws.max_row + 1
        expense_id = _next_expense_id(ws)

    ws.cell(row=row_target, column=headers.get("Expense ID", 1), value=expense_id)
    ws.cell(row=row_target, column=headers.get("Date", 2), value=payload.date)
    ws.cell(row=row_target, column=headers.get("Front", 3), value=payload.front)
    ws.cell(row=row_target, column=headers.get("Category", 4), value=payload.category)
    ws.cell(row=row_target, column=headers.get("Description", 5), value=payload.description)
    ws.cell(row=row_target, column=headers.get("Amount ($)", 6), value=payload.amount)
    ws.cell(row=row_target, column=headers.get("Tax Deductible?", 7), value=payload.taxDeductible)
    ws.cell(row=row_target, column=headers.get("Receipt?", 8), value=payload.receipt)
    ws.cell(row=row_target, column=headers.get("Notes", 9), value=payload.notes)

    wb.save(FINANCIALS_FILE)
    wb.close()
    return expense_id


def _delete_expense(expense_id: str) -> None:
    wb = load_workbook(FINANCIALS_FILE)
    ws = wb["Expenses"]
    headers = _header_map(ws)
    target = None
    for row in range(3, ws.max_row + 1):
        if str(ws.cell(row=row, column=headers.get("Expense ID", 1)).value) == expense_id:
            target = row
            break
    if target is None:
        wb.close()
        raise HTTPException(status_code=404, detail="Expense not found")

    ws.delete_rows(target, 1)
    wb.save(FINANCIALS_FILE)
    wb.close()


def _insert_job(job_id: str, payload: GenerationRequest) -> None:
    with _db() as con:
        con.execute(
            "INSERT INTO jobs (id, kind, design_type, mode, status, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (job_id, "generation", payload.designType, payload.mode, "queued", payload.model_dump_json(), _now_iso()),
        )
        con.commit()


def _update_job(job_id: str, **fields: Any) -> None:
    if not fields:
        return
    keys = list(fields.keys())
    set_clause = ", ".join([f"{k}=?" for k in keys])
    values = [fields[k] for k in keys]
    with _db() as con:
        con.execute(f"UPDATE jobs SET {set_clause} WHERE id=?", (*values, job_id))
        con.commit()


def _latest_log_for_front(front_code: str) -> Path | None:
    pattern = f"front_{front_code.lower()}*"
    logs = sorted(LOGS_DIR.glob(f"{pattern}.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return logs[0] if logs else None


def _run_generation_job(job_id: str, payload: GenerationRequest) -> None:
    _update_job(job_id, status="running", started_at=_now_iso())
    cfg = FRONT_CONFIG[payload.designType]
    front_code = cfg["code"]

    command = [
        sys.executable,
        str(WORKSPACE_DIR / "design_pipeline.py"),
        "batch",
        "--front",
        front_code,
    ]

    temp_phrase_file: Path | None = None
    try:
        selected_render = payload.render

        if payload.generationStyle == "random":
            if payload.randomVisualMode == "text_only":
                selected_render = None
            elif payload.randomVisualMode == "text_plus_image":
                selected_render = selected_render or "hf"
            else:
                selected_render = selected_render or random.choice([None, "hf"])

            if front_code == "A":
                drop_ids = _get_drop_ids()
                command.extend(["--drop", random.choice(drop_ids)])
            else:
                phrase_count = 1 if payload.mode == "single" else 8
                phrases = _build_random_phrase_samples(phrase_count)
                temp_phrase_file = Path(tempfile.gettempdir()) / f"pod_phrase_{uuid.uuid4().hex}.csv"
                temp_phrase_file.write_text("\n".join(phrases) + "\n", encoding="utf-8")
                command.extend(["--phrases", str(temp_phrase_file)])

                opts = _build_generation_options().get("general", {})
                command.extend(["--niche", random.choice(opts.get("niches") or ["General"])])
                command.extend(["--sub-niche", random.choice(opts.get("subNiches") or ["General"])])
                command.extend(["--style", random.choice(opts.get("styles") or ["minimalist line art"])])

        else:
            if front_code == "A":
                if payload.dropId:
                    command.extend(["--drop", payload.dropId])
            else:
                if payload.mode == "single":
                    if not payload.phrase:
                        raise ValueError("Single general generation requires phrase")
                    temp_phrase_file = Path(tempfile.gettempdir()) / f"pod_phrase_{uuid.uuid4().hex}.csv"
                    temp_phrase_file.write_text(payload.phrase + "\n", encoding="utf-8")
                    command.extend(["--phrases", str(temp_phrase_file)])
                elif payload.phrase:
                    temp_phrase_file = Path(tempfile.gettempdir()) / f"pod_phrase_{uuid.uuid4().hex}.csv"
                    temp_phrase_file.write_text(payload.phrase + "\n", encoding="utf-8")
                    command.extend(["--phrases", str(temp_phrase_file)])

                if payload.niche:
                    command.extend(["--niche", payload.niche])
                if payload.subNiche:
                    command.extend(["--sub-niche", payload.subNiche])
                if payload.style:
                    command.extend(["--style", payload.style])

        if selected_render:
            command.extend(["--render", selected_render])
        if payload.skipApi:
            command.append("--skip-api")

        run = subprocess.run(
            command,
            cwd=str(WORKSPACE_DIR),
            capture_output=True,
            text=True,
        )
        output = (run.stdout or "") + "\n" + (run.stderr or "")

        if run.returncode != 0:
            _update_job(job_id, status="failed", finished_at=_now_iso(), output=output)
            return

        latest_log = _latest_log_for_front(front_code)
        if latest_log:
            sync = subprocess.run(
                [
                    sys.executable,
                    str(WORKSPACE_DIR / "update_workbooks.py"),
                    "--log",
                    str(latest_log),
                    "--front",
                    front_code,
                ],
                cwd=str(WORKSPACE_DIR),
                capture_output=True,
                text=True,
            )
            output += "\n\n--- Workbook Sync ---\n"
            output += (sync.stdout or "") + "\n" + (sync.stderr or "")

        _update_job(job_id, status="success", finished_at=_now_iso(), output=output)
    except Exception as exc:
        _update_job(job_id, status="failed", finished_at=_now_iso(), output=str(exc))
    finally:
        if temp_phrase_file and temp_phrase_file.exists():
            temp_phrase_file.unlink(missing_ok=True)


@app.on_event("startup")
def startup_event() -> None:
    _ensure_db()


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "workspace": str(WORKSPACE_DIR),
        "timestamp": _now_iso(),
    }


@app.get("/api/dashboard/summary")
def dashboard_summary() -> dict[str, Any]:
    summary: dict[str, Any] = {"designs": {}, "expenses": {}, "jobs": {}}

    for design_type, cfg in FRONT_CONFIG.items():
        generated = len(_list_pngs(cfg["design_folder"]))
        approved = len(_list_pngs(cfg["approved_folder"]))
        rejected = len(_list_pngs(cfg["rejected_folder"]))
        summary["designs"][design_type] = {
            "generated": generated,
            "approved": approved,
            "rejected": rejected,
            "total": generated + approved + rejected,
        }

    expenses = _read_expenses()
    total_expense = sum(float(item.get("amount") or 0) for item in expenses)
    summary["expenses"] = {"count": len(expenses), "total": round(total_expense, 2)}

    with _db() as con:
        rows = con.execute("SELECT status, COUNT(*) as c FROM jobs GROUP BY status").fetchall()
        summary["jobs"] = {row["status"]: row["c"] for row in rows}

    return summary


@app.get("/api/designs")
def list_designs(
    designType: Literal["general", "sneaker"] | None = Query(default=None),
    status: Literal["generated", "approved", "rejected", "all"] = Query(default="all"),
) -> dict[str, Any]:
    types = [designType] if designType else ["sneaker", "general"]
    all_rows: list[dict[str, Any]] = []

    for dt in types:
        rows = _read_design_rows(dt)
        for row in rows:
            source_path, location = _get_design_location(dt, row["filename"])
            row["location"] = location or "missing"
            row["path"] = str(source_path.resolve()) if source_path else None
            all_rows.append(row)

    if status != "all":
        all_rows = [item for item in all_rows if item.get("location") == status]

    all_rows.sort(key=lambda x: str(x.get("dateCreated") or ""), reverse=True)
    return {"items": all_rows, "count": len(all_rows)}


@app.get("/api/jobs")
def list_jobs() -> dict[str, Any]:
    with _db() as con:
        rows = con.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 100").fetchall()
        items = [dict(row) for row in rows]
    return {"items": items}


@app.get("/api/designs/image")
def get_design_image(
    designType: Literal["general", "sneaker"] = Query(...),
    filename: str = Query(...),
):
    safe_name = Path(filename).name
    if safe_name != filename or not safe_name.lower().endswith(".png"):
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path, _ = _get_design_location(designType, safe_name)
    if file_path is None or not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(path=file_path, media_type="image/png", filename=safe_name)


@app.post("/api/generate")
def start_generation(payload: GenerationRequest) -> dict[str, Any]:
    if (
        payload.generationStyle == "detailed"
        and payload.mode == "single"
        and payload.designType == "general"
        and not (payload.phrase or "").strip()
    ):
        raise HTTPException(status_code=422, detail="Single general generation requires phrase")

    job_id = uuid.uuid4().hex
    _insert_job(job_id, payload)

    thread = threading.Thread(target=_run_generation_job, args=(job_id, payload), daemon=True)
    thread.start()

    return {"jobId": job_id, "status": "queued"}


@app.get("/api/generation/options")
def generation_options() -> dict[str, Any]:
    return _build_generation_options()


@app.post("/api/approvals")
def approve_design(payload: ApprovalRequest) -> dict[str, Any]:
    cfg = FRONT_CONFIG[payload.designType]
    source, source_state = _get_design_location(payload.designType, payload.filename)
    if source is None:
        raise HTTPException(status_code=404, detail="Design file not found in generated/approved/rejected folders")

    target_folder = cfg["approved_folder"] if payload.approved else cfg["rejected_folder"]
    target_folder.mkdir(parents=True, exist_ok=True)
    target = target_folder / payload.filename

    if source != target:
        shutil.move(str(source), str(target))

    design_id = _update_design_sheet_approval(payload.designType, payload.filename, payload.approved)
    _update_tm_log(design_id, cfg["code"], payload.approved, payload.notes)
    log_updates = _update_logs(payload.filename, payload.approved, payload.notes)

    return {
        "filename": payload.filename,
        "from": source_state,
        "to": "approved" if payload.approved else "rejected",
        "designId": design_id,
        "updatedLogs": log_updates,
    }


@app.get("/api/expenses")
def list_expenses() -> dict[str, Any]:
    items = _read_expenses()
    total = sum(float(item.get("amount") or 0) for item in items)
    return {"items": items, "count": len(items), "total": round(total, 2)}


@app.post("/api/expenses")
def create_expense(payload: ExpenseCreate) -> dict[str, Any]:
    expense_id = _upsert_expense(payload, update=False)
    return {"expenseId": expense_id}


@app.put("/api/expenses/{expense_id}")
def update_expense(expense_id: str, payload: ExpenseCreate) -> dict[str, Any]:
    data = ExpenseUpdate(expenseId=expense_id, **payload.model_dump())
    _upsert_expense(data, update=True)
    return {"expenseId": expense_id, "updated": True}


@app.delete("/api/expenses/{expense_id}")
def delete_expense(expense_id: str) -> dict[str, Any]:
    _delete_expense(expense_id)
    return {"deleted": True}
