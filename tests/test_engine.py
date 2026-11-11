import pandas as pd
from engine import evaluate

def test_unverified_cannot_recommend():
    rows=[]
    for m in range(1,13):
        rows.append(dict(market='UK',asin='X',product='Test',month=f'2025-{m:02}',demand_index=80,sale_price=25,source_cost=5,marketplace_fee=4,shipping=3,other_cost=1,competition_index=20,source='demo',verified=False))
    result=evaluate(pd.DataFrame(rows))
    assert result.iloc[0].decision=='RESEARCH REQUIRED'

def test_missing_months_cannot_recommend():
    rows=[]
    for m in range(1,7):
        rows.append(dict(market='IE',asin='Y',product='Test',month=f'2025-{m:02}',demand_index=80,sale_price=25,source_cost=5,marketplace_fee=4,shipping=3,other_cost=1,competition_index=20,source='provider',verified=True))
    assert evaluate(pd.DataFrame(rows)).iloc[0].decision=='RESEARCH REQUIRED'
