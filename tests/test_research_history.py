from datetime import datetime, timezone
import pytest
from research_history import manual_observation, timeline, validate_import_rows

def test_manual_identity():
    r = manual_observation('12345678', 'Sample', at=datetime(2026,11,12,tzinfo=timezone.utc))
    assert r['source'] == 'Operator documented'
    assert r['amazon_sales_known'] is False
    assert timeline([r]) == [{'barcode':'12345678','month':'2026-11','identity_observations':1}]

def test_invalid_manual():
    with pytest.raises(ValueError): manual_observation('invalid','Sample')
    with pytest.raises(ValueError): manual_observation('12345678','')
    with pytest.raises(ValueError): manual_observation('12345678','Sample',source_url='ftp://foo')

def test_csv_validation():
    row = manual_observation('12345678','Sample',at=datetime(2026,11,12,tzinfo=timezone.utc))
    assert len(validate_import_rows([row])) == 1
    row['amazon_sales_known'] = True
    with pytest.raises(ValueError): validate_import_rows([row])
