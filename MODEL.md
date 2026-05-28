# MODEL

## Goals
- Ingest heterogeneous client data (SAP, utilities, travel) while preserving complete source-of-truth.
- Normalize into a consistent activity model with explicit Scope 1/2/3 classification and unit normalization.
- Provide an analyst review workflow with immutable locking for audit and a full edit trail.

## Core design: two-layer ingestion

Ingestion produces two kinds of rows:

1. **`RawRecord`** — immutable. Written once, never mutated. Stores the exact payload from the source file, the row number, a SHA-256 hash of the payload (for deduplication/idempotency), and the parse outcome (`PARSED` or `FAILED`). If we re-ingest the same file we can detect duplicates by hash.

2. **`ActivityRecord`** — normalized, analyst-reviewable. Created only when a RawRecord parses successfully. Contains the structured, typed fields an analyst needs: scope, category, quantities in original *and* normalized units, attribution, and suspicious flags. Analysts can edit this before approval; the RawRecord is never touched.

This two-layer design is the core judgment call. A single flat table would lose the original shape. A single document-style store would make normalization and querying hard. Keeping them 1:1-linked via a FK gives lineage, auditability, and clean querying.

---

## Entities

### Tenant
```
id (UUID)        — UUID not auto-increment; safe to expose in URLs, no enumeration risk
name (unique)
created_at
```
Every other table has a `tenant` FK. All API list endpoints accept `?tenant_id=` for scoping. No cross-tenant leakage is possible because filters are applied at the ORM layer before serialization.

### DataSource
```
id (UUID)
tenant (FK)
type: SAP | UTILITY | TRAVEL
name
config (JSON)    — reserved for per-source column mappings, plant code lookups, unit overrides
created_at
```
`config` is a JSON field intentionally left flexible. In production it would carry the plant-code-to-facility mapping for SAP, tariff zone overrides for utility, or travel category to Scope 3 sub-category mappings. For the prototype it is unused but the field exists so the model is extensible without a migration.

### IngestionJob
```
id (UUID)
tenant (FK), data_source (FK)
status: UPLOADED → PARSING → PARSED | FAILED | PARTIALLY_PARSED
uploaded_file    — original file kept on disk for audit
started_at, finished_at
created_by       — email/name of the analyst who triggered the upload
total_rows, parsed_rows, failed_rows, suspicious_rows  — counters for dashboard
created_at
```
`PARTIALLY_PARSED` is a distinct status because a file that is 95% good is very different from one that is 100% failed. Analysts need to know to check the failed rows without discarding the good ones.

### RawRecord
```
id (UUID)
tenant (FK), ingestion_job (FK)
row_number (int)             — 1-based, matches CSV row or JSON array index
source_type (string)         — SAP / UTILITY / TRAVEL
raw_payload (JSON)           — exact dict from the source, key names preserved
hash (SHA-256 hex)           — SHA-256 of JSON-serialized payload, sorted keys; used for deduplication
parse_status: PARSED | FAILED
parse_error (text, nullable) — full exception string if parsing failed
created_at
```

`raw_payload` stores the exact original row. If an analyst later disputes a normalized value, you can always show them exactly what the source said. The `hash` field means re-uploading the same file won't create duplicate ActivityRecords (future work: enforce uniqueness constraint per DataSource).

### ActivityRecord
```
id (UUID)
tenant (FK), ingestion_job (FK), raw_record (OneToOne FK)
status: PENDING_REVIEW | APPROVED | REJECTED
locked_at (datetime, nullable)   — set on approval, signals immutability
locked_by (string, nullable)     — analyst name/email at time of approval

# Scope & category
scope:    SCOPE_1 | SCOPE_2 | SCOPE_3
category: FUEL_COMBUSTION | ELECTRICITY | PROCUREMENT | FLIGHT | HOTEL | GROUND

# Quantities — both original and normalized are stored
activity_date (date)
period_start, period_end (date, nullable)   — for billing-period-based sources (utility)
quantity (decimal)              — original value from source
unit_original (string)          — e.g. "GAL", "MWh", "km"
quantity_normalized (decimal)   — converted value
unit_normalized (string)        — canonical unit: "L", "kWh", "km"

# Attribution (all nullable — not every source provides all fields)
facility_id, facility_name, meter_id, vendor
cost_amount, cost_currency
country, notes

# Travel-specific (nullable)
travel_mode: AIR | HOTEL | GROUND
origin, destination (airport/city codes)
distance_km, cabin_class, nights

# Procurement-specific (nullable)
material_group, spend_amount, spend_currency, item_description

# Flags & audit
flags (JSON array of strings)   — e.g. ["MISSING_SCOPE", "LONG_BILLING_PERIOD"]
edited_fields (JSON)            — tracks which fields have ever been manually edited
created_at, updated_at
```

**Why store both original and normalized quantity?** The analyst needs to verify the normalization was correct. Showing only the normalized value hides errors. Showing only the original makes it impossible to compare across sources. Storing both and flagging the unit explicitly gives full transparency.

**Why `OneToOne` FK from ActivityRecord to RawRecord?** A RawRecord either parsed into one ActivityRecord or it didn't. There's never a fan-out scenario (one raw row → multiple activity rows) in this model. OneToOne enforces that constraint at the DB level and makes the join trivial.

### ActivityEditLog
```
id (UUID)
tenant (FK), activity_record (FK)
edited_by (string)
edited_at (auto timestamp)
before (JSON)   — snapshot of changed fields before edit
after (JSON)    — snapshot of changed fields after edit
reason (text, nullable)
```

Only changed fields are stored in `before`/`after` — not the entire record. This keeps the log readable and avoids bloated JSON on large records. Edits are only possible before approval (`locked_at` is null); once approved the record is immutable and the API returns 400 on PATCH.

---

## Multi-tenancy
Every table has a `tenant` FK. Every API query filters by `tenant_id`. A tenant cannot see or modify another tenant's data because the ORM queryset is always scoped before serialization. In production this would be enforced via a middleware that injects `tenant_id` from the JWT claim.

## Scope 1/2/3 mapping
| Source | Category | Scope |
|---|---|---|
| SAP MATERIAL_GROUP starts with `FUEL_` | FUEL_COMBUSTION | Scope 1 |
| SAP MATERIAL_GROUP starts with `PROC_` | PROCUREMENT | Scope 3 |
| Utility (electricity) | ELECTRICITY | Scope 2 |
| Travel FLIGHT | FLIGHT | Scope 3 |
| Travel HOTEL | HOTEL | Scope 3 |
| Travel GROUND | GROUND | Scope 3 |

## Unit normalization rules
| Original unit | Normalized unit | Conversion |
|---|---|---|
| GAL (gallons) | L | × 3.78541 |
| MWh | kWh | × 1000 |
| L, kWh, km | unchanged | 1:1 |

## Suspicious flags (rules encoded in parsers)
| Flag | Trigger |
|---|---|
| `MISSING_SCOPE` | MATERIAL_GROUP not in known prefixes |
| `UNKNOWN_PLANT` | Plant code not in known lookup set |
| `NEGATIVE_QUANTITY` | Parsed quantity < 0 |
| `MISSING_QUANTITY` | Fuel row has no quantity |
| `LONG_BILLING_PERIOD` | `BILL_END - BILL_START > 40 days` |
| `ABSURD_FUEL_QUANTITY` | Normalized quantity > 1,000,000 L |
| `MISSING_CURRENCY` | Amount present but no currency |
| `MISSING_DISTANCE` | GROUND/FLIGHT row has no distance_km |
| `MISSING_ROUTE` | FLIGHT row missing origin or destination |

## What's not in this model (intentional)
- **Emission factors**: The model is ready for them (normalized quantities are the input), but factor versioning is a separate concern with its own auditability requirements.
- **User/auth table**: Prototype uses a plain string `created_by`/`locked_by`. Production needs a proper auth model.
- **Versioned amendments**: Once approved, this model allows no further edits. A real system may need an "amendment" flow that creates a new ActivityRecord linked to the same RawRecord.

## Next additions
- Emission factors (versioned by year, region, source) and computed CO2e fields on ActivityRecord.
- Real entity resolution: plant codes, meter IDs, and suppliers resolved against master data tables.
- True async ingestion: Celery + Redis task queue so large files don't block the HTTP response.
