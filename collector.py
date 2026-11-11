"""Opt-in ingestion of a user-authorised HTTPS CSV feed. Never scrapes Amazon."""
import argparse
import io
import os
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import pandas as pd
from engine import REQUIRED
from free_sources import RANK_FIELDS, TREND_FIELDS

FIELDS={'monthly':REQUIRED,'rank':RANK_FIELDS,'interest':TREND_FIELDS}
KEYS={'monthly':['market','asin','month'],'rank':['market','asin','observed_at'],'interest':['market','keyword','month']}
MAX_BYTES=2_000_000

def validate(df,kind):
    fields=FIELDS[kind]
    missing=set(fields)-set(df.columns)
    if missing: raise ValueError(f'Missing {kind} columns: {sorted(missing)}')
    d=df[fields].copy()
    d['market']=d['market'].astype(str).str.upper().str.strip()
    if not d['market'].isin(['UK','IE']).all(): raise ValueError('Only UK and IE markets allowed')
    if d.empty: raise ValueError('Empty feed')
    if len(d)>10000: raise ValueError('Too many rows')
    datecol='observed_at' if kind=='rank' else 'month'
    dates=pd.to_datetime(d[datecol],errors='coerce',utc=True)
    if dates.isna().any(): raise ValueError('Invalid dates')
    if (dates>pd.Timestamp.now(tz='UTC')).any(): raise ValueError('Future observations are not allowed')
    d[datecol]=dates.dt.strftime('%Y-%m-%d' if kind=='rank' else '%Y-%m')
    if kind=='monthly':
        for c in ['demand_index','competition_index']:
            vals=pd.to_numeric(d[c],errors='coerce')
            if vals.isna().any() or not vals.between(0,100).all(): raise ValueError(f'Invalid {c}')
        for c in ['sale_price','source_cost','marketplace_fee','shipping','other_cost']:
            vals=pd.to_numeric(d[c],errors='coerce')
            if vals.isna().any() or not vals.ge(0).all(): raise ValueError(f'Invalid {c}')
        if d['source'].fillna('').astype(str).str.strip().eq('').any(): raise ValueError('Source required')
    if kind=='rank':
        vals=pd.to_numeric(d.best_seller_rank,errors='coerce')
        if vals.isna().any() or not vals.gt(0).all(): raise ValueError('Invalid ranks')
        if not d.source_url.astype(str).str.startswith('https://').all(): raise ValueError('HTTPS source URLs required')
    if kind=='interest':
        vals=pd.to_numeric(d.search_interest,errors='coerce')
        if vals.isna().any() or not vals.between(0,100).all(): raise ValueError('Invalid search interest')
    return d.drop_duplicates(KEYS[kind],keep='last')

def merge(existing,incoming,kind):
    if existing is None or existing.empty: return validate(incoming,kind)
    old=validate(existing,kind)
    new=validate(incoming,kind)
    return pd.concat([old,new],ignore_index=True).drop_duplicates(KEYS[kind],keep='last').sort_values(KEYS[kind]).reset_index(drop=True)

def fetch_csv(url):
    parsed=urlparse(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('A public HTTPS feed URL is required')
    # This runs only in the operator-controlled GitHub Action, never on untrusted user input.
    req=Request(url,headers={'User-Agent':'SustainableDemandMonitor/1.2 (authorised CSV feed)'})
    with urlopen(req,timeout=20) as resp:
        if urlparse(resp.geturl()).scheme!='https': raise ValueError('Redirected away from HTTPS')
        raw=resp.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES: raise ValueError('Feed too large')
    return pd.read_csv(io.BytesIO(raw))

def run(kind,url,output):
    incoming=validate(fetch_csv(url),kind)
    path=Path(output)
    existing=pd.read_csv(path) if path.exists() and path.stat().st_size else None
    combined=merge(existing,incoming,kind)
    path.parent.mkdir(parents=True,exist_ok=True)
    combined.to_csv(path,index=False)
    return len(combined)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--kind',choices=FIELDS,required=True)
    parser.add_argument('--url',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    print(f'Validated stored observations: {run(args.kind,args.url,args.output)}')
