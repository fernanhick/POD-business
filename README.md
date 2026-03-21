# POD Business — Dual-Front Print-on-Demand Automation

A **solo indie developer** Print-on-Demand (POD) dropshipping operation with full design-to-listing automation, built on Printify + Etsy. Two distinct product fronts run from the same codebase, managed through a local web UI that doubles as a control center.

---

## The Idea

Most POD businesses start from zero — no audience, no traffic, and a slow grind to Etsy organic ranking. This project is structured differently.

**Front A — Sneaker Culture (Primary):** A pre-built sneaker portfolio mobile app acts as a captive audience layer. App users are already self-identified sneaker collectors who see contextual merch inside the app ("Match Your Rotation"). Tapping a product opens the Etsy listing directly — bypassing the cold-start problem entirely. Designs use a 72-hour drop model that mirrors real sneaker culture.

**Front B — Generalized Designs (Secondary):** High-volume designs across evergreen niches (occupation, pet, hobby, identity) build Etsy shop authority and steady passive revenue. Fully automated pipeline from concept to upload.

Both fronts share the same infrastructure, spreadsheets, and upload pipeline. No inventory. Under $20 to launch.

```
Mobile App  ──→  Etsy listing  ──→  Printify fulfills  ──→  ships to customer
                      ↑
Etsy organic ─────────┘
                      ↑
Pinterest scheduler ──┘
```

---

## Architecture

```
POD business/
├── workspace/          ← Python automation scripts (pipeline, uploads, spreadsheets)
├── webapp/             ← Local control center (FastAPI backend + React frontend)
│   ├── backend/        ← FastAPI app, Printify/Printful/Etsy/Pinterest integrations
│   └── frontend/       ← React 18 + Vite UI
├── pinterest-docs/     ← Pinterest integration planning docs
├── pod-business-plan.md
└── README.md           ← you are here
```

| Layer | Tech | Purpose |
|---|---|---|
| Backend | FastAPI + Python 3.13 | API, job queue, POD uploads, Pinterest scheduler |
| Frontend | React 18 + Vite | Control center UI |
| Data | SQLite + openpyxl (xlsx) | Settings, pin queue, design registry, financials |
| POD — US | Printify | Product creation + Etsy sync for US market |
| POD — EU | Printful | Product creation + Etsy sync for EU market |
| Social | Pinterest API | Automated pin scheduling, app promotion |
| Marketplace | Etsy API (OAuth 2) | Listing management, shop sections, analytics |
| Design gen | OpenAI / Ideogram / HF / Leonardo | AI-assisted design generation |

---

## Features

- **Dashboard** — live counts of generated / approved / rejected designs per front
- **Design browser** — approve or reject designs with one click
- **Generation jobs** — trigger single or batch generation for Front A (sneaker) or Front B (general)
- **POD upload** — provider-aware upload (Printify US / Printful EU) per approved design
- **Pricing engine** — regional pricing profiles for US and EU markets
- **Expense tracker** — CRUD against `workspace/spreadsheets/financials.xlsx`
- **Pinterest scheduler** — pin queue, rate-limit-aware drip scheduling, app-phase CTA switching
- **Pinterest pin factory** — AI-assisted pin copy generation from design metadata
- **Etsy integration** — OAuth 2 setup, shop sections, listing assignment
- **App phase control** — switch between `pre_launch` and `launched` to change all Pinterest CTAs at once
- **Key management** — all API credentials stored locally in SQLite, managed via the Setup UI tab

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.13 | Required by `servers.ps1`. Other versions work with manual commands. |
| Node.js | 18+ | For the React frontend |
| Git | any | — |
| PowerShell | 5.1+ | Windows only — for `servers.ps1` one-command start |

> **macOS / Linux:** `servers.ps1` is Windows-specific. Use the manual start commands listed in the [Manual Start](#manual-start) section.

---

## Quick Start (Windows)

```powershell
# 1. Clone the repo
git clone <your-repo-url> "POD business"
cd "POD business"

# 2. Set up backend virtual environment (one-time)
cd webapp\backend
py -3.13 -m venv .venv313
.\.venv313\Scripts\python.exe -m pip install --upgrade pip
.\.venv313\Scripts\python.exe -m pip install -r requirements.txt
cd ..\..

# 3. Set up frontend (one-time)
cd webapp\frontend
npm install
cd ..\..

# 4. Generate workspace spreadsheets (one-time)
python generate_workspace_v2.py --dir workspace

# 5. Start both servers
cd webapp
.\servers.ps1 start
```

Then open **http://127.0.0.1:5173** in your browser.

---

## Detailed Setup

### 1. Backend — Python virtual environment

```powershell
cd "d:\Projects\POD business\webapp\backend"
py -3.13 -m venv .venv313
.\.venv313\Scripts\python.exe -m pip install --upgrade pip
.\.venv313\Scripts\python.exe -m pip install -r requirements.txt
```

Key dependencies: `fastapi`, `uvicorn`, `openpyxl`, `pydantic`, `requests`, `pillow`, `python-dotenv`, `apscheduler`, `pywebview`.

### 2. Frontend — Node modules

```powershell
cd "d:\Projects\POD business\webapp\frontend"
npm install
```

### 3. Workspace spreadsheets

```powershell
cd "d:\Projects\POD business"
python generate_workspace_v2.py --dir workspace
```

This creates all `.xlsx` workbooks under `workspace/spreadsheets/`. Safe to run again — use `--reset` to rebuild from scratch.

### 4. API Keys (first run)

Open the app, go to the **Setup** tab, and fill in your credentials. Keys are persisted in `workspace/pinterest/pinterest.db` and reloaded automatically on every backend restart.

Alternatively, copy `webapp/backend/.env.example` to `webapp/backend/.env` and fill it in before starting the backend:

```env
# webapp/backend/.env
PRINTIFY_TOKEN=your_printify_api_token
PRINTIFY_SHOP_ID=your_shop_id

PRINTFUL_API_KEY=your_printful_key
PRINTFUL_STORE_ID=your_store_id
PRINTFUL_API_BASE=https://api.printful.com

OPENAI_API_KEY=
IDEOGRAM_API_KEY=
HF_API_TOKEN=
LEONARDO_API_KEY=
```

| Key | Where to get it | Required? |
|---|---|---|
| `PRINTIFY_TOKEN` | Printify → My account → Connections | Yes (US uploads) |
| `PRINTIFY_SHOP_ID` | Printify → Shop URL or API | Yes (US uploads) |
| `PRINTFUL_API_KEY` | Printful → Developer Portal | Yes (EU uploads) |
| `PRINTFUL_STORE_ID` | Printful → Dashboard | Yes (EU uploads) |
| `OPENAI_API_KEY` | platform.openai.com | Optional (generation) |
| `IDEOGRAM_API_KEY` | ideogram.ai | Optional (generation) |
| `HF_API_TOKEN` | huggingface.co | Optional (generation) |
| `LEONARDO_API_KEY` | app.leonardo.ai | Optional (generation) |

**Etsy OAuth** is configured separately through the Setup → Etsy tab. You will need a Etsy developer app (API key + shared secret) from the [Etsy Developer portal](https://developer.etsy.com/).

**Pinterest** credentials are set through Setup → Pinterest tab.

---

## Running the App

### Option A — One command (Windows PowerShell)

```powershell
cd "d:\Projects\POD business\webapp"
.\servers.ps1 start      # start both backend and frontend
.\servers.ps1 status     # check status + LAN IP
.\servers.ps1 stop       # stop both
```

Logs are written to `webapp/.runtime/backend.out.log` and `webapp/.runtime/frontend.out.log`.

### Option B — Manual Start

**Backend:**
```powershell
cd "d:\Projects\POD business\webapp\backend"
.\.venv313\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend (separate terminal):**
```powershell
cd "d:\Projects\POD business\webapp\frontend"
npm run dev
```

### Option C — Desktop app

```powershell
cd "d:\Projects\POD business\webapp"
python desktop.pyw
```

Opens the control center in a native window via `pywebview` (no browser tab needed).

### Option D — Batch file

Double-click `webapp\POD Business.bat` — starts both servers and opens the window.

---

## Access from Another Device (same Wi-Fi / LAN)

Start the servers normally, then on any other device on the same network:

```
http://<YOUR_LAN_IP>:5173
```

Find your LAN IP with:
```powershell
.\servers.ps1 status
```

---

## Manual Start (macOS / Linux)

```bash
# Backend
cd webapp/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Frontend (separate terminal)
cd webapp/frontend
npm install
npm run dev
```

---

## Workspace Scripts

| Script | Purpose |
|---|---|
| `generate_workspace_v2.py` | Generate or reset all spreadsheet workbooks |
| `update_workbooks_v2.py` | Update workbooks from a batch log JSON |
| `workspace/design_pipeline.py` | Core design generation pipeline |
| `workspace/printify_upload.py` | Upload and publish products to Printify |
| `workspace/printful_upload.py` | Upload products to Printful |
| `workspace/printify_mockups.py` | Generate product mockups from Printify |
| `workspace/pod_pricing.py` | Regional pricing profiles (US / EU) |
| `workspace/pod_providers.py` | Provider registry |
| `workspace/trademark_check.py` | IP clearance checks |
| `workspace/update_workbooks.py` | Earlier version of workbook updater |
| `workspace/branding/generate_insert.py` | Generate branded insert cards |
| `workspace/pinterest/export_pins.py` | Export pin batch for Pinterest |

---

## Spreadsheets

All data lives under `workspace/spreadsheets/`. Generated by `generate_workspace_v2.py`.

| File | Front | Auto-populated | Updated |
|---|---|---|---|
| `designs_front_a.xlsx` | A | ✅ | After each sneaker batch |
| `designs_front_b.xlsx` | B | ✅ | After each general batch |
| `sales.xlsx` | Both | Manual | After each Etsy payout |
| `listings.xlsx` | Both | Manual | Weekly from Etsy Stats |
| `trademark_log.xlsx` | Both | ✅ | After each batch |
| `drops_front_a.xlsx` | A | Manual | Before each drop launch |
| `app_analytics.xlsx` | A | Manual | Weekly from app dashboard |
| `niches_front_b.xlsx` | B | ✅ | After each batch |
| `financials.xlsx` | Both | Manual | Monthly |

---

## Pinterest Integration

The Pinterest module lives in `webapp/backend/app/pinterest/` and `workspace/pinterest/`.

**App phase control** (`pre_launch` ↔ `launched`) switches all pin CTAs globally — pins created before launch say "get notified", pins after launch say "download the app".

A **launch burst** automatically queues all draft app-promo pins when you flip to `launched`.

The **pin scheduler** respects Pinterest rate limits and drips pins according to a configurable cadence (see `webapp/backend/app/pinterest/scheduler.py`).

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Backend won't start | Make sure `.venv313` exists via setup step. Check `webapp/.runtime/backend.err.log`. |
| `ModuleNotFoundError` on workspace scripts | Run from the project root, not from `workspace/`. |
| Frontend shows blank / API errors | Backend must be running on port 8000 first. |
| Spreadsheets missing | Run `python generate_workspace_v2.py --dir workspace`. |
| Etsy OAuth redirect fails | Ensure `http://localhost:8000/api/etsy/setup/callback` is registered in your Etsy app's redirect URIs. |
| Pinterest pins not scheduling | Check `APP_PHASE` setting in the Pinterest → App Mode tab. |
| Keys not saving | The backend writes to `workspace/pinterest/pinterest.db` — ensure the `workspace/pinterest/` directory exists (created automatically on first run). |

---

## Project History

The workspace was bootstrapped with `generate_workspace_v2.py` and the design pipeline has been running since early March 2026. The webapp control center was added to provide a UI over the existing scripts without modifying the automation layer.
