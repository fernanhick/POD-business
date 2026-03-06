# AGENTS.md — Pinterest Module: Master Context File
> READ THIS FILE FIRST before opening any other file in this folder.
> This is the only file you need to orient yourself. It tells you exactly
> what to build, what to never touch, and in what order to work.

---

## WHAT THIS MODULE IS

A Pinterest automation feature being added to an existing POD business portal.
The portal already handles design generation, approvals, and Printify publishing.
This module adds a new "Pinterest" tab to that same portal so the founder can
generate pin graphics, schedule daily posting, and track Pinterest performance —
all from the same interface they already use.

**This module is additive only. It never modifies existing files except for
three append-only changes documented precisely in 02_frontend/FRONTEND_CHANGES.md.**

---

## THE EXISTING PROJECT (do not touch anything listed here)

```
./                                        ← project root
├── webapp/
│   ├── backend/app/
│   │   ├── main.py                       ← EXISTING — add 2 lines only (see BACKEND.md)
│   │   ├── __init__.py                   ← DO NOT TOUCH
│   │   └── app_state.db                  ← DO NOT TOUCH
│   └── frontend/src/
│       ├── App.jsx                       ← EXISTING — add 1 tab entry only (see FRONTEND_CHANGES.md)
│       ├── api.js                        ← EXISTING — append new functions only (see FRONTEND_CHANGES.md)
│       ├── main.jsx                      ← DO NOT TOUCH
│       └── styles.css                    ← DO NOT TOUCH
└── workspace/
    ├── front_a_sneaker/
    │   ├── approved/                     ← READ ONLY — source images for pins
    │   ├── designs/                      ← DO NOT TOUCH
    │   ├── drops/                        ← DO NOT TOUCH
    │   └── rejected/                     ← DO NOT TOUCH
    ├── front_b_general/                  ← DO NOT TOUCH (Pinterest is sneaker-only)
    ├── logs/                             ← DO NOT TOUCH
    └── spreadsheets/
        ├── designs_front_a.xlsx          ← READ ONLY — design titles, concepts, status
        ├── listings.xlsx                 ← READ ONLY — Printify product URLs per design
        └── (all other .xlsx files)       ← DO NOT TOUCH
```

**Existing API routes that are already taken — do not reuse these prefixes:**
`/api/health`, `/api/dashboard/`, `/api/designs`, `/api/jobs/`,
`/api/generate`, `/api/generation/`, `/api/approvals`, `/api/expenses/`, `/api/printify/`

**All new routes in this module use the prefix `/api/pinterest/` — no exceptions.**

---

## WHAT GETS ADDED (new files only, except the 3 noted edits)

```
webapp/
├── backend/app/
│   ├── main.py                           ← ADD 2 lines (import + include_router)
│   └── pinterest/                        ← NEW FOLDER — entire Pinterest backend
│       ├── __init__.py
│       ├── router.py                     ← all /api/pinterest/* routes
│       ├── pin_factory.py                ← builds pin graphics with Pillow
│       ├── pinterest_client.py           ← Pinterest API v5 wrapper
│       ├── scheduler.py                  ← APScheduler posting jobs
│       ├── keyword_service.py            ← keyword selection logic
│       ├── spreadsheet_reader.py         ← reads workspace spreadsheets (read-only)
│       └── models.py                     ← Pydantic schemas + SQLite models for pins
└── frontend/src/
    ├── App.jsx                           ← ADD 1 tab (Pinterest) to existing tab list
    ├── api.js                            ← APPEND pinterest functions at bottom
    └── pinterest/                        ← NEW FOLDER — all Pinterest UI components
        ├── PinterestTab.jsx              ← tab root, internal sub-navigation
        ├── PinFactory.jsx                ← pick approved design → generate pins
        ├── PinSchedule.jsx               ← view/manage posting queue
        └── PinAnalytics.jsx              ← Pinterest performance metrics

workspace/
└── pinterest/                            ← NEW FOLDER — generated output only
    ├── pins/                             ← 1000×1500 pin graphics output here
    └── pinterest.db                      ← SQLite: pins table + schedule_jobs table
```

---

## READ ORDER FOR IMPLEMENTATION

Feed these files to your LLM in this exact order. Each file is self-contained
but references the ones before it.

| Step | File | What it covers |
|---|---|---|
| 1 | `AGENTS.md` (this file) | Full context, constraints, file map |
| 2 | `00_start/DATA_MODELS.md` | All data shapes — read before writing any code |
| 3 | `01_backend/BACKEND.md` | Backend: all services + routes + the 2 lines to add to main.py |
| 4 | `02_frontend/FRONTEND_CHANGES.md` | The exact 3 changes to existing frontend files |
| 5 | `02_frontend/FRONTEND_COMPONENTS.md` | All new Pinterest UI pages + components |
| 6 | `03_data/KEYWORDS.md` | Full 300+ keyword database — write to keywords.json |
| 7 | `03_data/PIN_TEMPLATES.md` | 20 pin template definitions — write to pin_templates.json |
| 8 | `04_strategy/SCHEDULING.md` | Posting schedule + holiday calendar logic |
| 9 | `04_strategy/APP_PHASE.md` | Mobile app promotion phases + launch day burst strategy |

---

## IMPLEMENTATION STATUS TABLE

Update this table every time a piece is completed.
An LLM starting a new session checks this first to know what's done.

| Component | Status | Notes |
|---|---|---|
| `webapp/backend/app/pinterest/` folder | 🔴 Not started | |
| `webapp/backend/app/pinterest/models.py` | 🔴 Not started | |
| `webapp/backend/app/pinterest/spreadsheet_reader.py` | 🔴 Not started | |
| `webapp/backend/app/pinterest/keyword_service.py` | 🔴 Not started | |
| `webapp/backend/app/pinterest/pin_factory.py` | 🔴 Not started | |
| `webapp/backend/app/pinterest/pinterest_client.py` | 🔴 Not started | |
| `webapp/backend/app/pinterest/scheduler.py` | 🔴 Not started | |
| `webapp/backend/app/pinterest/router.py` | 🔴 Not started | |
| `main.py` 2-line edit | 🔴 Not started | |
| `workspace/pinterest/` folder + pins/ subfolder | 🔴 Not started | |
| `workspace/pinterest/keywords.json` | 🔴 Not started | |
| `workspace/pinterest/pin_templates.json` | 🔴 Not started | |
| `webapp/frontend/src/pinterest/` folder | 🔴 Not started | |
| `webapp/frontend/src/pinterest/PinterestTab.jsx` | 🔴 Not started | |
| `webapp/frontend/src/pinterest/PinFactory.jsx` | 🔴 Not started | |
| `webapp/frontend/src/pinterest/PinSchedule.jsx` | 🔴 Not started | |
| `webapp/frontend/src/pinterest/PinAnalytics.jsx` | 🔴 Not started | |
| `App.jsx` tab edit | 🔴 Not started | |
| `api.js` append | 🔴 Not started | |
| App phase toggle (env + DB setting) | 🔴 Not started | See APP_PHASE.md |
| `webapp/backend/app/pinterest/app_phase.py` | 🔴 Not started | See APP_PHASE.md |
| `webapp/frontend/src/pinterest/AppMode.jsx` | 🔴 Not started | See APP_PHASE.md |
| `workspace/pinterest/app_pin_templates.json` | 🔴 Not started | See APP_PHASE.md |

---

## ENV VARIABLES TO ADD

Add these to `workspace/.env` alongside the existing variables.
Do not create a new .env file.

```env
# Pinterest API
PINTEREST_APP_ID=
PINTEREST_APP_SECRET=
PINTEREST_ACCESS_TOKEN=
PINTEREST_REFRESH_TOKEN=

# Pinterest Board IDs (from your Pinterest Business account)
PINTEREST_BOARD_SNEAKER_CULTURE=
PINTEREST_BOARD_OUTFIT_IDEAS=
PINTEREST_BOARD_ROOM_DECOR=
PINTEREST_BOARD_GIFTS=
PINTEREST_BOARD_STREETWEAR=

# Pinterest Posting Schedule
PINTEREST_PINS_PER_DAY=5
PINTEREST_POST_TIMES=08:00,11:00,14:00,18:00,21:00
PINTEREST_TIMEZONE=America/New_York

# Paths (relative to project root — adjust if your working directory differs)
WORKSPACE_PATH=./workspace
PINTEREST_STORAGE_PATH=./workspace/pinterest

# Mobile App Phase — controls all app-promotion pin behavior
# Values: pre_launch | launched
# Switch from pre_launch to launched via the App Mode toggle in the portal.
# Do not edit this manually — use the portal toggle so the launch burst fires correctly.
APP_PHASE=pre_launch
APP_WEBSITE_URL=                  # your current app preview website URL
APP_EMAIL_CAPTURE_URL=            # landing page with email signup (can be same as above)
APP_STORE_URL=                    # Apple App Store URL — fill in when launched
PLAY_STORE_URL=                   # Google Play URL — fill in when launched
APP_LAUNCH_BURST_PINS=30          # number of pre-generated pins to release on launch day
```
