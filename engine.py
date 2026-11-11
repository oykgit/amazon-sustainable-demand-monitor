import pandas as pd

REQUIRED = ['market','asin','product','month','demand_index','sale_price','source_cost','marketplace_fee','shipping','other_cost','competition_index','source','verified']

def evaluate(df, budget=1000):
    missing = set(REQUIRED)-set(df.columns)
    if missing: raise ValueError('Missing columns: '+', '.join(sorted(missing)))
    d=df.copy()
    d['month']=pd.to_datetime(d['month'], errors='coerce')
    for c in ['demand_index','sale_price','source_cost','marketplace_fee','shipping','other_cost','competition_index']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    d['verified']=d['verified'].astype(str).str.lower().isin(['true','1','yes'])
    output=[]
    for (market,asin),g in d.groupby(['market','asin']):
        g=g.dropna(subset=['month','demand_index','sale_price','source_cost','marketplace_fee','shipping','other_cost','competition_index']).sort_values('month')
        if g.empty:continue
        g=g.drop_duplicates('month',keep='last')
        last=g.iloc[-1]; months=len(g); valid=(months>=12 and (g['month'].max().to_period('M')-g['month'].min().to_period('M')).n>=11)
        mean=g.demand_index.mean(); cv=(g.demand_index.std(ddof=0)/mean) if mean>0 else 999
        consistency=max(0,min(100,100*(1-cv))) if valid else 0
        price=float(last.sale_price); unit_cost=float(last.source_cost+last.marketplace_fee+last.shipping+last.other_cost)
        profit=price-unit_cost; margin=profit/price if price>0 else -1
        competition=float(g.competition_index.tail(3).mean())
        price_cv=float(g.sale_price.std(ddof=0)/g.sale_price.mean()) if g.sale_price.mean()>0 else 999
        score=round(.30*consistency+.25*max(0,min(100,margin*250))+.15*max(0,100-competition)+.10*max(0,100-price_cv*200)+.10*(100 if last.verified else 0)+.05*(100 if 0<=last.other_cost else 0)+.05*max(0,min(100,50+(g.demand_index.tail(3).mean()-g.demand_index.head(3).mean()))),1)
        evidence=bool(valid and g.verified.all() and g.source.astype(str).str.strip().ne('').all())
        if not evidence:decision='RESEARCH REQUIRED'
        elif profit<5 or margin<.20 or competition>75 or consistency<60:decision='AVOID / WATCH'
        elif score>=70 and unit_cost<=budget*.15:decision='TEST PURCHASE CANDIDATE'
        else:decision='WATCHLIST'
        max_qty=max(0,int(min(budget*.20//max(last.source_cost,0.01),budget*.25//max(unit_cost,0.01))))
        output.append(dict(market=market,asin=asin,product=last['product'],months=months,demand_consistency=round(consistency,1),score=score,sale_price=round(price,2),unit_cost=round(unit_cost,2),unit_profit=round(profit,2),margin_pct=round(margin*100,1),competition=round(competition,1),evidence_verified=evidence,decision=decision,suggested_test_units=(min(10,max_qty) if decision=='TEST PURCHASE CANDIDATE' else 0)))
    return pd.DataFrame(output).sort_values(['score'],ascending=False) if output else pd.DataFrame()
