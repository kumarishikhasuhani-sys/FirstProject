import csv
import hashlib
import io
import json
from datetime import datetime

DATE_FORMATS = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d']


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


def _normalize_electricity(qty, unit):
    unit = (unit or '').strip().upper()
    if unit == 'MWH':
        return float(qty) * 1000, 'kWh'
    if unit in ('KWH', 'KWH'):
        return float(qty), 'kWh'
    return float(qty), unit


def parse(file_bytes, source_type='UTILITY'):
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
            activity_data['scope'] = 'SCOPE_2'
            activity_data['category'] = 'ELECTRICITY'

            # Billing period
            bill_start = _parse_date(row.get('BILL_START', ''))
            bill_end = _parse_date(row.get('BILL_END', ''))
            if bill_start:
                activity_data['period_start'] = bill_start
                activity_data['activity_date'] = bill_start
            if bill_end:
                activity_data['period_end'] = bill_end

            if bill_start and bill_end:
                days = (bill_end - bill_start).days
                if days > 40:
                    flags.append('LONG_BILLING_PERIOD')

            # Meter / site
            meter_id = row.get('METER_ID', '').strip()
            if meter_id:
                activity_data['meter_id'] = meter_id
            site_name = row.get('SITE_NAME', '').strip()
            if site_name:
                activity_data['facility_name'] = site_name

            # Consumption
            consumption_str = row.get('CONSUMPTION', '').strip()
            unit = row.get('UNIT', '').strip()
            if consumption_str:
                qty = float(consumption_str)
                activity_data['quantity'] = qty
                activity_data['unit_original'] = unit

                if qty < 0:
                    flags.append('NEGATIVE_QUANTITY')

                norm_qty, norm_unit = _normalize_electricity(qty, unit)
                activity_data['quantity_normalized'] = norm_qty
                activity_data['unit_normalized'] = norm_unit
            else:
                flags.append('MISSING_QUANTITY')

            # Cost
            amount_str = row.get('TOTAL_AMOUNT', '').strip()
            currency = row.get('CURRENCY', '').strip()
            if amount_str:
                activity_data['cost_amount'] = float(amount_str)
                if currency:
                    activity_data['cost_currency'] = currency
                else:
                    flags.append('MISSING_CURRENCY')

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
