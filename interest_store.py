"""Operator-approved, durable Google search-interest observations; not Amazon sales."""
import os
import re
import pandas as pd
from persistent_store import _connection
from free_sources import TREND_FIELDS


def validate_interest(frame):
    if not isinstance(frame, pd.DataFrame) or any(c not in frame for c in TREND_FIELDS):
        raise ValueError('Missing search-interest CSV columns')
    if frame.empty or len(frame) > 10000:
        raise ValueError('CSV must contain 1–10000 observations')
    d = frame[TREND_FIELDS].copy()
    d['market'] = d.market.astype(str).str.strip().str.upper()
    d['keyword'] = d.keyword.astype(str).str.strip()
    d['source'] = d.source.astype(str).str.strip()
    d['month'] = d.month.astype(str).str.strip()
    d['search_interest'] = pd.to_numeric(d.search_interest, errors='coerce')
    if not d.market.isin(['UK', 'IE']).all():
        raise ValueError('Market must be UK or IE')
    if d.keyword.eq('').any() or d.source.eq('').any() or d.keyword.str.len().gt(250).any() or d.source.str.len().gt(1000).any() or d[['keyword','source']].isin(['nan','None']).any().any():
        raise ValueError('Keyword and documented source are required')
    if not d.month.map(lambda s: bool(re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',s))).all():
        raise ValueError('Months must be YYYY-MM')
    current_month = pd.Timestamp.now(tz='UTC').strftime('%Y-%m')
    if d.month.gt(current_month).any():
        raise ValueError('Future months are not allowed')
    if not d.search_interest.between(0,100).all():
        raise ValueError('Search interest must be between 0 and 100')
    # No silent overwrites of differing observations for the same month.
    if d.duplicated(['market','keyword','month']).any():
        raise ValueError('Duplicate market/keyword/month rows in CSV')
    return d


def _init(conn):
    with conn.cursor() as cur:
        cur.execute('''CREATE TABLE IF NOT EXISTS search_interest_observations (
          market TEXT NOT NULL, keyword TEXT NOT NULL, month TEXT NOT NULL,
          search_interest DOUBLE PRECISION NOT NULL, source TEXT NOT NULL,
          PRIMARY KEY (market,keyword,month),
          CONSTRAINT interest_range CHECK (search_interest >= 0 AND search_interest <= 100)
        )''')


def save_interest(frame, url=None):
    d = validate_interest(frame)
    url = url or os.environ.get('DATABASE_URL', '')
    if not url:
        raise RuntimeError('DATABASE_URL is not configured')
    inserted = 0
    conflicts = 0
    with _connection(url) as conn:
        _init(conn)
        with conn.cursor() as cur:
            for row in d.itertuples(index=False):
                cur.execute('''INSERT INTO search_interest_observations
                    (market,keyword,month,search_interest,source)
                    VALUES (%s,%s,%s,%s,%s)
                    ON CONFLICT (market,keyword,month) DO NOTHING''',
                    (row.market,row.keyword,row.month,float(row.search_interest),row.source))
                inserted += cur.rowcount
                conflicts += 1-cur.rowcount
    return {'inserted':inserted,'existing_not_overwritten':conflicts}


def load_interest(url=None, limit=10000):
    url = url or os.environ.get('DATABASE_URL', '')
    if not url:
        raise RuntimeError('DATABASE_URL is not configured')
    if not isinstance(limit,int) or not 1 <= limit <= 10000:
        raise ValueError('Invalid limit')
    with _connection(url) as conn:
        _init(conn)
        with conn.cursor() as cur:
            cur.execute('''SELECT market,keyword,month,search_interest,source
                        FROM search_interest_observations
                        ORDER BY month DESC, market, keyword LIMIT %s''',(limit,))
            return pd.DataFrame(cur.fetchall(),columns=TREND_FIELDS)
