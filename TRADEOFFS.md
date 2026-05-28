# TRADEOFFS

## 1) No real API integrations (SAP OData / Concur/Navan OAuth)
I used file uploads to prove the ingestion + normalization + review + audit workflow within time.

## 2) No PDF utility bill parsing
CSV portal exports are both realistic and higher-signal; PDF extraction would dominate time and add brittleness.

## 3) No emissions factor engine
I focused on reliable activity normalization and auditability; factor versioning and CO2e computation would be the next layer.

## 4) Synchronous parsing
Parsing runs synchronously in the request-response cycle. For large files this would need a background task queue (Celery + Redis). The API response shape already includes counters to support async polling.

## 5) SQLite vs Postgres
SQLite for zero-config prototype; Postgres needed for production (concurrent writes, row-level locking for approval).
