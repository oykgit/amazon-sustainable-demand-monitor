from datetime import datetime, timezone
import pytest
from asin_research import validate_asin, asin_url, make_observation

def test_asin_validation():
    assert validate_asin('b008s8rjkk') == 'B008S8RJKK'
    for bad in ('', 'B008S8RJ', 'B008S8RJKKK', 'B008S8RJK!'):
        with pytest.raises(ValueError): validate_asin(bad)

def test_marketplace_urls():
    assert asin_url('B008S8RJKK', 'UK') == 'https://www.amazon.co.uk/dp/B008S8RJKK'
    assert asin_url('B008S8RJKK', 'IE') == 'https://www.amazon.ie/dp/B008S8RJKK'
    with pytest.raises(ValueError): asin_url('B008S8RJKK', 'US')

def test_observation():
    r = make_observation('b008s8rjkk','UK','Example','12345678',at=datetime(2026,11,12,tzinfo=timezone.utc))
    assert r['asin'] == 'B008S8RJKK'
    assert r['marketplace'] == 'UK'
    assert not r['amazon_sales_known']
    assert r['observed_at_utc'].startswith('2026-11-12')

def test_reject_invalid_optional_data():
    with pytest.raises(ValueError): make_observation('B008S8RJKK','UK','Example','invalid')
    with pytest.raises(ValueError): make_observation('B008S8RJKK','UK','Example',source_url='http://bad.example')
    with pytest.raises(ValueError): make_observation('B008S8RJKK','UK','')
