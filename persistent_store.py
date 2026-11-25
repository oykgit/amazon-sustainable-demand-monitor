"""Optional PostgreSQL-backed durable catalogue identity observations.

DATABASE_URL must point to a persistent PostgreSQL service. No writes to GitHub.
No Amazon sales, prices or eligibility are inferred from these records.
"""
import os
from urllib.parse import urlparse
from contextlib import contextmanager
from secure_database import database_transaction, DatabaseAccessError

FIELDS = ('observed_at_utc','barcode','name','brand','quantity','source','source_url',
          'amazon_sales_known','amazon_price_known','amazon_eligibility_known')


def configured(environ=None):
    env = os.environ if environ is None else environ
    return bool(env.get('DATABASE_URL', '').strip())


def _connection(url):
    if secure_storage_enabled():
        raise DatabaseAccessError("Legacy database path disabled in secure storage mode.")
    from psycopg import connect
    parsed = urlparse(url)
    if parsed.scheme not in ('postgres', 'postgresql') or not parsed.hostname:
        raise ValueError('DATABASE_URL must be a PostgreSQL connection URL.')
    return connect(url, connect_timeout=8)


def secure_storage_enabled():
    mode = os.getenv('COMMERCIAL_STORAGE_MODE', 'legacy')
    if mode not in ('legacy', 'secure'):
        raise DatabaseAccessError('Invalid commercial storage mode.')
    return mode == 'secure'


@contextmanager
def storage_transaction(role, url=None):
    """Explicit migration switch; never fall back after a secure-mode failure."""
    if role not in ('reader', 'ingestion'):
        raise DatabaseAccessError('Invalid storage role.')
    if secure_storage_enabled():
        with database_transaction(role) as conn:
            yield conn
        return
    url = url or os.getenv('DATABASE_URL', '')
    if not url:
        raise DatabaseAccessError('Legacy database configuration missing.')
    with _connection(url) as conn:
        if role == 'reader':
            with conn.cursor() as cur:
                cur.execute('SET TRANSACTION READ ONLY')
        yield conn


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
    with storage_transaction('ingestion', url) as conn:
        if not secure_storage_enabled():
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
    if not isinstance(limit, int) or not 1 <= limit <= 10000:
        raise ValueError('limit must be between 1 and 10000')
    with storage_transaction('reader', url) as conn:
        with conn.cursor() as cur:
            cur.execute('''SELECT observed_at_utc,barcode,name,brand,quantity,source,source_url,
                        amazon_sales_known,amazon_price_known,amazon_eligibility_known
                        FROM catalogue_identity_observations
                        ORDER BY observed_at_utc DESC LIMIT %s''', (limit,))
            return [dict(zip(FIELDS, row)) for row in cur.fetchall()]
