# POD Local Control Center

This app runs locally and wraps your existing automation inside `workspace/`.

## Structure

- `backend/` FastAPI API for designs, jobs, approvals, and expenses
- `frontend/` React + Vite UI
- Existing scripts/data stay in `../workspace/` (unchanged)

## Run Backend

```powershell
cd "d:\Projects\POD business\webapp\backend"
c:/python314/python.exe -m pip install -r requirements.txt
c:/python314/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Run Frontend

```powershell
cd "d:\Projects\POD business\webapp\frontend"
npm install
npm run dev
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
