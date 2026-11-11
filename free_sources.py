"""Offline, user-supplied, legitimately collected data importers. No scraping."""
import pandas as pd

RANK_FIELDS=['market','asin','product','observed_at','best_seller_rank','category','source_url']
TREND_FIELDS=['market','keyword','month','search_interest','source']

def import_rank_snapshots(data):
    df=pd.read_csv(data)
    missing=set(RANK_FIELDS)-set(df.columns)
    if missing: raise ValueError('Missing rank fields: '+', '.join(sorted(missing)))
    df=df[RANK_FIELDS].copy()
    df['market']=df.market.astype(str).str.upper().str.strip()
    df['observed_at']=pd.to_datetime(df.observed_at,errors='coerce',utc=True)
    df['best_seller_rank']=pd.to_numeric(df.best_seller_rank,errors='coerce')
    df=df[df.market.isin(['UK','IE']) & df.observed_at.notna() & df.best_seller_rank.gt(0)]
    df=df[df.asin.astype(str).str.strip().ne('') & df.source_url.astype(str).str.startswith('https://')]
    return df.drop_duplicates(['market','asin','observed_at'],keep='last').sort_values('observed_at')

def rank_summary(df):
    if df.empty: return pd.DataFrame()
    d=df.copy();d['month']=d.observed_at.dt.tz_localize(None).dt.to_period('M').astype(str)
    out=[]
    for (market,asin),g in d.groupby(['market','asin']):
        monthly=g.groupby('month').best_seller_rank.median()
        out.append({'market':market,'asin':asin,'product':g.iloc[-1]['product'],
                    'observed_months':len(monthly),'rank_observations':len(g),
                    'median_category_rank':round(float(monthly.median())),
                    'rank_variability_pct':round(float(monthly.std(ddof=0)/monthly.mean()*100),1) if monthly.mean()>0 else None,
                    'first_observed':g.observed_at.min().date().isoformat(),
                    'last_observed':g.observed_at.max().date().isoformat(),
                    'historical_coverage':'12+ months observed' if len(monthly)>=12 else 'Insufficient for 12-month claim',
                    'decision':'RESEARCH REQUIRED'})
    return pd.DataFrame(out)

def import_search_interest(data):
    d=pd.read_csv(data)
    missing=set(TREND_FIELDS)-set(d.columns)
    if missing:raise ValueError('Missing search-interest fields: '+', '.join(sorted(missing)))
    d=d[TREND_FIELDS].copy()
    d['search_interest']=pd.to_numeric(d.search_interest,errors='coerce')
    d['month']=pd.to_datetime(d.month,errors='coerce')
    d['market']=d.market.astype(str).str.upper().str.strip()
    return d[d.market.isin(['UK','IE']) & d.month.notna() & d.search_interest.between(0,100)].copy()

def search_interest_summary(d):
    if d.empty:return pd.DataFrame()
    out=[]
    for (market,keyword),g in d.groupby(['market','keyword']):
        monthly=g.drop_duplicates('month',keep='last').sort_values('month')
        out.append({'market':market,'keyword':keyword,'months':len(monthly),
                    'average_relative_interest':round(monthly.search_interest.mean(),1),
                    'relative_interest_variability_pct':round(100*monthly.search_interest.std(ddof=0)/monthly.search_interest.mean(),1) if monthly.search_interest.mean()>0 else None,
                    'interpretation':'SEARCH INTEREST ONLY; NOT AMAZON SALES'})
    return pd.DataFrame(out)
