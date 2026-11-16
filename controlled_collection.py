"""V1.16 authorized CSV intake preview. No HTTP requests, database writes or purchases."""
import csv
import io
import json
from datetime import datetime, timezone
from asin_research import validate_asin, validate_marketplace
from price_history import build_snapshot

COLUMNS = ('asin','marketplace','observed_at_utc','selling_price_eur','supplier_cost_eur','referral_pct','fulfilment_eur','inbound_eur','other_eur','returns_pct','source_note','source_url','authorization_reference')
MAX_BYTES = 1_000_000
MAX_ROWS = 250

def inspect_csv(content, max_rows=MAX_ROWS):
    """Validate a manually supplied authorized feed; never save or backfill."""
    if isinstance(content, str): content = content.encode('utf-8')
    if len(content) > MAX_BYTES: raise ValueError('CSV exceeds 1 MB safety limit')
    try: data = content.decode('utf-8-sig')
    except UnicodeError: raise ValueError('CSV must be UTF-8')
    reader = csv.DictReader(io.StringIO(data))
    if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError('CSV missing headers or has duplicate headers')
    missing = set(COLUMNS) - set(reader.fieldnames)
    if missing: raise ValueError('Missing columns: ' + ', '.join(sorted(missing)))
    accepted, rejected, seen = [], [], set()
    for i, row in enumerate(reader, start=2):
        if i > max_rows + 1: raise ValueError('Feed exceeds per-run quota of 250 records')
        try:
            if None in row: raise ValueError('Unexpected extra CSV fields')
            url = (row['source_url'] or '').strip()
            authorization = (row['authorization_reference'] or '').strip()
            if not url.startswith('https://') or len(url) > 500:
                raise ValueError('Traceable HTTPS source URL required')
            if not authorization or len(authorization) > 200:
                raise ValueError('Source authorization reference required')
            ts = datetime.fromisoformat(row['observed_at_utc'].replace('Z','+00:00'))
            if ts.tzinfo is None: raise ValueError('Timestamp must have UTC offset')
            if ts > datetime.now(timezone.utc): raise ValueError('Future observation not permitted')
            snapshot = build_snapshot(row['asin'], row['marketplace'], row['selling_price_eur'],
                row['supplier_cost_eur'], row['referral_pct'], row['fulfilment_eur'],
                row['inbound_eur'], row['other_eur'], row['returns_pct'], row['source_note'], at=ts)
            key = (snapshot['asin'], snapshot['marketplace'], snapshot['observed_at_utc'], snapshot['source_note'])
            if key in seen: raise ValueError('Duplicate within CSV')
            seen.add(key)
            accepted.append({'row': i, 'asin':snapshot['asin'], 'marketplace':snapshot['marketplace'],
                'observed_at_utc':snapshot['observed_at_utc'], 'source_url':url,
                'authorization_reference':authorization, 'validation':'accepted_for_preview_only'})
        except (ValueError, TypeError, KeyError) as exc:
            rejected.append({'row':i,'reason':str(exc)})
    return {'mode':'AUTHORIZED_CSV_PREVIEW_ONLY','records_seen':len(accepted)+len(rejected),
        'accepted':len(accepted),'rejected':len(rejected),'accepted_rows':accepted,
        'rejected_rows':rejected,'network_requests':0,'database_writes':0,
        'purchases_enabled':False,'quota_max_rows':max_rows,
        'note':'Source references are operator claims, not independent authorization verification.'}

if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('csv_path');p.add_argument('--output',default='collection_preview_report.json')
    args=p.parse_args()
    with open(args.csv_path,'rb') as f: report=inspect_csv(f.read())
    with open(args.output,'w',encoding='utf-8') as f: json.dump(report,f,indent=2)
    print(json.dumps({k:v for k,v in report.items() if k not in ('accepted_rows','rejected_rows')},indent=2))
