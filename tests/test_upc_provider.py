import json
import pytest
from upc_provider import lookup, ProviderFailure, BASE

def test_found():
    result = lookup('3017620422003', fetcher=lambda url: json.dumps({'code':'OK','items':[{'title':'Example','brand':'Example Brand','category':'Food'}]}))
    assert result['status'] == 'CATALOGUE_METADATA_FOUND'
    assert result['database_writes'] == 0
    assert result['purchases_enabled'] is False
    assert result['amazon_sales_verified'] is False

def test_not_found():
    result = lookup('3017620422003', fetcher=lambda url: b'{"code":"NOT_FOUND","items":[]}')
    assert result['status'] == 'PRODUCT_NOT_FOUND'

def test_bad_barcode_no_fetch():
    with pytest.raises(ValueError):
        lookup('12345', fetcher=lambda url: (_ for _ in ()).throw(AssertionError('network called')))

def test_malformed_json():
    with pytest.raises(ProviderFailure) as error:
        lookup('3017620422003', fetcher=lambda url: b'not json')
    assert error.value.code == 'INVALID_JSON'

def test_bad_schema():
    with pytest.raises(ProviderFailure):
        lookup('3017620422003', fetcher=lambda url: b'{"code":"OK","items":{}}')

def test_large_response():
    with pytest.raises(ProviderFailure):
        lookup('3017620422003', fetcher=lambda url: b' ' * 256001)

def test_unknown_provider_status():
    with pytest.raises(ProviderFailure):
        lookup('3017620422003', fetcher=lambda url: b'{"code":"TOO_FAST","items":[]}')

def test_fixed_host():
    def fetch(url):
        assert url.startswith(BASE + '?upc=')
        return b'{"code":"NOT_FOUND","items":[]}'
    lookup('3017620422003', fetcher=fetch)
