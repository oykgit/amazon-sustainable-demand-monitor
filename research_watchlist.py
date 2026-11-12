"""V1.14: operator-managed research watchlist. No network collection or buying."""
import os
from datetime import date, datetime, timedelta, timezone
from asin_research import validate_asin, validate_marketplace
from persistent_store import _connection

FIELDS = ('asin','marketplace','priority','review_interval_days','source_reference','notes','created_at_utc','updated_at_utc')
PRIORITIES = ('Low','Normal','High')

def validate_entry(asin, marketplace, priority='Normal', interval=7, source_reference='', notes=''):
    asin=validate_asin(asin)
    marketplace=validate_marketplace(marketplace)
    if priority not in PRIORITIES: raise ValueError('Invalid priority.')
    if type(interval) is not int or not 1 <= interval <= 365: raise ValueError('Review interval must be 1–365 days.')
    source_reference=str(source_reference).strip()
    notes=str(notes).strip()
    if len(source_reference)>500 or len(notes)>1000: raise ValueError('Source reference or notes too long.')
    return {'asin':asin,'marketplace':marketplace,'priority':priority,
            'review_interval_days':interval,'source_reference':source_reference,'notes':notes}

def _init(conn):
    with conn.cursor() as cur:
        cur.execute('''CREATE TABLE IF NOT EXISTS asin_research_watchlist (
            asin TEXT NOT NULL, marketplace TEXT NOT NULL,
            priority TEXT NOT NULL, review_interval_days INTEGER NOT NULL,
            source_reference TEXT NOT NULL, notes TEXT NOT NULL,
            created_at_utc TEXT NOT NULL, updated_at_utc TEXT NOT NULL,
            PRIMARY KEY (asin,marketplace))''')

def upsert_entry(entry,url=None):
    data=validate_entry(entry['asin'],entry['marketplace'],entry.get('priority','Normal'),
                        entry.get('review_interval_days',7),entry.get('source_reference',''),entry.get('notes',''))
    url=url or os.environ.get('DATABASE_URL','')
    if not url: raise RuntimeError('DATABASE_URL not configured.')
    now=datetime.now(timezone.utc).isoformat()
    with _connection(url) as conn:
        _init(conn)
        with conn.cursor() as cur:
            cur.execute('''INSERT INTO asin_research_watchlist
                (asin,marketplace,priority,review_interval_days,source_reference,notes,created_at_utc,updated_at_utc)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (asin,marketplace) DO UPDATE SET
                priority=EXCLUDED.priority,review_interval_days=EXCLUDED.review_interval_days,
                source_reference=EXCLUDED.source_reference,notes=EXCLUDED.notes,
                updated_at_utc=EXCLUDED.updated_at_utc''',
                (data['asin'],data['marketplace'],data['priority'],data['review_interval_days'],
                 data['source_reference'],data['notes'],now,now))
    return data

def load_entries(url=None):
    url=url or os.environ.get('DATABASE_URL','')
    if not url: raise RuntimeError('DATABASE_URL not configured.')
    with _connection(url) as conn:
        _init(conn)
        with conn.cursor() as cur:
            cur.execute('SELECT '+','.join(FIELDS)+' FROM asin_research_watchlist ORDER BY updated_at_utc DESC LIMIT 10000')
            return [dict(zip(FIELDS,row)) for row in cur.fetchall()]

def watchlist_status(entries,snapshots,today=None):
    """Review reminders derive only from saved snapshots; never synthesize historical prices."""
    today=today or datetime.now(timezone.utc).date()
    grouped={}
    for s in snapshots:
        try:
            observed=datetime.fromisoformat(str(s['observed_at_utc']).replace('Z','+00:00'))
            if observed.tzinfo is None: continue
            key=(s['asin'],s['marketplace'])
            grouped.setdefault(key,[]).append(observed.astimezone(timezone.utc).date())
        except (KeyError,ValueError,TypeError): continue
    results=[]
    for entry in entries:
        key=(entry['asin'],entry['marketplace'])
        dates=sorted(set(grouped.get(key,[])))
        latest=dates[-1] if dates else None
        due=latest+timedelta(days=int(entry['review_interval_days'])) if latest else today
        span=(dates[-1]-dates[0]).days if dates else 0
        results.append({'ASIN':key[0],'Marketplace':key[1],'Priority':entry['priority'],
            'Observation days':len(dates),'History days':span,
            'Latest observation':latest.isoformat() if latest else 'None',
            'Next review due':due.isoformat(), 'Review status':'Due' if due<=today else 'Scheduled',
            '30-day coverage':'Reached' if span>=30 else 'Pending',
            '90-day coverage':'Reached' if span>=90 else 'Pending',
            '365-day coverage':'Reached' if span>=365 else 'Pending',
            'Source reference':entry['source_reference'],
            'Traceable source':'Provided' if entry['source_reference'] else 'Missing',
            'Notes':entry['notes']})
    return results
