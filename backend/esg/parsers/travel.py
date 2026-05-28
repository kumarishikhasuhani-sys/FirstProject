import hashlib
import json
from datetime import datetime

DATE_FORMATS = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']

CATEGORY_MAP = {
    'FLIGHT': 'FLIGHT',
    'HOTEL': 'HOTEL',
    'GROUND': 'GROUND',
}


def _parse_date(date_str):
    if not date_str:
        return None
    date_str = str(date_str).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def parse(file_bytes, source_type='TRAVEL'):
    records = json.loads(file_bytes.decode('utf-8'))
    if isinstance(records, dict):
        records = [records]

    results = []

    for row_num, record in enumerate(records, start=1):
        raw_payload = record
        row_hash = hashlib.sha256(
            json.dumps(raw_payload, sort_keys=True, default=str).encode()
        ).hexdigest()

        flags = []
        activity_data = {}
        parse_error = None

        try:
            activity_data['scope'] = 'SCOPE_3'

            trip_type = (record.get('type') or '').upper()
            category = CATEGORY_MAP.get(trip_type)
            if category:
                activity_data['category'] = category
                activity_data['travel_mode'] = trip_type
            else:
                flags.append('MISSING_SCOPE')

            # Date — differs by trip type
            if trip_type == 'FLIGHT':
                date = _parse_date(record.get('ticketed_date'))
                origin = record.get('origin', '').strip()
                destination = record.get('destination', '').strip()
                activity_data['origin'] = origin
                activity_data['destination'] = destination
                if not origin or not destination:
                    flags.append('MISSING_ROUTE')
                cabin = record.get('cabin', '').strip()
                if cabin:
                    activity_data['cabin_class'] = cabin
                dist = record.get('distance_km')
                if dist is not None:
                    activity_data['distance_km'] = float(dist)
                    activity_data['quantity'] = float(dist)
                    activity_data['unit_original'] = 'km'
                    activity_data['quantity_normalized'] = float(dist)
                    activity_data['unit_normalized'] = 'km'
                else:
                    flags.append('MISSING_DISTANCE')

            elif trip_type == 'HOTEL':
                date = _parse_date(record.get('check_in'))
                nights = record.get('nights')
                if nights is not None:
                    activity_data['nights'] = int(nights)
                    activity_data['quantity'] = float(nights)
                    activity_data['unit_original'] = 'nights'
                    activity_data['quantity_normalized'] = float(nights)
                    activity_data['unit_normalized'] = 'nights'
                city = record.get('city', '').strip()
                if city:
                    activity_data['facility_name'] = city

            elif trip_type == 'GROUND':
                date = _parse_date(record.get('ride_date'))
                dist = record.get('distance_km')
                if dist is not None:
                    activity_data['distance_km'] = float(dist)
                    activity_data['quantity'] = float(dist)
                    activity_data['unit_original'] = 'km'
                    activity_data['quantity_normalized'] = float(dist)
                    activity_data['unit_normalized'] = 'km'
                else:
                    flags.append('MISSING_DISTANCE')
                city = record.get('city', '').strip()
                if city:
                    activity_data['facility_name'] = city

            else:
                date = None

            if date:
                activity_data['activity_date'] = date

            # Cost
            amount = record.get('amount')
            currency = record.get('currency', '').strip()
            if amount is not None:
                activity_data['cost_amount'] = float(amount)
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
