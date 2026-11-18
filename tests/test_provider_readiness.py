from provider_readiness import readiness
import pytest

def test_unconfigured():
    r = readiness('Keepa', {})
    assert r['status'] == 'CONFIGURATION_INCOMPLETE'
    assert r['network_requests'] == r['database_writes'] == 0
    assert r['purchases_enabled'] is False

def test_configured_not_connected():
    r = readiness('Keepa', {'KEEPA_API_KEY': 'test', 'RESEARCH_PROVIDER_MAX_DAILY_REQUESTS':'5', 'RESEARCH_PROVIDER_NETWORK_ENABLED':'true'})
    assert r['status'] == 'CONFIGURATION_READY_NOT_CONNECTED'
    assert r['network_requests'] == 0
    assert 'test' not in str(r)

def test_dataforseo_requires_login():
    r = readiness('DataForSEO', {'DATAFORSEO_PASSWORD':'secret','RESEARCH_PROVIDER_MAX_DAILY_REQUESTS':'3'})
    assert r['credentials_configured'] is False

def test_budget_invalid():
    assert readiness('Keepa', {'RESEARCH_PROVIDER_MAX_DAILY_REQUESTS':'bad'})['daily_request_budget'] == 0

def test_unknown():
    with pytest.raises(ValueError): readiness('Unknown', {})
