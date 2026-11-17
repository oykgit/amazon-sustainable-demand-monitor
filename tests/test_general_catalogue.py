import json
import pytest
from general_catalogue import normalize_gtin, preview, NoRedirect


def test_valid_ean():
    assert normalize_gtin('3017 6204 22003') == '3017620422003'


def test_bad_check_digit():
    with pytest.raises(ValueError, match='check digit'):
        normalize_gtin('3017620422004')


def test_bad_format():
    with pytest.raises(ValueError):
        normalize_gtin('B008S8RJKK')


def test_reject_provider():
    with pytest.raises(ValueError, match='Unsupported'):
        preview('https://evil.example', '3017620422003')


def test_found():
    result = preview('Open Food Facts', '3017620422003', fetcher=lambda url: json.dumps({'status': 1, 'product': {'product_name': 'Example', 'brands': 'Example brand'}}))
    assert result['status'] == 'CATALOGUE_METADATA_FOUND'
    assert result['database_writes'] == 0
    assert result['amazon_sales_verified'] is False
    assert result['purchases_enabled'] is False


def test_missing():
    assert preview('Open Beauty Facts', '3017620422003', fetcher=lambda url: '{"status":0}')['status'] == 'PRODUCT_NOT_FOUND'


def test_malformed_json():
    with pytest.raises(ValueError, match='invalid JSON'):
        preview('Open Food Facts', '3017620422003', fetcher=lambda url: 'nope')


def test_response_limit():
    with pytest.raises(ValueError, match='256 KB'):
        preview('Open Food Facts', '3017620422003', fetcher=lambda url: b' ' * 256001)


def test_malformed_record():
    with pytest.raises(ValueError, match='malformed'):
        preview('Open Food Facts', '3017620422003', fetcher=lambda url: '{"status":1,"product":[]}')


def test_redirect_rejected():
    with pytest.raises(ValueError, match='redirect blocked'):
        NoRedirect().redirect_request(None, None, 302, 'redirect', {}, 'https://example.org')
