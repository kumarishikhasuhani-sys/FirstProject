# DECISIONS

## 1) SAP: flat CSV file upload, not IDoc or OData

**Ambiguity:** SAP exposes data four ways — IDoc (EDI-style XML), BAPI/RFC calls, OData services, and flat file extracts. Which do we target?

**Chosen:** Flat CSV export, uploaded by the analyst.

**Why:**
- IDocs require a configured receiver port and partner profile on the SAP system — not something a sustainability team sets up without IT involvement. Realistic for a managed integration, not for a prototype handoff.
- OData requires SAP Gateway to be enabled and a specific service activated (`/sap/opu/odata/sap/MM_MATDOC_SRV` etc.). Often blocked by IT security policy.
- Flat file extracts from MB51 (material documents) or ME2M (PO line items) are a standard "download to Excel/CSV" flow any SAP user can do from the transaction menu. No IT involvement.
- The messiness is identical: date format variation, plant codes, SAP unit codes, missing master data — all present in the flat file.

**Subset handled:** Material documents with `MATERIAL_GROUP` matching `FUEL_*` prefix (Scope 1 combustion) and `PROC_*` prefix (Scope 3 procurement). The prefix convention reflects a client who has structured their SAP material group hierarchy — realistic for a manufacturing company with a proper MM setup.

**Ignored:** German column headers (I use English; justified by assuming client has SAP language set to EN, which is standard for multinational companies), IDoc structure, deep material master joins, multi-currency conversion.

**What I'd ask the PM:** Is there an SAP BASIS team at the client who can enable an OData service? If yes, a live pull is better long-term. If not, is there a scheduled batch job that can drop extracts to SFTP? That's the production version of this file upload flow.

---

## 2) Utility: portal CSV, not PDF or API

**Ambiguity:** Utility data comes as PDF bills, portal CSV exports, or (sometimes) a Green Button / ESPI API.

**Chosen:** Portal CSV download, uploaded by the analyst.

**Why:**
- PDF bill parsing requires OCR. Layout differs by utility provider, changes with redesigns, and produces brittle extraction with high error rates on numeric fields. Not appropriate when data integrity is critical (this goes to auditors).
- Green Button / ESPI XML is a US-specific standard with uneven adoption even there; the sample client has German and Indian facilities. Not a universal solution.
- Portal CSV is what facilities managers actually do. Every major European and Indian utility (EON, RWE, BESCOM, TATA Power) offers a CSV download of billing data in their business customer portal. The data shape is consistent: meter ID, site, billing period, consumption, unit, amount.

**Subset handled:** Single-phase electricity consumption per meter per billing period. Unit (kWh or MWh), billing period dates, meter ID, site name, total cost.

**Ignored:** Demand charges (kW peak), time-of-use tier breakdowns, sub-metering aggregation, RECs/GOs for market-based Scope 2, PDF bills.

---

## 3) Travel: JSON file upload, not live Concur/Navan OAuth

**Ambiguity:** Travel data can be pulled via Concur v4 OAuth API, Navan export endpoint, or exported as a file from the travel platform admin dashboard.

**Chosen:** JSON file upload (data shaped like a Concur/Navan API response).

**Why:**
- Live OAuth requires a registered client application on the travel platform — days of setup and security review, not something done in a sprint.
- The JSON shape of the file export is structurally identical to what an API call would return. The parser works identically; the ingestion mechanism is just "file" vs "HTTP GET."
- This is also the realistic production pattern for clients who set up a weekly scheduled export from their travel admin dashboard and upload it to Breathe.

**Subset handled:** Flights (with IATA codes, distance if available, cabin class), hotels (check-in/check-out, city, nights), ground transport (date, city, distance if available).

**Ignored:** Multi-leg itineraries as single records, cancellations/refunds, live OAuth polling.

---

## 4) Two-layer model: immutable RawRecord + editable ActivityRecord

**Ambiguity:** Should we store the original source row separately from the normalized version, or just normalize in place?

**Chosen:** Two separate tables, linked 1:1.

**Why:** Analysts need to be able to compare what they approved against what the source actually said. If we normalized in-place and a bug in the unit conversion passed review, there's no way to re-derive the correct value. The immutable RawRecord is the "receipt." It also enables re-parsing: if we fix a parser bug, we can re-create ActivityRecords from the existing RawRecords without re-uploading files.

---

## 5) Approval is a one-way lock, not versioned amendments

**Ambiguity:** Can an approved record ever be edited?

**Chosen:** Once approved, the record is immutable. The API returns 400 on PATCH to an approved record.

**Why:** The simplest model that satisfies the audit requirement. If auditors ever see a record, it should be frozen in time. Amendments are a more complex workflow (create a new record linked to the same RawRecord, mark the old one as superseded) that I'd build only if the PM confirms auditors need it.

**What I'd ask the PM:** Is there a correction workflow after audit submission? Some GHG reporting standards allow restated figures with documentation. If yes, I'd add an `AmendedBy` FK on ActivityRecord pointing to a replacement record.

---

## 6) SQLite for local dev, Postgres for production

**Chosen:** SQLite for the prototype.

**Why:** Zero setup. The entire DB is a single file. Switching to Postgres requires only a settings change (`DATABASES` in `settings.py`) and a `manage.py migrate`.

**Production concern:** SQLite doesn't handle concurrent writes well. The approval action (`POST /activities/:id/approve/`) and ingest (`POST /ingestions/`) both write. With multiple analysts, SQLite's table-level locking would cause contention. Postgres row-level locking solves this.

---

## Questions I would ask the PM before going further

1. **Approval semantics**: Is a locked record frozen forever, or is there a correction/amendment flow post-audit?
2. **File retention**: Do auditors require the original uploaded files to be kept indefinitely, or can they be purged after a retention period?
3. **Emission factors**: Is CO2e calculation in scope for the next sprint, or is this data pipeline + review the full product scope?
4. **Scale**: How many rows per file per client per month? 500-row SAP export vs 500k-row SAP export changes the sync/async parsing decision entirely.
5. **Auth**: Is there a user/auth system to integrate with, or is the "created_by"/"locked_by" string field sufficient for now?
6. **SAP client config**: Is there a SAP BASIS team at the client who can enable an OData service for a live pull, or is file upload the permanent mechanism?
