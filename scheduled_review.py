"""V1.15 scheduled read-only research review. Never fetches Amazon or writes observations."""
import argparse
import json
import os
from datetime import datetime, timezone
from research_watchlist import load_entries, watchlist_status
from price_history import load_snapshots


from datetime import timedelta, time
from reporting_guard import bounded, key, timestamp, reader_url, require

def build_report(entries, snapshots, today=None):
    now=datetime.now(timezone.utc)
    today=today or now.date()
    cutoff=min(now,datetime.combine(today,time.max,tzinfo=timezone.utc))
    latest={}
    for row in bounded(snapshots):
        k=key(row); day=timestamp(row.get('observed_at_utc'),cutoff).date()
        latest[k]=max(day,latest.get(k,day))
    due=[]; missing=0; seen=set()
    for row in bounded(entries):
        k=key(row); require(k not in seen); seen.add(k)
        priority=row.get('priority'); interval=row.get('review_interval_days')
        require(priority in ('Low','Normal','High') and type(interval) is int and 1<=interval<=365)
        source=row.get('source_reference')
        missing+=not (isinstance(source,str) and bool(source.strip()))
        day=latest.get(k); next_due=day+timedelta(days=interval) if day else today
        if next_due<=today:
            due.append(dict(asin=k[0],marketplace=k[1],priority=priority,next_review_due=next_due.isoformat(),latest_observation=day.isoformat() if day else 'None'))
    return {'mode':'DRY_RUN_READ_ONLY','tracked':len(seen),'due_count':len(due),'missing_source_count':missing,'due':due,'amazon_requests':0,'observations_inserted':0,'purchases_enabled':False}

def run(database_url=None):
    url=reader_url(database_url)
    return build_report(load_entries(url=url),load_snapshots(url=url,limit=10000))

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
