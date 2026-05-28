import csv
import hashlib
import io
import json
from datetime import datetime

KNOWN_PLANTS = {'DE01', 'IN05', 'US01', 'GB01'}

DATE_FORMATS = ['%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d', '%m/%d/%Y']


def _parse_date(date_str):
    if not date_str:
        return None
    date_str = date_str.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def _map_material_group(mg):
    mg = (mg or '').upper().strip()
    if mg.startswith('FUEL_'):
        return 'SCOPE_1', 'FUEL_COMBUSTION'
    if mg.startswith('PROC_'):
        return 'SCOPE_3', 'PROCUREMENT'
    return None, None


def _normalize_fuel_unit(qty, unit):
    unit = (unit or '').strip().upper()
    if unit == 'GAL':
        return float(qty) * 3.78541, 'L'
    if unit == 'L':
        return float(qty), 'L'
    return float(qty), unit


def parse(file_bytes, source_type='SAP'):
    text = file_bytes.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text))
    results = []

    for row_num, row in enumerate(reader, start=1):
        raw_payload = dict(row)
        row_hash = hashlib.sha256(
            json.dumps(raw_payload, sort_keys=True).encode()
        ).hexdigest()

        flags = []
        activity_data = {}
        parse_error = None

        try:
            # Date
            date = _parse_date(row.get('DOC_DATE', ''))
            if date:
                activity_data['activity_date'] = date

            # Scope + category from material group
            mg = row.get('MATERIAL_GROUP', '').strip()
            scope, category = _map_material_group(mg)
            if scope:
                activity_data['scope'] = scope
                activity_data['category'] = category
            else:
                flags.append('MISSING_SCOPE')

            # Plant / facility
            plant = row.get('PLANT', '').strip()
            activity_data['facility_id'] = plant
            if plant and plant not in KNOWN_PLANTS:
                flags.append('UNKNOWN_PLANT')

            # Quantity + unit
            qty_str = row.get('QUANTITY', '').strip()
            unit = row.get('UNIT', '').strip()

            if qty_str:
                qty = float(qty_str)
                activity_data['quantity'] = qty
                activity_data['unit_original'] = unit

                if qty < 0:
                    flags.append('NEGATIVE_QUANTITY')

                if category == 'FUEL_COMBUSTION':
                    norm_qty, norm_unit = _normalize_fuel_unit(qty, unit)
                    activity_data['quantity_normalized'] = norm_qty
                    activity_data['unit_normalized'] = norm_unit
                    if norm_qty > 1_000_000:
                        flags.append('ABSURD_FUEL_QUANTITY')
            else:
                if category == 'FUEL_COMBUSTION':
                    flags.append('MISSING_QUANTITY')

            # Cost
            amount_str = row.get('AMOUNT', '').strip()
            currency = row.get('CURRENCY', '').strip()
            if amount_str:
                activity_data['cost_amount'] = float(amount_str)
                if currency:
                    activity_data['cost_currency'] = currency
                else:
                    flags.append('MISSING_CURRENCY')

            # Procurement-specific
            if category == 'PROCUREMENT':
                activity_data['material_group'] = mg
                activity_data['item_description'] = row.get('GL_TEXT', '').strip()
                if amount_str:
                    activity_data['spend_amount'] = float(amount_str)
                    activity_data['spend_currency'] = currency

            parse_status = 'PARSED'

        except Exception as exc:
            parse_error = str(exc)
            parse_status = 'FAILED'

        activity_data['flags'] = flags

        results.append({
            'row_number': row_num,
            'raw_payload': raw_payload,
            'hash': row_hash,
            'parse_status': parse_status,
            'parse_error': parse_error,
            'activity_data': activity_data,
        })

    return results
