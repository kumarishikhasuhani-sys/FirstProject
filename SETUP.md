# Local Setup Guide

Run the full app locally in ~5 minutes. No Docker, no Postgres, no extra services needed.

---

## What you need first

| Tool | Min version | How to check |
|---|---|---|
| Python | 3.10+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |

---

## Step 1 — Get the code

```bash
git clone <your-repo-url> breathe-esg
cd breathe-esg
```

You should see this structure:
```
breathe-esg/
├── backend/          ← Django API
├── frontend/         ← React app
├── MODEL.md
├── DECISIONS.md
├── TRADEOFFS.md
├── SOURCES.md
└── SETUP.md
```

---

## Step 2 — Start the backend

Open a terminal and run these **one by one**:

```bash
cd breathe-esg/backend
```

**Create and activate a virtual environment:**

```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows (Command Prompt)
python -m venv venv
venv\Scripts\activate.bat

# Windows (PowerShell)
python -m venv venv
venv\Scripts\Activate.ps1
```

Your prompt will now show `(venv)`.

**Install dependencies:**

```bash
pip install -r requirements.txt
```

Installs: Django 4.2, Django REST Framework, CORS headers, python-dateutil.

**Create the database:**

```bash
python manage.py migrate
```

You'll see a list of migrations ending with `esg.0001_initial... OK`. This creates a `db.sqlite3` file — that's your local database.

**Start the server:**

```bash
python manage.py runserver 8000
```

You should see:
```
Starting development server at http://127.0.0.1:8000/
```

**Keep this terminal open** — the backend must stay running.

**Quick check** (open a new terminal tab):
```bash
curl http://localhost:8000/api/tenants/
# Expected: []
```

---

## Step 3 — Start the frontend

Open a **new terminal tab** (keep backend running in the first one):

```bash
cd breathe-esg/frontend
npm install
npm run dev
```

You should see:
```
VITE v8.x.x  ready in ~100ms
➜  Local:   http://localhost:5173/
```

> **Port conflict?** If 5173 is taken, Vite auto-picks 5174, 5175, etc. Check your terminal for the actual URL.

Open **http://localhost:5173** in your browser. You should see the green Breathe ESG sidebar.

---

## Step 4 — Load sample data

Three sample files live in `backend/sample_data/`. Load them through the UI:

### 4a. Create a tenant

1. Click **Ingest Data** in the sidebar
2. In the "Or create new tenant" field type **Acme Corp**
3. Click **+ Create** — it appears in the dropdown, auto-selected

### 4b. Upload SAP data

1. Source type: click **SAP**
2. Upload file: pick `backend/sample_data/sample_sap.csv`
3. Click **↑ Upload & Ingest**

Result card should show:
```
PARSED   Total: 4   Parsed: 4   Suspicious: 1
```

### 4c. Upload Utility data

1. Source type: click **UTILITY**
2. Upload file: pick `backend/sample_data/sample_utility.csv`
3. Click **↑ Upload & Ingest**

Result: `PARSED  Total: 3  Parsed: 3  Suspicious: 1`

### 4d. Upload Travel data

1. Source type: click **TRAVEL**
2. Upload file: pick `backend/sample_data/sample_travel.json`
3. Click **↑ Upload & Ingest**

Result: `PARSED  Total: 3  Parsed: 3  Suspicious: 1`

---

## Step 5 — Use the dashboard

Click **Dashboard** in the sidebar. Select **Acme Corp** from the tenant dropdown (top right).

You should see **10 total records** across the 6 metric cards.

### What to try

**Filter by status:** Use the Status dropdown → select `PENDING_REVIEW` (all 10 should appear)

**Filter flagged only:** Check the "Flagged only" checkbox — 3 suspicious records appear:

| Record | Flag | Reason |
|---|---|---|
| SAP — DE99 plant | `UNKNOWN_PLANT` | Plant code DE99 not in the known set |
| Utility — ELEC-9999 | `LONG_BILLING_PERIOD` | 49-day billing period (> 40-day threshold) |
| Travel — Berlin ground | `MISSING_DISTANCE` | Ground transport with no distance_km |

**Review and approve a record:**

1. Click any row → review drawer opens on the right
2. The **Flags** section (top) shows any suspicious flags
3. Edit a field (e.g. change a quantity) → click **Save Edits**
4. Click **Show edit log** → see the before/after diff recorded
5. Click **Show raw payload** → see the exact original row from the source file
6. Click **✓ Approve** → record locks, status changes to APPROVED, can no longer be edited

---

## Running both servers — quick reference

You need **two terminals open at the same time**:

```
Terminal 1 (backend):               Terminal 2 (frontend):
──────────────────────────────────  ──────────────────────────────────
cd breathe-esg/backend              cd breathe-esg/frontend
source venv/bin/activate            npm run dev
python manage.py runserver 8000
```

Then open: **http://localhost:5173**

---

## Resetting to a clean state

Wipe all data and start fresh (e.g. before a demo):

```bash
cd breathe-esg/backend
rm db.sqlite3
python manage.py migrate
```

---

## Deploying to Railway (required for submission)

> The assignment says **"Local-only submissions will not be reviewed."** You must deploy.

The project is set up for a **single Railway service** — Railway builds the React app, copies it into Django, then Django serves both the API and the React SPA from one process.

### How it works

```
Railway build phase:
  1. npm install  (frontend)
  2. pip install  (backend)
  3. npm run build  →  frontend/dist/
  4. cp -r frontend/dist  backend/frontend_build/
  5. python manage.py collectstatic

Railway start:
  gunicorn breathe.wsgi  (Django serves /api/... and serves React SPA for everything else)
```

The `nixpacks.toml` file at the repo root tells Railway exactly how to do all of this — you don't need to configure anything manually in the Railway dashboard except the environment variables below.

### Step-by-step

**1. Push to GitHub**

```bash
cd breathe-esg
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/<your-username>/breathe-esg.git
git push -u origin main
```

**2. Create a Railway project**

- Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
- Select your `breathe-esg` repository
- Railway detects `nixpacks.toml` and starts building automatically

**3. Add a PostgreSQL database**

In Railway dashboard → your project → **+ New** → **Database** → **Add PostgreSQL**

Railway automatically injects `DATABASE_URL` into your service. Django reads it via `dj_database_url` — no extra config needed.

**4. Set environment variables**

In Railway dashboard → your service → **Variables** tab, add:

| Variable | Value |
|---|---|
| `SECRET_KEY` | any long random string, e.g. `openssl rand -hex 32` |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | your Railway domain, e.g. `breathe-esg-production.up.railway.app` |

> `DATABASE_URL` is set automatically by Railway when you add the Postgres database.

**5. Get your URL**

Railway → your service → **Settings** → **Domains** → click **Generate Domain**

Your live URL will be something like: `https://breathe-esg-production.up.railway.app`

Open it — you should see the Breathe ESG app. Load the sample data through the Ingest page to demo it.

### Environment variables summary

| Variable | Required | Notes |
|---|---|---|
| `SECRET_KEY` | Yes | Long random string. Never commit this. |
| `DEBUG` | Yes | Set to `False` in production |
| `ALLOWED_HOSTS` | Yes | Your Railway domain (no `https://`) |
| `DATABASE_URL` | Auto | Railway sets this when you add Postgres |

### If the build fails

Check the **Build Logs** in Railway. Common issues:

| Error | Fix |
|---|---|
| `npm: command not found` | Railway auto-detects Nixpacks — check `nixpacks.toml` is committed |
| `ModuleNotFoundError: No module named 'dj_database_url'` | Make sure `requirements.txt` is committed with all 7 packages |
| `collectstatic` fails | Make sure `backend/staticfiles/` is NOT committed (it's in `.gitignore`) |
| App loads but API returns 500 | Check Railway **Logs** tab — usually a missing env variable |
| `/dashboard` shows 404 | The SPA catch-all is in `urls.py` — make sure it's committed |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'rest_framework'` | Activate venv: `source venv/bin/activate` |
| `OperationalError: no such table: esg_tenant` | Run `python manage.py migrate` |
| Browser shows blank page | Check backend is running on port 8000 |
| Dashboard shows no records after upload | Make sure you selected the tenant from the top-right dropdown |
| Port 8000 already in use | `python manage.py runserver 8001` then update proxy in `frontend/vite.config.js`: change `8000` to `8001` |
| File upload fails with an error banner | Check the backend terminal — the full Python traceback is printed there |
| Vite shows `ENOENT` or import error | `cd frontend && npm install` again |

---

## Project layout (for reference)

```
backend/
├── breathe/              Django project config (settings, urls, wsgi)
├── esg/
│   ├── models.py         All 6 models: Tenant, DataSource, IngestionJob,
│   │                     RawRecord, ActivityRecord, ActivityEditLog
│   ├── parsers/
│   │   ├── sap.py        SAP CSV parser
│   │   ├── utility.py    Utility CSV parser
│   │   └── travel.py     Travel JSON parser
│   ├── serializers.py    DRF serializers
│   ├── views.py          ViewSets + DashboardSummaryView
│   └── urls.py           API URL routing
├── migrations/           Auto-generated, committed — migrate just works
├── requirements.txt
└── sample_data/          sample_sap.csv, sample_utility.csv, sample_travel.json

frontend/
├── src/
│   ├── App.jsx           Sidebar + routing
│   ├── api.js            All fetch calls in one place
│   └── components/
│       ├── IngestPage.jsx  Tenant selector + file upload + job result
│       ├── Dashboard.jsx   Metric cards + filterable table
│       └── ReviewModal.jsx Editable fields + raw JSON + edit log + approve
├── vite.config.js        Proxies /api → localhost:8000
└── tailwind.config.js
```
