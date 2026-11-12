"""Separate ASIN storage; preserves legacy barcode tables unchanged."""
import os
from persistent_store import _connection
from asin_research import validate_asin, validate_marketplace

FIELDS = ('observed_at_utc','asin','marketplace','name','ean_upc','source','source_url',
          'amazon_sales_known','amazon_price_known','amazon_eligibility_known')

def _init(conn):
    with conn.cursor() as cur:
        cur.execute('''CREATE TABLE IF NOT EXISTS asin_identity_observations (
            observed_at_utc TEXT NOT NULL, asin TEXT NOT NULL, marketplace TEXT NOT NULL,
            name TEXT NOT NULL, ean_upc TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL, source_url TEXT NOT NULL DEFAULT '',
            amazon_sales_known BOOLEAN NOT NULL DEFAULT FALSE,
            amazon_price_known BOOLEAN NOT NULL DEFAULT FALSE,
            amazon_eligibility_known BOOLEAN NOT NULL DEFAULT FALSE,
            PRIMARY KEY (source, asin, marketplace, observed_at_utc))''')

def save_asin_observations(records, url=None):
    url = url or os.environ.get('DATABASE_URL', '')
    if not url:
        raise RuntimeError('DATABASE_URL not configured.')
    with _connection(url) as conn:
        _init(conn)
        inserted = 0
        with conn.cursor() as cur:
            for r in records:
                validate_asin(r.get('asin'))
                validate_marketplace(r.get('marketplace'))
                if not r.get('observed_at_utc') or not r.get('source') or not r.get('name'):
                    raise ValueError('ASIN record missing required fields.')
                if any(r.get(k) not in (False, 'False', 'false', 0, None, '') for k in FIELDS[-3:]):
                    raise ValueError('Identity records cannot claim Amazon verification.')
                values = [str(r.get(k) or '') for k in FIELDS[:7]] + [False, False, False]
                cur.execute('''INSERT INTO asin_identity_observations
                    (observed_at_utc,asin,marketplace,name,ean_upc,source,source_url,
                     amazon_sales_known,amazon_price_known,amazon_eligibility_known)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (source,asin,marketplace,observed_at_utc) DO NOTHING''', values)
                inserted += cur.rowcount
        return inserted

def load_asin_observations(url=None, limit=10000):
    url = url or os.environ.get('DATABASE_URL', '')
    if not url:
        raise RuntimeError('DATABASE_URL not configured.')
    if not isinstance(limit, int) or not 1 <= limit <= 10000:
        raise ValueError('limit must be 1–10000.')
    with _connection(url) as conn:
        _init(conn)
        with conn.cursor() as cur:
            cur.execute('''SELECT observed_at_utc,asin,marketplace,name,ean_upc,source,source_url,
                           amazon_sales_known,amazon_price_known,amazon_eligibility_known
                           FROM asin_identity_observations ORDER BY observed_at_utc DESC LIMIT %s''', (limit,))
            return [dict(zip(FIELDS, row)) for row in cur.fetchall()]
