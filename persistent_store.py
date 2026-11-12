"""Optional PostgreSQL-backed durable catalogue identity observations.

DATABASE_URL must point to a persistent PostgreSQL service. No writes to GitHub.
No Amazon sales, prices or eligibility are inferred from these records.
"""
import os
from urllib.parse import urlparse

FIELDS = ('observed_at_utc','barcode','name','brand','quantity','source','source_url',
          'amazon_sales_known','amazon_price_known','amazon_eligibility_known')


def configured(environ=None):
    env = os.environ if environ is None else environ
    return bool(env.get('DATABASE_URL', '').strip())


def _connection(url):
    from psycopg import connect
    parsed = urlparse(url)
    if parsed.scheme not in ('postgres', 'postgresql') or not parsed.hostname:
        raise ValueError('DATABASE_URL must be a PostgreSQL connection URL.')
    return connect(url, connect_timeout=8)


def _init(conn):
    with conn.cursor() as cur:
        cur.execute('''CREATE TABLE IF NOT EXISTS catalogue_identity_observations (
          observed_at_utc TEXT NOT NULL,
          barcode TEXT NOT NULL,
          name TEXT NOT NULL DEFAULT '',
          brand TEXT NOT NULL DEFAULT '',
          quantity TEXT NOT NULL DEFAULT '',
          source TEXT NOT NULL,
          source_url TEXT NOT NULL DEFAULT '',
          amazon_sales_known BOOLEAN NOT NULL DEFAULT FALSE,
          amazon_price_known BOOLEAN NOT NULL DEFAULT FALSE,
          amazon_eligibility_known BOOLEAN NOT NULL DEFAULT FALSE,
          PRIMARY KEY (source, barcode, observed_at_utc)
        )''')


def save_observations(records, url=None):
    """Insert sourced records idempotently; return inserted count."""
    url = url or os.environ.get('DATABASE_URL', '')
    if not url:
        raise RuntimeError('Persistent database not configured. Set DATABASE_URL in Render.')
    with _connection(url) as conn:
        _init(conn)
        inserted = 0
        with conn.cursor() as cur:
            for record in records:
                if not all(record.get(k) for k in ('observed_at_utc','barcode','source')):
                    raise ValueError('Observation missing timestamp, barcode or source.')
                if any(record.get(k) not in (False, 'False', 'false', 0, None, '')
                       for k in ('amazon_sales_known','amazon_price_known','amazon_eligibility_known')):
                    raise ValueError('Catalogue records cannot claim Amazon verification.')
                values = [str(record.get(k) or '') for k in FIELDS[:7]] + [False, False, False]
                cur.execute('''INSERT INTO catalogue_identity_observations
                    (observed_at_utc,barcode,name,brand,quantity,source,source_url,
                     amazon_sales_known,amazon_price_known,amazon_eligibility_known)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (source,barcode,observed_at_utc) DO NOTHING''', values)
                inserted += cur.rowcount
        return inserted


def load_observations(url=None, limit=10000):
    url = url or os.environ.get('DATABASE_URL', '')
    if not url:
        raise RuntimeError('Persistent database not configured. Set DATABASE_URL in Render.')
    if not isinstance(limit, int) or not 1 <= limit <= 10000:
        raise ValueError('limit must be between 1 and 10000')
    with _connection(url) as conn:
        _init(conn)
        with conn.cursor() as cur:
            cur.execute('''SELECT observed_at_utc,barcode,name,brand,quantity,source,source_url,
                        amazon_sales_known,amazon_price_known,amazon_eligibility_known
                        FROM catalogue_identity_observations
                        ORDER BY observed_at_utc DESC LIMIT %s''', (limit,))
            return [dict(zip(FIELDS, row)) for row in cur.fetchall()]
