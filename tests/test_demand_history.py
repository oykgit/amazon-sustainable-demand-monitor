import pandas as pd
from demand_history import analyse_history

def sample(n=12, value=50):
    return pd.DataFrame([dict(market='UK', asin='X', product='Sample', month=str(m), demand_index=value, source='documented') for m in pd.period_range('2025-12', periods=n, freq='M')])

def test_full_history():
    r=analyse_history(sample(), as_of='2026-11').iloc[0]
    assert r.full_12_months and r.stability_score == 100 and r.interpretation == 'CONSISTENT PROXY'

def test_missing_month():
    r=analyse_history(sample(11), as_of='2026-11').iloc[0]
    assert not r.full_12_months and r.evidence_status == 'INSUFFICIENT HISTORY'
    assert '2026-11' in r.missing_months

def test_future_excluded():
    r=analyse_history(sample(), as_of='2026-10').iloc[0]
    assert r.months == 11

def test_invalid_range():
    d=sample(); d.loc[0,'demand_index']=150
    assert analyse_history(d, as_of='2026-11').iloc[0].months == 11
