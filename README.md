# Breathe ESG — Data Ingestion Platform

A full-stack prototype for ingesting heterogeneous ESG data (SAP, utilities, travel), normalising it into Scope 1/2/3 activity records, and providing an analyst review/approval workflow with a complete audit trail.

## Stack

| Layer | Tech |
|---|---|
| Backend | Django 4.2 + Django REST Framework + SQLite |
| Frontend | React 19 + Vite + Tailwind CSS |

## Quick Start

### Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # starts on http://localhost:5173
```

### Sample data

Three sample files are in `backend/sample_data/`:

| File | Source |
|---|---|
| `sample_sap.csv` | SAP fuel + procurement export |
| `sample_utility.csv` | Electricity meter billing CSV |
| `sample_travel.json` | Flight / hotel / ground JSON |

Upload them via the **Ingest Data** page in the UI or directly via API:

```bash
curl -X POST http://localhost:8000/api/ingestions/ \
  -F "tenant_id=<uuid>" \
  -F "source_type=SAP" \
  -F "file=@backend/sample_data/sample_sap.csv"
```

## API reference

| Method | Endpoint | Description |
|---|---|---|
| GET/POST | `/api/tenants/` | List / create tenants |
| GET/POST | `/api/ingestions/` | List / trigger ingestion |
| GET | `/api/ingestions/:id/` | Job status + counters |
| GET | `/api/activities/` | List records (filters: `tenant_id`, `status`, `source_type`, `suspicious`) |
| GET | `/api/activities/:id/` | Record detail + raw payload + edit log |
| PATCH | `/api/activities/:id/` | Edit fields (pre-approval only) |
| POST | `/api/activities/:id/approve/` | Lock record as approved |
| POST | `/api/activities/:id/reject/` | Reject record |
| GET | `/api/dashboard/summary/` | Aggregated counts |

## Project layout

```
breathe-esg/
├── backend/
│   ├── esg/
│   │   ├── models.py          # Tenant, DataSource, IngestionJob, RawRecord, ActivityRecord, ActivityEditLog
│   │   ├── parsers/
│   │   │   ├── sap.py         # CSV parser: fuel + procurement
│   │   │   ├── utility.py     # CSV parser: electricity meters
│   │   │   └── travel.py      # JSON parser: flights, hotels, ground
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   └── sample_data/
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── api.js
│       └── components/
│           ├── IngestPage.jsx
│           ├── Dashboard.jsx
│           └── ReviewModal.jsx
├── MODEL.md
├── DECISIONS.md
├── TRADEOFFS.md
└── SOURCES.md
```
