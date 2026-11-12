import pytest
from datetime import datetime, timezone
from price_history import build_snapshot

def test_profit_and_roi():
    x=build_snapshot('b008s8rjkk','UK',20,8,15,3,0.5,0.5,3,'Manual page check',at=datetime(2026,11,12,tzinfo=timezone.utc))
    assert x['asin']=='B008S8RJKK'
    assert x['estimated_profit_eur']==4.4
    assert x['estimated_roi_pct']==55.0

def test_invalid_asin():
    with pytest.raises(ValueError): build_snapshot('bad','UK',20,8,15,3,0,0,3,'Manual')

def test_missing_source():
    with pytest.raises(ValueError): build_snapshot('B008S8RJKK','UK',20,8,15,3,0,0,3,'')

def test_negative_cost():
    with pytest.raises(ValueError): build_snapshot('B008S8RJKK','UK',20,-8,15,3,0,0,3,'Manual')

def test_roi_undefined_zero_cost():
    x=build_snapshot('B008S8RJKK','IE',20,0,15,3,0,0,0,'Manual')
    assert x['estimated_roi_pct'] is None
