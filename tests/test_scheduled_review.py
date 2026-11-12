from datetime import date
from scheduled_review import build_report

def test_empty():
    r=build_report([], [], date(2026,11,12))
    assert r['tracked']==0 and r['amazon_requests']==0 and r['observations_inserted']==0
    assert r['purchases_enabled'] is False

def test_due_and_missing_source():
    entry={'asin':'B008S8RJKK','marketplace':'UK','priority':'High','review_interval_days':7,'source_reference':'','notes':''}
    r=build_report([entry], [], date(2026,11,12))
    assert r['due_count']==1 and r['missing_source_count']==1
    assert r['due'][0]['asin']=='B008S8RJKK'

def test_not_due():
    entry={'asin':'B008S8RJKK','marketplace':'UK','priority':'Normal','review_interval_days':7,'source_reference':'https://example.org/receipt','notes':''}
    snap={'asin':'B008S8RJKK','marketplace':'UK','observed_at_utc':'2026-11-11T12:00:00+00:00'}
    r=build_report([entry],[snap],date(2026,11,12))
    assert r['due_count']==0 and r['missing_source_count']==0
