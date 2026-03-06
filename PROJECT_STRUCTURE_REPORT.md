# POD Business Project Structure Report

Generated: 2026-03-06

## 1) Project File Tree

> Snapshot excludes cache/vendor folders for readability: `.git`, `.venv`, `node_modules`, `__pycache__`, `.venv313`, `.runtime`.

```text
./
├── .claude/
│   └── settings.local.json
├── webapp/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── app_state.db
│   │   │   └── main.py
│   │   ├── .env.example
│   │   └── requirements.txt
│   ├── frontend/
│   │   ├── dist/
│   │   │   ├── assets/
│   │   │   │   ├── index-BWCj81F2.css
│   │   │   │   └── index-C2tgIwdk.js
│   │   │   └── index.html
│   │   ├── public/
│   │   ├── src/
│   │   │   ├── api.js
│   │   │   ├── App.jsx
│   │   │   ├── main.jsx
│   │   │   └── styles.css
│   │   ├── index.html
│   │   ├── package.json
│   │   ├── package-lock.json
│   │   └── vite.config.js
│   ├── .gitignore
│   ├── README.md
│   └── servers.ps1
├── workspace/
│   ├── front_a_sneaker/
│   │   ├── approved/
│   │   │   └── rotation_standard_001.png
│   │   ├── designs/
│   │   │   ├── collector_status_001.png
│   │   │   └── wear_your_pairs_001.png
│   │   ├── drops/
│   │   └── rejected/
│   │       └── rotation_society_001.png
│   ├── front_b_general/
│   │   ├── approved/
│   │   ├── designs/
│   │   │   ├── daily_culture_001.png
│   │   │   └── vibes_club_001.png
│   │   └── rejected/
│   ├── logs/
│   │   ├── front_a_DROP-01_20260306.json
│   │   └── front_b_batch_20260306.json
│   ├── spreadsheets/
│   │   ├── app_analytics.xlsx
│   │   ├── designs_front_a.xlsx
│   │   ├── designs_front_b.xlsx
│   │   ├── drops_front_a.xlsx
│   │   ├── financials.xlsx
│   │   ├── listings.xlsx
│   │   ├── niches_front_b.xlsx
│   │   ├── sales.xlsx
│   │   └── trademark_log.xlsx
│   ├── .env
│   ├── design_pipeline.py
│   ├── inspect_designs.py
│   ├── pipeline_output_example_front_a.json
│   ├── pipeline_output_example_front_b.json
│   ├── printify_upload.py
│   ├── trademark_check.py
│   ├── update_workbooks.py
│   └── WORKSPACE_README.md
├── .gitignore
├── generate_workspace_v2.py
├── pipeline_output_example_front_a.json
├── pipeline_output_example_front_b.json
├── pod-business-plan.md
├── update_workbooks_v2.py
└── WORKSPACE_README_v2.md
```

## 2) Backend API Routes (FastAPI)

Source: `webapp/backend/app/main.py`

| Method | Path                         | Handler              | Purpose                                            |
| ------ | ---------------------------- | -------------------- | -------------------------------------------------- |
| GET    | `/api/health`                | `health`             | Health + workspace/timestamp check                 |
| GET    | `/api/dashboard/summary`     | `dashboard_summary`  | Aggregated dashboard metrics                       |
| GET    | `/api/designs`               | `list_designs`       | List designs with filters (`designType`, `status`) |
| GET    | `/api/jobs`                  | `list_jobs`          | List recent jobs                                   |
| GET    | `/api/jobs/{job_id}`         | `get_job`            | Get one job detail + generated files               |
| GET    | `/api/designs/image`         | `get_design_image`   | Serve design PNG by query params                   |
| POST   | `/api/generate`              | `start_generation`   | Queue generation job                               |
| GET    | `/api/generation/options`    | `generation_options` | Get dynamic options (drops/niches/phrases)         |
| POST   | `/api/designs/variant`       | `generate_variant`   | Queue variant generation job                       |
| POST   | `/api/approvals`             | `approve_design`     | Approve/reject and sync spreadsheets/logs          |
| GET    | `/api/expenses`              | `list_expenses`      | List expense records + totals                      |
| POST   | `/api/expenses`              | `create_expense`     | Create expense                                     |
| PUT    | `/api/expenses/{expense_id}` | `update_expense`     | Update expense                                     |
| DELETE | `/api/expenses/{expense_id}` | `delete_expense`     | Delete expense                                     |
| GET    | `/api/printify/status`       | `printify_status`    | Check Printify env/config status                   |
| POST   | `/api/printify/upload`       | `printify_upload`    | Upload approved design to Printify                 |

## 3) Existing Frontend Pages / Views

Frontend is a **single-page React app** with tab-based views in `webapp/frontend/src/App.jsx`.

### Navigation Tabs (existing pages)

1. **Dashboard**
   - KPI cards: sneaker total, general total, expenses, jobs
   - Design bucket summary (generated/approved/rejected)

2. **Designs**
   - Filter by type/status
   - Table with preview, metadata, location/status, Printify state
   - Actions: approve, reject, upload (if approved), generate variant
   - Image modal preview + keyboard navigation
   - Variant generation form

3. **Generate**
   - New generation form (type, visual mode, palette, count)
   - Sneaker-specific drop selector
   - General-specific phrase/niche/sub-niche fields
   - Skip USPTO API toggle
   - Generation modal with live job logs and completion state

4. **Expenses**
   - Add/edit expense form
   - Total expenses summary card
   - Expenses table with edit/delete actions

5. **Jobs**
   - Job history table (status, reason, timestamps)
   - Per-job log viewer panel

### Entry + API integration

- App entry: `webapp/frontend/src/main.jsx`
- API client: `webapp/frontend/src/api.js`
- Frontend expects backend base URL: `http://127.0.0.1:8000/api`
