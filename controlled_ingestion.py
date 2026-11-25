"""Operator-approved, duplicate-safe CSV ingestion into Neon; no network fetching or purchasing."""
import csv
import hashlib
import io
import os
from datetime import datetime, timezone
from controlled_collection import inspect_csv, COLUMNS
from price_history import build_snapshot, FIELDS as PRICE_FIELDS, _init as init_prices
from persistent_store import storage_transaction, secure_storage_enabled
from commercial_privacy import validate_feed_row


def prepare_feed(content):
    if isinstance(content, str):
        content = content.encode('utf-8')
    report = inspect_csv(content)
    digest = hashlib.sha256(content).hexdigest()
    # No partial acceptance: malformed rows must be fixed before saving anything.
    if report['rejected'] or not report['accepted']:
        raise ValueError('Feed must contain at least one accepted row and zero rejected rows.')
    reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig')))
    prepared = []
    for row in reader:
        row = validate_feed_row(row, allowed_host=os.getenv('AUTHORIZED_FEED_HOST',''), approved_reference=os.getenv('AUTHORIZED_FEED_PERMISSION_REF',''))
        ts = datetime.fromisoformat(row['observed_at_utc'].replace('Z', '+00:00'))
        snapshot = build_snapshot(row['asin'], row['marketplace'], row['selling_price_eur'],
            row['supplier_cost_eur'], row['referral_pct'], row['fulfilment_eur'],
            row['inbound_eur'], row['other_eur'], row['returns_pct'], row['source_note'], at=ts)
        prepared.append((snapshot, row['source_url'].strip(), row['authorization_reference'].strip()))
    return {'sha256': digest, 'count': len(prepared), 'report': report, 'rows': prepared}


def ingest_approved_feed(content, expected_sha256, approval, url=None):
    """Write only on explicit operator confirmation of the exact previewed bytes."""
    if approval != 'I APPROVE THIS CSV INGESTION':
        raise ValueError('Explicit operator approval required.')
    prepared = prepare_feed(content)  # revalidate at write time
    if prepared['sha256'] != expected_sha256:
        raise ValueError('Uploaded CSV differs from the approved preview.')
    inserted = 0
    with storage_transaction('ingestion', url) as conn:
        if not secure_storage_enabled():
            init_prices(conn)
        with conn.cursor() as cur:
            if not secure_storage_enabled():
                cur.execute('''CREATE TABLE IF NOT EXISTS asin_price_feed_provenance (
                    asin TEXT NOT NULL, marketplace TEXT NOT NULL, observed_at_utc TEXT NOT NULL,
                    source_note TEXT NOT NULL, source_url TEXT NOT NULL,
                    authorization_reference TEXT NOT NULL, feed_sha256 TEXT NOT NULL,
                    ingested_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (asin, marketplace, observed_at_utc, source_note))''')
            for snapshot, source_url, authorization in prepared['rows']:
                cur.execute('INSERT INTO asin_price_snapshots (' + ','.join(PRICE_FIELDS) +
                    ') VALUES (' + ','.join(['%s'] * len(PRICE_FIELDS)) +
                    ') ON CONFLICT (asin,marketplace,observed_at_utc,source_note) DO NOTHING',
                    tuple(snapshot[k] for k in PRICE_FIELDS))
                if cur.rowcount:
                    inserted += 1
                    cur.execute('''INSERT INTO asin_price_feed_provenance
                        (asin,marketplace,observed_at_utc,source_note,source_url,authorization_reference,feed_sha256)
                        VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING''',
                        (snapshot['asin'],snapshot['marketplace'],snapshot['observed_at_utc'],
                         snapshot['source_note'],source_url,authorization,prepared['sha256']))
                    if cur.rowcount != 1:
                        raise RuntimeError('PROVENANCE_CONFLICT')
    return {'mode':'OPERATOR_APPROVED_CSV_INGESTION','feed_sha256':prepared['sha256'],
            'validated':prepared['count'],'inserted':inserted,
            'duplicates_skipped':prepared['count'] - inserted,
            'network_requests':0,'purchases_enabled':False,
            'note':'Source authorization is operator-attested, not independently verified.'}
