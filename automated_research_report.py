"""Scheduled read-only Neon research summary; no provider collection or trading."""
import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from asin_store import load_asin_observations
from price_history import load_snapshots
from research_watchlist import load_entries

from reporting_guard import MAX_RECORDS, bounded, key, timestamp, scenario, projected, reader_url, require

def summarize(snapshots, identities, watchlist, checked_at=None):
    now=checked_at or datetime.now(timezone.utc)
    require(now.tzinfo is not None)
    now=now.astimezone(timezone.utc)
    groups=defaultdict(list)
    for row in bounded(snapshots):
        groups[key(row)].append((timestamp(row.get('observed_at_utc'),now),scenario(row)))
    known=set()
    for row in bounded(identities):
        timestamp(row.get('observed_at_utc'),now)
        known.add(key(row))
    watch={key(row) for row in bounded(watchlist)}
    products=[]
    for asin,market in sorted(set(groups)|known|watch):
        history=sorted(groups.get((asin,market),[]),key=lambda pair:pair[0])
        latest=history[-1] if history else None
        if latest:
            require(all(v==latest[1] for t,v in history if t==latest[0]))
        dates={t.date() for t,v in history}
        price,profit,roi=latest[1] if latest else (None,None,None)
        reasons=['No verified Amazon sales or sustained demand evidence','Supplier eligibility and actual fees unverified']
        if len(dates)<12: reasons.append('Fewer than 12 distinct observation days')
        if not latest: reasons.append('No price/cost observation')
        if (asin,market) not in known: reasons.append('Product identity not recorded')
        row=projected(dict(asin=asin,marketplace=market,scenario_profit_eur=profit,scenario_roi_pct=roi))
        row.update(snapshots=len(history),distinct_observation_days=len(dates),
                   latest_observation=latest[0].isoformat() if latest else None,
                   latest_entered_price_eur=price,evidence_warnings=reasons)
        products.append(row)
    products.sort(key=lambda p:(p['research_priority']!='REVIEW SCENARIO',-(p['scenario_profit_eur'] or 0),p['asin'],p['marketplace']))
    return {'mode':'AUTOMATED_READ_ONLY_RESEARCH_SUMMARY','checked_at_utc':now.isoformat(),
            'products_count':len(products),'source':'Previously stored operator observations in Neon',
            'amazon_live_requests':0,'database_writes':0,'purchases_enabled':False,
            'automatic_product_discovery_enabled':False,'verified_demand':False,'products':products}

def run():
    url=reader_url()
    snapshots=load_snapshots(url=url,limit=MAX_RECORDS)
    identities=load_asin_observations(url=url,limit=MAX_RECORDS)
    watchlist=load_entries(url=url)
    return summarize(snapshots,identities,watchlist)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='automated_research_report.json')
    args=parser.parse_args()
    report=run()
    with open(args.output,'w',encoding='utf-8') as f:json.dump(report,f,indent=2,allow_nan=False)
    print(f"Read-only report produced: {report['products_count']} tracked products; no purchases or database writes")

if __name__=='__main__': main()
