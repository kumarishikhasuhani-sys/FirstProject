# SOURCES

## 1. SAP — fuel and procurement

### Format chosen: flat CSV extract (MB51 / ME2M style)

SAP exposes data four ways: IDoc (XML-based EDI messages), BAPI/RFC function calls, OData services (via SAP Gateway), and flat file extracts triggered from transactions like MB52 (stock overview), MB51 (material document list), or ME2M (purchase orders by material). I chose flat file extract because:

- It is the most common real-world handoff between an SAP team and a third party without a live integration agreement.
- IDocs require a receiver port and partner profile configured on the SAP side — not something a sustainability team sets up.
- OData requires SAP Gateway to be enabled and a service activated — often blocked by IT.
- The flat file captures the same messiness as the other formats without requiring auth infrastructure.

### What I learned about real SAP exports

SAP flat exports from MB51 or ME2M have specific characteristics:

- **Column names depend on SAP language/locale setting.** A German system will output `BUCHUNGSDATUM` instead of `BUDAT` (posting date), `WERK` instead of `PLANT`, `MENGE` instead of `QUANTITY`. I use English column names (typical in international clients' SAP configurations), justified in DECISIONS.md.
- **WERKS (plant code)** is a 4-character string that means nothing without the plant master table (T001W). A sustainability analyst receiving this file won't know if `DE01` is "Berlin factory" or "Munich depot" without a lookup. I model this as `facility_id` and flag unknown plant codes.
- **MEINS (unit of measure)** uses SAP internal codes: `L` for litres, `GAL` for US gallons, `KG`, `TO`, `EA` (each), `ST` (Stück = piece). The same physical item can appear in different units depending on the purchase order.
- **BUDAT (posting date)** format depends on SAP date format setting: `YYYYMMDD` in many exports, but portal downloads sometimes reformat to `DD.MM.YYYY` (German locale) or `MM/DD/YYYY`. I handle all three in the parser.
- **MATERIAL_GROUP (MATKL)** is a configurable grouping field. The `FUEL_*` / `PROC_*` prefix convention in my sample data reflects a client that has structured their material groups with a meaningful prefix — realistic for a company that has set up SAP MM properly.

### Sample data rationale

```
2026-04-02,DE01,FUEL_DIESEL  — ISO date format, known plant, fuel row
02.04.2026,DE01,PROC_IT      — German date format (DD.MM.YYYY), same plant, procurement
2026/04/05,IN05,FUEL_PETROL  — slash-separated date, different plant (India), quantity in GAL
2026-04-07,DE99,PROC_MRO     — unknown plant (DE99 not in lookup), missing quantity
```

Each row exercises a different realistic problem: date format variation, unit variation, missing plant lookup, and missing quantity. Row 4 (DE99) specifically tests the `UNKNOWN_PLANT` flag and the case where a procurement row has no quantity (spend-only lines are common in MRO purchasing).

### What would break in a real deployment

- **Plant master joins**: Every `WERKS` code needs a join to T001W to get facility name, address, and country — required for geographic Scope 1 reporting.
- **Material master joins**: The `MATKL` material group is a blunt instrument. Real Scope 1/3 classification often requires `MATNR` (material number) joined to the material master to get the correct emission factor.
- **Multi-currency**: SAP posts in local currency (WAERS). International clients have SAP posting in EUR, USD, INR, GBP on the same extract. FX normalization is not in scope here.
- **Batch sizes**: Real MB51 exports for a large manufacturer can be 500k+ rows per month. Synchronous parsing in a web request would time out.

---

## 2. Utility electricity

### Format chosen: portal CSV export

Utilities in Germany (EON, RWE, Vattenfall), the UK (National Grid, EDF), and India (BESCOM, TATA Power) all offer online portal access for business customers. The download options are typically PDF invoice or CSV/Excel export of meter readings. I chose CSV for the same reason as SAP flat file: it's the path of least resistance for a facilities team and captures the realistic data shape without requiring API access or PDF OCR.

The alternative — PDF bill parsing — would require an OCR pipeline. PDF layouts differ by utility, change with redesigns, and produce brittle extraction. Not worth it for a prototype where the goal is to demonstrate the normalization + review workflow.

Green Button (the US DOE standard for utility data exchange) and ESPI (Energy Services Provider Interface) offer structured XML/JSON exports, but adoption is fragmented, mostly US-focused, and typically requires customer-authorized API access.

### What I learned about real utility exports

- **Billing period vs calendar month**: Utilities read meters on a cycle, not on the 1st of each month. A "March" bill might cover 2026-02-28 to 2026-04-01. ESG teams frequently discover mid-year that their Q1 data actually spans into Q2, causing double-counting. I flag billing periods > 40 days as suspicious.
- **Unit variation**: Large industrial consumers are typically billed in MWh; small commercial in kWh. Some European utilities mix both on the same account (demand in kW, energy in kWh). I normalize everything to kWh.
- **Tariff structure**: The `TARIFF` column in my sample data (e.g. `GE-IND-TOU`) represents a time-of-use industrial tariff. In a real Scope 2 calculation, the tariff and billing period together determine whether to use a residual mix or supplier-specific emission factor.
- **Site vs meter**: One site can have multiple meters (sub-metering). My model stores `meter_id` and `facility_name` separately so this is captured, but I don't group multiple meters per site in this prototype.

### Sample data rationale

```
ELEC-7781, Berlin Plant A, 2026-03-15 to 2026-04-14  — 30 days, MWh, clean
ELEC-7782, Berlin Plant B, 2026-04-01 to 2026-04-30  — 29 days, kWh, clean
ELEC-9999, Unknown Site,   2026-04-01 to 2026-05-20  — 49 days, MWh → LONG_BILLING_PERIOD flag
```

Row 3 deliberately spans 49 days (crosses a calendar month boundary by 9 days) to trigger the suspicious flag. This is a real QA check Breathe ESG would want: a utility bill covering 7 weeks often means an estimated read was corrected mid-period.

### What would break in a real deployment

- **Multi-meter sites**: Grouping consumption across meters at the same site (for SECR/GHG inventory roll-up) requires a site master table.
- **Demand charges**: Large commercial/industrial bills have both energy (kWh) and demand (kW peak) charges. Energy charge is what matters for Scope 2; the model doesn't separate them.
- **Estimated vs actual reads**: Utilities sometimes bill estimated consumption and then correct it. An ESG system needs to handle corrections without double-counting.
- **Renewable energy certificates**: Scope 2 market-based method requires tracking RECs/GOs separately from the energy volume — different field entirely.

---

## 3. Corporate travel — flights, hotels, ground transport

### Format chosen: JSON file upload (Concur/Navan API-shaped)

Corporate travel data comes from T&E platforms: SAP Concur, Navan (formerly TripActions), Egencia, TravelPerk, or Amex GBT. All of them expose a REST API. Concur's v4 Expense API returns JSON objects per expense line; Navan's export endpoint returns a JSON array of trip objects with `type`, dates, amounts, and where available, route data.

I use file upload instead of live OAuth because:
- Live OAuth to Concur/Navan requires a registered app client ID, not something you set up in 4 days.
- The JSON shape of the file is identical to what the API would return — the ingestion parser works the same way.
- This is realistic: many clients set up a weekly scheduled export from their travel platform and drop the file into an SFTP or upload it to Breathe.

### What I learned about real travel data

- **Flights**: Concur expense reports include `origin_airport_code` and `destination_airport_code` (IATA 3-letter codes). Distance is sometimes present if the booking was made through the platform's booking tool; for manually-expensed tickets it is absent. When absent, Scope 3 Category 6 (business travel) flight emissions require deriving great-circle distance from IATA codes — a call to an airport distance API or a static lookup table. I flag missing distance.
- **Hotels**: Emission calculation for hotel stays uses nights × room nights emission factor (kgCO2e per room night). The city or country matters because factors differ significantly (e.g. Indian grid vs Scandinavian hydro). I store city and nights.
- **Ground transport**: Rental cars, taxis, ride-hailing (Uber for Business, Bolt Business). Navan tracks distance for ride-hail bookings; expense reports for taxi/rental often just have a cost. Missing distance is common and must be flagged.
- **Scope 3 sub-categories**: All three travel types are Scope 3 Category 6 (Business Travel) under the GHG Protocol. The distinction matters for the emission factor, not the scope number — different EFs per mode and cabin class.
- **Cabin class**: Business class flights have an uplift factor (~2×) vs economy. I store `cabin_class` for this reason.

### Sample data rationale

```json
T-1001: FLIGHT  DEL→BLR  1740km  ECONOMY  — known route, distance given, clean
T-1002: HOTEL   Bengaluru  3 nights        — standard hotel stay, no distance needed
T-1003: GROUND  Berlin  distance=null      — MISSING_DISTANCE flag, realistic for taxi expense
```

`T-1003` (the Berlin ground trip with null distance) is the key test case. A taxi expense on Concur will have city and amount but usually no distance unless the employee entered it or the booking was through Navan's ride-hail integration. This row deliberately triggers the `MISSING_DISTANCE` flag and lands in the analyst review queue.

### What would break in a real deployment

- **Multi-leg flights**: A DEL→DXB→LHR itinerary appears as two separate legs or sometimes one combined record. Emission calculation requires summing leg distances, not treating it as a single DEL→LHR flight.
- **Cancellations and refunds**: Concur expense reports include voided transactions. Without filtering these out, an analyst approving them inflates the Scope 3 inventory.
- **Distance derivation**: When `distance_km` is null for a flight, the production path is: look up IATA codes → geocode airports → compute great-circle distance → apply radiative forcing uplift. None of that is in scope here; I flag and surface it for manual review.
- **Currency**: Travel expenses come in the local currency of wherever the trip happened. The model stores `cost_amount` + `cost_currency` but doesn't convert to a reporting currency.
