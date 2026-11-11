"""Auditable historical coverage diagnostics. No inferred sales volumes."""
from pathlib import Path
import pandas as pd
from collector import validate

SOURCES = {'monthly':'monthly.csv','rank':'ranks.csv','interest':'interest.csv'}

def inspect(kind, frame):
    d=validate(frame,kind)
    datecol='observed_at' if kind=='rank' else 'month'
    date=pd.to_datetime(d[datecol],utc=True)
    today=pd.Timestamp.now(tz='UTC')
    age=(today-date.max()).days
    result={'kind':kind,'rows':len(d),'markets':', '.join(sorted(d.market.unique())),
            'first_observation':date.min().strftime('%Y-%m-%d'),
            'last_observation':date.max().strftime('%Y-%m-%d'),
            'days_since_latest':age,'status':'CURRENT' if age<=45 else 'STALE',
            'notes':'Rank/search-interest observations are not Amazon units sold.' if kind!='monthly' else 'Demand index is a user-supplied proxy, not sales volume.'}
    if kind=='monthly':
        d=d.copy();d['month']=pd.to_datetime(d['month']).dt.to_period('M')
        coverage=[]
        for (market,asin),g in d.groupby(['market','asin']):
            periods=sorted(set(g.month))
            latest=periods[-1]
            window=pd.period_range(end=latest,periods=12,freq='M')
            observed=sum(p in periods for p in window)
            coverage.append({'market':market,'asin':asin,'product':g.iloc[-1]['product'],
                             'months_in_latest_12':observed,'missing_months':12-observed,
                             'complete_12_months':observed==12,
                             'last_month':str(latest)})
        result['coverage']=pd.DataFrame(coverage)
    return result

def inspect_stored(folder='data'):
    reports=[]; details={}
    for kind,filename in SOURCES.items():
        path=Path(folder)/filename
        if not path.exists() or path.stat().st_size==0:
            reports.append({'source':kind,'status':'NOT CONFIGURED / NO DATA','rows':0,'last_observation':'—','days_since_latest':None})
            continue
        try:
            info=inspect(kind,pd.read_csv(path))
            reports.append({'source':kind,'status':info['status'],'rows':info['rows'],
                            'last_observation':info['last_observation'],'days_since_latest':info['days_since_latest']})
            details[kind]=info
        except Exception as exc:
            reports.append({'source':kind,'status':'INVALID DATA','rows':0,'last_observation':'—','days_since_latest':None})
            details[kind]={'error':str(exc)}
    return pd.DataFrame(reports),details
