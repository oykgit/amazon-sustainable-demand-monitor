"""Operator-entered ASIN price/cost snapshots. No live Amazon data or buying signals."""
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from asin_research import validate_asin, validate_marketplace
from persistent_store import _connection

FIELDS = ('observed_at_utc','asin','marketplace','selling_price_eur','supplier_cost_eur',
          'referral_pct','fulfilment_eur','inbound_eur','other_eur','returns_pct',
          'source_note','estimated_profit_eur','estimated_roi_pct')

def amount(value, name, upper=1000000):
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f'{name} must be a number.')
    if not n.is_finite() or n < 0 or n > upper:
        raise ValueError(f'{name} must be between 0 and {upper}.')
    return n

def build_snapshot(asin, marketplace, price, cost, referral_pct, fulfilment, inbound,
                   other, returns_pct, source_note, at=None):
    asin = validate_asin(asin)
    marketplace = validate_marketplace(marketplace)
    note = str(source_note).strip()
    if not note or len(note) > 500:
        raise ValueError('A source note of 1–500 characters is required.')
    p = amount(price, 'Price'); c = amount(cost, 'Supplier cost')
    ref = amount(referral_pct, 'Referral percent', 100)
    ful = amount(fulfilment, 'Fulfilment'); inbound = amount(inbound, 'Inbound')
    other = amount(other, 'Other costs'); ret = amount(returns_pct, 'Returns percent', 100)
    profit = p - c - p * ref / 100 - ful - inbound - other - p * ret / 100
    roi = profit / c * 100 if c else None
    at = at or datetime.now(timezone.utc)
    if at.tzinfo is None:
        raise ValueError('Observation timestamp must be timezone-aware.')
    return dict(zip(FIELDS, [at.astimezone(timezone.utc).isoformat(), asin, marketplace,
        float(p),float(c),float(ref),float(ful),float(inbound),float(other),float(ret),
        note,float(round(profit,2)),None if roi is None else float(round(roi,2))]))

def _init(conn):
    with conn.cursor() as cur:
        cur.execute('''CREATE TABLE IF NOT EXISTS asin_price_snapshots (
          id BIGSERIAL PRIMARY KEY, observed_at_utc TEXT NOT NULL,
          asin TEXT NOT NULL, marketplace TEXT NOT NULL,
          selling_price_eur NUMERIC NOT NULL, supplier_cost_eur NUMERIC NOT NULL,
          referral_pct NUMERIC NOT NULL, fulfilment_eur NUMERIC NOT NULL,
          inbound_eur NUMERIC NOT NULL, other_eur NUMERIC NOT NULL,
          returns_pct NUMERIC NOT NULL, source_note TEXT NOT NULL,
          estimated_profit_eur NUMERIC NOT NULL, estimated_roi_pct NUMERIC,
          UNIQUE (asin, marketplace, observed_at_utc, source_note))''')

def save_snapshot(snapshot, url=None):
    url = url or os.environ.get('DATABASE_URL','')
    if not url: raise RuntimeError('DATABASE_URL not configured.')
    with _connection(url) as conn:
        _init(conn)
        with conn.cursor() as cur:
            cur.execute('''INSERT INTO asin_price_snapshots (''' + ','.join(FIELDS) + ''')
                VALUES (''' + ','.join(['%s'] * len(FIELDS)) + ''')
                ON CONFLICT (asin,marketplace,observed_at_utc,source_note) DO NOTHING''',
                tuple(snapshot[k] for k in FIELDS))
            return cur.rowcount

def load_snapshots(asin=None, marketplace=None, url=None, limit=1000):
    url = url or os.environ.get('DATABASE_URL','')
    if not url: raise RuntimeError('DATABASE_URL not configured.')
    if asin: asin = validate_asin(asin)
    if marketplace: marketplace = validate_marketplace(marketplace)
    if not isinstance(limit,int) or not 1 <= limit <= 10000: raise ValueError('Invalid limit.')
    with _connection(url) as conn:
        _init(conn)
        clauses=[]; params=[]
        if asin: clauses.append('asin = %s'); params.append(asin)
        if marketplace: clauses.append('marketplace = %s'); params.append(marketplace)
        where = (' WHERE ' + ' AND '.join(clauses)) if clauses else ''
        with conn.cursor() as cur:
            cur.execute('SELECT ' + ','.join(FIELDS) + ' FROM asin_price_snapshots' + where +
                        ' ORDER BY observed_at_utc DESC LIMIT %s', tuple(params+[limit]))
            return [dict(zip(FIELDS, row)) for row in cur.fetchall()]
