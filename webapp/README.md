# POD Local Control Center

This app runs locally and wraps your existing automation inside `workspace/`.

## Structure

- `backend/` FastAPI API for designs, jobs, approvals, and expenses
- `frontend/` React + Vite UI
- Existing scripts/data stay in `../workspace/` (unchanged)

## One-command start/stop

```powershell
cd "d:\Projects\POD business\webapp"
.\servers.ps1 start
```

Useful commands:

```powershell
.\servers.ps1 status
.\servers.ps1 stop
```

The script writes logs and PID files under `webapp/.runtime/`.

## Backend setup (first run)

```powershell
cd "d:\Projects\POD business\webapp\backend"
py -3.13 -m venv .venv313
.\.venv313\Scripts\python.exe -m pip install --upgrade pip
.\.venv313\Scripts\python.exe -m pip install -r requirements.txt
```

## Frontend setup (first run)

```powershell
cd "d:\Projects\POD business\webapp\frontend"
npm install
```

Open http://127.0.0.1:5173

## Current Features

- Dashboard summary for generated/approved/rejected designs
- Designs and approvals with manual approve/reject actions
- Generation jobs (single/batch, sneaker/general) routed to existing pipeline
- Job history/state tracking
- Expenses CRUD against `workspace/spreadsheets/financials.xlsx`

## Approval Reconciliation

When approving/rejecting in the app, it will:

1. Move file to `approved/` or `rejected/`
2. Update `Approved?` + `Status` in the corresponding design spreadsheet
3. Update decision in `trademark_log.xlsx`
4. Update matching records in JSON logs under `workspace/logs/`

## Recommendations

1. Add a nightly backup job for `workspace/spreadsheets` and `workspace/logs`.
2. Add role/PIN lock if this runs on shared machines.
3. Add dry-run toggle for generation/upload actions.
4. Add a resync endpoint to rebuild app state from workbook + folders.
