"""V1.15 scheduled read-only research review. Never fetches Amazon or writes observations."""
import argparse
import json
import os
from datetime import datetime, timezone
from research_watchlist import load_entries, watchlist_status
from price_history import load_snapshots


def build_report(entries, snapshots, today=None):
    rows = watchlist_status(entries, snapshots, today=today)
    due = [r for r in rows if r['Review status'] == 'Due']
    missing = [r for r in rows if r['Traceable source'] == 'Missing']
    return {
        'mode': 'DRY_RUN_READ_ONLY',
        'tracked': len(rows),
        'due_count': len(due),
        'missing_source_count': len(missing),
        'due': [{'asin': r['ASIN'], 'marketplace': r['Marketplace'],
                 'priority': r['Priority'], 'next_review_due': r['Next review due'],
                 'latest_observation': r['Latest observation']} for r in due],
        'amazon_requests': 0,
        'observations_inserted': 0,
        'purchases_enabled': False,
    }


def run(database_url=None):
    database_url = database_url or os.getenv('DATABASE_URL', '')
    if not database_url:
        raise RuntimeError('DATABASE_URL missing; no research review executed.')
    entries = load_entries(url=database_url)
    snapshots = load_snapshots(url=database_url, limit=10000)
    if len(snapshots) >= 10000:
        raise RuntimeError('Price history reached 10,000-row cap; review incomplete.')
    return build_report(entries, snapshots)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='', help='Optional JSON report output path')
    args = parser.parse_args()
    result = run()
    result['checked_at_utc'] = datetime.now(timezone.utc).isoformat()
    output = json.dumps(result, indent=2)
    print(output)
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as file:
            file.write(output + '\n')


if __name__ == '__main__':
    main()
