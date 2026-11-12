from opportunity_score import compare_snapshots

def sample(**kw):
    row=dict(asin='B008S8RJKK',marketplace='UK',observed_at_utc='2026-11-01T00:00:00+00:00',selling_price_eur=20,supplier_cost_eur=8,estimated_profit_eur=5,estimated_roi_pct=62.5)
    row.update(kw)
    return row

def test_empty():
    assert compare_snapshots([])==[]

def test_one_is_limited():
    r=compare_snapshots([sample()])[0]
    assert r['Snapshots']==1 and 'Only one price observation' in r['Warnings']
    assert 'No verified Amazon unit sales' in r['Warnings']

def test_history_and_competition():
    a=compare_snapshots([sample(),sample(observed_at_utc='2026-12-05T00:00:00+00:00',selling_price_eur=21)],{('B008S8RJKK','UK'):'low'})[0]
    assert a['History days']==34 and a['Competition (manual)']=='low'
    assert a['Research completeness score / 90']<=90

def test_negative_profit():
    r=compare_snapshots([sample(estimated_profit_eur=-2,estimated_roi_pct=-25)])[0]
    assert 'not positive' in r['Warnings']
