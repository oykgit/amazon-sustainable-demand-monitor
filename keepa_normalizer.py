"""Offline Keepa CSV history normalizer. No provider calls or database writes.

Keepa timestamps are minutes since 2011-01-01 UTC; price units for UK
are minor currency units (pence). Sales rank is ordinal, not sales volume.
"""
from datetime import datetime, timedelta, timezone
import math
import re

EPOCH = datetime(2011, 1, 1, tzinfo=timezone.utc)
MAX_POINTS = 10000
FIELDS = {'AMAZON': ('AMAZON_PRICE_GBP', 'GBP'), 'NEW': ('NEW_PRICE_GBP', 'GBP'), 'SALES': ('SALES_RANK', None)}
ASIN_PATTERN = re.compile(r'^[A-Z0-9]{10}$')


def normalize(payload, asin, market='UK', fx_gbp_to_eur=None):
    """Convert a *supplied* Keepa product JSON object to dated observations.

    Does not verify that the payload came from Keepa. If supplied, FX rate is
    operator-supplied and must be independently documented before use.
    """
    asin = str(asin).strip().upper()
    if not ASIN_PATTERN.fullmatch(asin):
        raise ValueError('ASIN must contain exactly ten ASCII letters or digits')
    if market != 'UK':
        raise ValueError('V1.25 supports only Keepa UK domain; Ireland is not a separate Keepa Amazon domain')
    if not isinstance(payload, dict):
        raise ValueError('Expected one Keepa product JSON object')
    if payload.get('asin') is not None and payload['asin'] != asin:
        raise ValueError('Payload ASIN does not match requested ASIN')
    csv = payload.get('csv')
    if not isinstance(csv, list):
        raise ValueError('Keepa product must contain a csv array')
    if fx_gbp_to_eur is not None:
        if isinstance(fx_gbp_to_eur, bool):
            raise ValueError('FX rate must be positive')
        try:
            fx_gbp_to_eur = float(fx_gbp_to_eur)
        except (ValueError, TypeError):
            raise ValueError('FX rate must be numeric') from None
        if not math.isfinite(fx_gbp_to_eur) or fx_gbp_to_eur <= 0:
            raise ValueError('FX rate must be positive and finite')
    out = []
    omitted = {'unavailable_or_out_of_stock': 0, 'invalid_time': 0}
    now = datetime.now(timezone.utc) + timedelta(days=1)
    for idx, key in [(0, 'AMAZON'), (1, 'NEW'), (3, 'SALES')]:
        if idx >= len(csv) or csv[idx] is None:
            continue
        arr = csv[idx]
        if not isinstance(arr, list) or len(arr) % 2:
            raise ValueError(f'{key} history must be an even-length list of timestamp/value pairs')
        if len(arr) // 2 > MAX_POINTS:
            raise ValueError(f'{key} history exceeds {MAX_POINTS} points')
        kind, currency = FIELDS[key]
        for i in range(0, len(arr), 2):
            stamp, val = arr[i:i+2]
            if isinstance(stamp, bool) or not isinstance(stamp, (int, float)) or not math.isfinite(stamp) or stamp < 0:
                raise ValueError(f'{key} has invalid Keepa minute timestamp')
            if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val) or not float(val).is_integer():
                raise ValueError(f'{key} has invalid observation value')
            if val in (-1, -2):
                omitted['unavailable_or_out_of_stock'] += 1
                continue
            if val <= 0:
                omitted['unavailable_or_out_of_stock'] += 1
                continue
            try:
                moment = EPOCH + timedelta(minutes=stamp)
            except (OverflowError, ValueError):
                raise ValueError(f'{key} timestamp out of range') from None
            if moment > now:
                omitted['invalid_time'] += 1
                continue
            observed = {'asin': asin, 'market': market, 'observed_at_utc': moment.isoformat(),
                        'observed_date': moment.date().isoformat(), 'source_field': key,
                        'evidence_type': kind, 'value': (val if currency is None else round(val / 100, 2)),
                        'currency': currency, 'source_provider': 'Keepa (operator-supplied JSON; unverified)'}
            if currency and fx_gbp_to_eur is not None:
                observed['price_eur_operator_estimate'] = round(val / 100 * fx_gbp_to_eur, 2)
                observed['fx_rate_operator_supplied'] = fx_gbp_to_eur
            out.append(observed)
    out.sort(key=lambda r: (r['observed_at_utc'], r['source_field']))
    return {'mode': 'KEEPA_JSON_OFFLINE_NORMALIZATION_ONLY', 'asin': asin, 'market': market,
            'observations': out, 'count': len(out), 'omitted': omitted,
            'network_requests': 0, 'database_writes': 0, 'purchases_enabled': False,
            'provider_origin_authenticated': False, 'amazon_sales_volume_verified': False,
            'historical_demand_verified': False,
            'note': 'Keepa timestamps converted to UTC; GBP prices are pence/100. Rank is not sales volume. Supplied JSON is not independently authenticated. No FX verification.'}
