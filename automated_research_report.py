"""Scheduled read-only Neon research summary; no provider collection or trading."""
import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from asin_store import load_asin_observations
from price_history import load_snapshots
from research_watchlist import load_entries

MAX_RECORDS = 10000

def summarize(snapshots, identities, watchlist, checked_at=None):
    checked_at = checked_at or datetime.now(timezone.utc)
    groups = defaultdict(list)
    for row in snapshots:
        groups[(str(row['asin']).upper(),str(row['marketplace']).upper())].append(row)
    names = {}
    for row in sorted(identities,key=lambda x:str(x.get('observed_at_utc',''))):
        names[(str(row['asin']).upper(),str(row['marketplace']).upper())] = str(row.get('name') or '')
    watch = {(str(row['asin']).upper(),str(row['marketplace']).upper()) for row in watchlist}
    keys = sorted(set(groups)|set(names)|watch)
    products=[]
    for asin,market in keys:
        history=sorted(groups.get((asin,market),[]),key=lambda r:str(r['observed_at_utc']))
        latest=history[-1] if history else None
        dates=set(str(r['observed_at_utc'])[:10] for r in history)
        profit=float(latest['estimated_profit_eur']) if latest and latest.get('estimated_profit_eur') is not None else None
        roi=float(latest['estimated_roi_pct']) if latest and latest.get('estimated_roi_pct') is not None else None
        reasons=['No verified Amazon sales or sustained demand evidence', 'Supplier eligibility and actual fees unverified']
        if len(dates)<12: reasons.append('Fewer than 12 distinct observation days')
        if not latest: reasons.append('No price/cost observation')
        if not names.get((asin,market)): reasons.append('Product identity not recorded')
        products.append({'asin':asin,'marketplace':market,'name':names.get((asin,market)) or 'Unknown',
                         'snapshots':len(history),'distinct_observation_days':len(dates),
                         'latest_observation':latest['observed_at_utc'] if latest else None,
                         'latest_entered_price_eur':float(latest['selling_price_eur']) if latest else None,
                         'scenario_profit_eur':profit,'scenario_roi_pct':roi,
                         'research_priority':'REVIEW SCENARIO' if profit is not None and profit>0 and roi is not None and roi>=30 else 'INSUFFICIENT OR LOW SCENARIO',
                         'evidence_warnings':reasons,'buy_recommendation':False})
    products.sort(key=lambda p:(p['research_priority']!='REVIEW SCENARIO', -(p['scenario_profit_eur'] or 0),p['asin']))
    return {'mode':'AUTOMATED_READ_ONLY_RESEARCH_SUMMARY','checked_at_utc':checked_at.isoformat(),
            'products_count':len(products),'source':'Previously stored operator observations in Neon',
            'amazon_live_requests':0,'database_writes':0,'purchases_enabled':False,
            'automatic_product_discovery_enabled':False,'verified_demand':False,
            'products':products}

def run():
    url=os.getenv('DATABASE_URL','')
    if not url: raise RuntimeError('DATABASE_URL missing; report cannot run')
    snapshots=load_snapshots(url=url,limit=MAX_RECORDS)
    identities=load_asin_observations(url=url,limit=MAX_RECORDS)
    watchlist=load_entries(url=url)
    if len(snapshots)>=MAX_RECORDS or len(identities)>=MAX_RECORDS or len(watchlist)>=MAX_RECORDS:
        raise RuntimeError('Data cap reached; report would be incomplete')
    return summarize(snapshots,identities,watchlist)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='automated_research_report.json')
    args=parser.parse_args()
    report=run()
    with open(args.output,'w',encoding='utf-8') as f:json.dump(report,f,indent=2,default=str)
    print(f"Read-only report produced: {report['products_count']} tracked products; no purchases or database writes")

if __name__=='__main__': main()
