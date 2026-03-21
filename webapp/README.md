# POD Business — Web App (Control Center)

Local web app that wraps the design automation pipeline in `../workspace/`. No cloud required — everything runs on your own machine.

## Structure

```
webapp/
├── backend/            ← FastAPI app (Python 3.13)
│   ├── app/
│   │   ├── main.py         ← All core routes + job queue
│   │   ├── provider_settings.py  ← API key storage (SQLite)
│   │   ├── pinterest/      ← Pinterest scheduler, pin factory, app-phase control
│   │   └── etsy/           ← Etsy OAuth 2 setup + listing management
│   ├── requirements.txt
│   └── .env.example
├── frontend/           ← React 18 + Vite
│   └── src/
│       ├── App.jsx
│       ├── pinterest/      ← Pinterest UI (setup, pin factory, schedule, analytics)
│       ├── etsy/           ← Etsy setup UI
│       └── setup/          ← API key management UI
├── servers.ps1         ← One-command start/stop/status (Windows)
├── desktop.pyw         ← Launch as native desktop window (pywebview)
└── POD Business.bat    ← Double-click launcher
```

The scripts and data in `../workspace/` are never modified by the web app — it only reads from and writes results back to them.

---

## First-time Setup

### Backend (Python 3.13)

```powershell
cd "d:\Projects\POD business\webapp\backend"
py -3.13 -m venv .venv313
.\.venv313\Scripts\python.exe -m pip install --upgrade pip
.\.venv313\Scripts\python.exe -m pip install -r requirements.txt
```

### Frontend (Node.js 18+)

```powershell
cd "d:\Projects\POD business\webapp\frontend"
npm install
```

---

## Starting the Servers

### One command (Windows)

```powershell
cd "d:\Projects\POD business\webapp"
.\servers.ps1 start      # start backend + frontend
.\servers.ps1 status     # check status and print LAN IP
.\servers.ps1 stop       # stop both
```

Logs and PID files are written to `webapp/.runtime/`.

### Manual start

```powershell
# Terminal 1 — backend
cd "d:\Projects\POD business\webapp\backend"
.\.venv313\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 — frontend
cd "d:\Projects\POD business\webapp\frontend"
npm run dev
```

Open **http://127.0.0.1:5173**

### Desktop window

```powershell
python desktop.pyw
```

Opens the UI in a native window via `pywebview` (no browser tab).

---

## Access from Another Device (same Wi-Fi / LAN)

The frontend proxies all `/api` requests to `127.0.0.1:8000`, so other devices only need port `5173`.

```powershell
.\servers.ps1 status    # prints your LAN IP
```

Then on the other device: `http://<LAN_IP>:5173`

---

## API Key Setup (first run)

Open the app → **Setup** tab. Keys are stored in `workspace/pinterest/pinterest.db` and reloaded automatically on every backend restart.

| Key                 | Provider     | Tab                     |
| ------------------- | ------------ | ----------------------- |
| `PRINTIFY_TOKEN`    | Printify     | Setup → POD Keys        |
| `PRINTIFY_SHOP_ID`  | Printify     | Setup → POD Keys        |
| `PRINTFUL_API_KEY`  | Printful     | Setup → POD Keys        |
| `PRINTFUL_STORE_ID` | Printful     | Setup → POD Keys        |
| `OPENAI_API_KEY`    | OpenAI       | Setup → Generation Keys |
| `IDEOGRAM_API_KEY`  | Ideogram     | Setup → Generation Keys |
| `HF_API_TOKEN`      | Hugging Face | Setup → Generation Keys |
| `LEONARDO_API_KEY`  | Leonardo.ai  | Setup → Generation Keys |

Alternatively, copy `.env.example` to `.env` before starting the backend:

```powershell
copy backend\.env.example backend\.env
# then edit backend\.env with your values
```

**Etsy OAuth:** Setup → Etsy tab. Requires an Etsy developer app (API key + shared secret). The OAuth callback must be registered as `http://localhost:8000/api/etsy/setup/callback` in the Etsy developer portal.

**Pinterest:** Setup → Pinterest tab.

---

## Features

| Feature                           | Route prefix                         |
| --------------------------------- | ------------------------------------ |
| Dashboard (design counts)         | `GET /api/designs/stats`             |
| Design browser + approve/reject   | `GET/POST /api/designs`              |
| Generation jobs (single/batch)    | `POST /api/jobs`                     |
| Job history                       | `GET /api/jobs`                      |
| POD upload (Printify or Printful) | `POST /api/pod/upload`               |
| Provider status                   | `GET /api/pod/provider-status`       |
| Pricing profiles                  | `GET /api/pod/pricing`               |
| Expense tracker (financials.xlsx) | `GET/POST/PUT/DELETE /api/expenses`  |
| Pinterest pin queue               | `/api/pinterest/pins`                |
| Pinterest scheduler               | `/api/pinterest/schedule`            |
| Pinterest pin factory             | `/api/pinterest/pin-factory`         |
| Pinterest app phase               | `/api/pinterest/app-phase`           |
| Pinterest analytics               | `/api/pinterest/analytics`           |
| Etsy setup / OAuth                | `/api/etsy/setup/*`                  |
| Etsy listings                     | `/api/etsy/listings/*`               |
| API key management                | `GET/POST/DELETE /api/settings/keys` |

---

## POD Providers (US/EU routing)

- **Printify** → US market uploads
- **Printful** → EU market uploads

The frontend reads readiness from `GET /api/pod/provider-status` and sends the provider choice alongside the design payload. Regional pricing is handled by `workspace/pod_pricing.py`.

---

## Approval Reconciliation

When approving or rejecting a design in the UI, the backend:

1. Moves the file to `approved/` or `rejected/` under the relevant front folder
2. Updates `Approved?` and `Status` in the corresponding design spreadsheet
3. Updates the decision in `trademark_log.xlsx`
4. Updates matching records in JSON logs under `workspace/logs/`

---

## Troubleshooting

| Problem                       | Fix                                                                                    |
| ----------------------------- | -------------------------------------------------------------------------------------- |
| Backend won't start           | Confirm `.venv313` exists. Check `webapp/.runtime/backend.err.log`.                    |
| Frontend blank / API errors   | Backend must be running on port 8000 before starting the frontend.                     |
| Spreadsheets missing          | Run `python generate_workspace_v2.py --dir workspace` from the project root.           |
| Keys not saving               | `workspace/pinterest/` is created automatically on first run. Check write permissions. |
| Etsy OAuth callback fails     | Register `http://localhost:8000/api/etsy/setup/callback` in your Etsy developer app.   |
| Pinterest pins not scheduling | Check the App Mode setting in Pinterest → App Mode tab.                                |

For complete setup instructions see the [root README](../README.md).
