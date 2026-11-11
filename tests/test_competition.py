import pandas as pd
import pytest
from competition import assess_competition

BASE = dict(market='UK', asin='B000TEST', observed_at='2026-11-01', competing_listings=5,
            median_competitor_price_eur=19.99, median_review_count=12,
            source='Manual authorised research', notes='Example')

def test_low():
    assert assess_competition(pd.DataFrame([BASE])).iloc[0].competition_pressure.startswith('LOW')

def test_high():
    assert assess_competition(pd.DataFrame([{**BASE,'competing_listings':35}])).iloc[0].competition_pressure.startswith('HIGH')

def test_moderate():
    assert assess_competition(pd.DataFrame([{**BASE,'median_review_count':250}])).iloc[0].competition_pressure.startswith('MODERATE')

@pytest.mark.parametrize('change', [{'market':'US'},{'competing_listings':-1},{'observed_at':'bad'},{'source':''},{'median_review_count':1.5}])
def test_invalid(change):
    with pytest.raises(ValueError): assess_competition(pd.DataFrame([{**BASE,**change}]))

def test_missing():
    with pytest.raises(ValueError): assess_competition(pd.DataFrame([{'market':'UK'}]))
