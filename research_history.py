"""Validated operator-entered product identity records and observed timelines.

Identity metadata is not evidence of Amazon demand, price, eligibility or sales.
"""
from datetime import datetime, timezone
from collections import Counter
from catalogue_sources import validate_barcode

MAX_TEXT = 300


def manual_observation(barcode, name, brand='', quantity='', source_url='', at=None):
    barcode = validate_barcode(barcode)
    name = str(name).strip()
    if not name or len(name) > MAX_TEXT:
        raise ValueError('Product name must be 1–300 characters.')
    fields = [str(value).strip() for value in (brand, quantity, source_url)]
    if any(len(value) > 1000 for value in fields):
        raise ValueError('A text field is too long.')
    if fields[2] and not fields[2].startswith(('https://', 'http://')):
        raise ValueError('Source URL must start with https:// or http://.')
    at = at or datetime.now(timezone.utc)
    if at.tzinfo is None:
        raise ValueError('Observation time must include timezone.')
    return {
        'observed_at_utc': at.astimezone(timezone.utc).isoformat(),
        'barcode': barcode, 'name': name, 'brand': fields[0],
        'quantity': fields[1], 'source': 'Operator documented',
        'source_url': fields[2], 'amazon_sales_known': False,
        'amazon_price_known': False, 'amazon_eligibility_known': False,
    }


def timeline(records):
    """Counts independent dated identity observations; not demand or sales."""
    valid = [r for r in records if r.get('barcode') and r.get('observed_at_utc')]
    counts = Counter((r['barcode'], str(r['observed_at_utc'])[:7]) for r in valid)
    return [{'barcode': barcode, 'month': month, 'identity_observations': count}
            for (barcode, month), count in sorted(counts.items())]


def validate_import_rows(rows):
    """Reject incomplete/unverified or fabricated-looking identity imports."""
    from datetime import datetime
    from catalogue_sources import FIELDS
    if len(rows) > 10000:
        raise ValueError('Maximum 10,000 CSV rows per import.')
    validated = []
    for row in rows:
        if not all(field in row for field in FIELDS):
            raise ValueError('Missing required V1.8 catalogue columns.')
        barcode = validate_barcode(row['barcode'])
        source = str(row['source']).strip()
        if not source or source == 'SYSTEM_TEST_ONLY':
            raise ValueError('Missing or prohibited source.')
        at = datetime.fromisoformat(str(row['observed_at_utc']).replace('Z', '+00:00'))
        if at.tzinfo is None or at > datetime.now(timezone.utc):
            raise ValueError('Observation date must have timezone and cannot be in the future.')
        for key in ('amazon_sales_known', 'amazon_price_known', 'amazon_eligibility_known'):
            if str(row[key]).strip().lower() not in ('false', '0', '', 'none', 'nan'):
                raise ValueError('Identity records cannot claim Amazon verification.')
        validated.append({
            'observed_at_utc': at.astimezone(timezone.utc).isoformat(),
            'barcode': barcode, 'name': str(row['name'])[:300],
            'brand': str(row['brand'])[:300], 'quantity': str(row['quantity'])[:300],
            'source': source[:300], 'source_url': str(row['source_url'])[:1000],
            'amazon_sales_known': False, 'amazon_price_known': False,
            'amazon_eligibility_known': False,
        })
    return validated
