from datetime import datetime, timezone
import pytest
from evidence_audit import audit_snapshots

BASE = {'asin':'B008S8RJKK','marketplace':'UK','observed_at_utc':'2026-11-01T12:00:00+00:00',
        'source_note':'operator observed','supplier_cost_eur':8,'fulfilment_eur':3}

def test_empty():
    assert audit_snapshots([]) == []

def test_single():
    result = audit_snapshots([BASE], now=datetime(2026,11,12,tzinfo=timezone.utc))[0]
    assert result['Snapshots'] == 1
    assert result['History days'] == 0
    assert 'Single price snapshot' in result['Audit warnings']
    assert result['Evidence status'] == 'MORE OBSERVATIONS NEEDED'

def test_distinct_days_and_span():
    second = {**BASE, 'observed_at_utc':'2026-12-03T12:00:00+00:00'}
    third = {**BASE, 'observed_at_utc':'2026-12-05T12:00:00+00:00'}
    result = audit_snapshots([BASE,second,third], now=datetime(2026,12,6,tzinfo=timezone.utc))[0]
    assert result['Distinct observation days'] == 3
    assert result['History days'] == 34
    assert result['Evidence status'] == 'REVIEW DOCUMENTATION'

def test_stale_and_cost():
    row = {**BASE,'supplier_cost_eur':0}
    result = audit_snapshots([row], now=datetime(2027,1,1,tzinfo=timezone.utc))[0]
    assert 'older than 30 days' in result['Audit warnings']
    assert 'Supplier cost missing' in result['Audit warnings']

def test_timezone_required():
    with pytest.raises(ValueError):
        audit_snapshots([{**BASE,'observed_at_utc':'2026-11-01T12:00:00'}])
