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

## Access from another device (same Wi-Fi/LAN)

1. Start servers from this machine:

```powershell
cd "d:\Projects\POD business\webapp"
.\servers.ps1 start
```

2. Find your machine LAN IP (the script also prints it in `status`):

```powershell
.\servers.ps1 status
```

3. Open on another device:

```text
http://<YOUR_LAN_IP>:5173
```

The frontend proxies `/api` requests to the local backend (`127.0.0.1:8000`), so other devices only need access to port `5173`.

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

## First-run key setup (persistent)

After opening the app, go to the `Setup` tab and save your credentials:

- Printify: `PRINTIFY_TOKEN`, `PRINTIFY_SHOP_ID`
- Printful: `PRINTFUL_API_KEY`, `PRINTFUL_STORE_ID` (optional `PRINTFUL_API_BASE`)
- Generation APIs: `OPENAI_API_KEY`, `IDEOGRAM_API_KEY`, `HF_API_TOKEN`, `LEONARDO_API_KEY`

Keys are persisted locally by the backend and reloaded automatically on restart.
Use `backend/.env.example` as a reference template when setting up a fresh machine.

## Current Features

- Dashboard summary for generated/approved/rejected designs
- Designs and approvals with manual approve/reject actions
- POD upload provider selection per approved design (`Printify (US)` or `Printful (EU)`)
- Generation jobs (single/batch, sneaker/general) routed to existing pipeline
- Job history/state tracking
- Expenses CRUD against `workspace/spreadsheets/financials.xlsx`

## POD Providers (US/EU routing)

The upload flow is provider-aware:

- `Printify` is routed for `US` market uploads
- `Printful` is routed for `EU` market uploads

The frontend reads provider readiness from:

- `GET /api/pod/provider-status`

and sends provider-aware payloads to:

- `POST /api/printify/upload`

with `provider` and `market` in the request body.

### Required environment variables

Backend checks these credentials:

- `PRINTIFY_TOKEN`
- `PRINTIFY_SHOP_ID`
- `PRINTFUL_API_KEY`
- `PRINTFUL_STORE_ID` (must be a Manual Order/API Printful store ID)
- `PRINTFUL_TSHIRT_VARIANT_IDS` (comma-separated Printful variant IDs)
- `PRINTFUL_HOODIE_VARIANT_IDS` (comma-separated Printful variant IDs)

Optional per-front overrides:

- `PRINTFUL_A_TSHIRT_VARIANT_IDS`, `PRINTFUL_B_TSHIRT_VARIANT_IDS`
- `PRINTFUL_A_HOODIE_VARIANT_IDS`, `PRINTFUL_B_HOODIE_VARIANT_IDS`

If a provider is not configured, it appears disabled in the website upload selector.

### Optional Etsy auto-create fallback (for Printful flow)

If Printful publish does not return an Etsy external listing ID, backend can auto-create
an Etsy draft listing (if Etsy setup is connected) using:

- `ETSY_SHIPPING_PROFILE_ID`
- `ETSY_RETURN_POLICY_ID`
- `ETSY_PROCESSING_PROFILE_ID`
- `ETSY_TAXONOMY_ID`

When missing, upload response includes `etsySyncError` with the exact missing keys.

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
