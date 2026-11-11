from datetime import datetime, timezone, timedelta
import pytest
from provider_guard import ProviderGuard, retry_seconds, MAX_CACHE_ITEMS
from api_diagnostics import CatalogueConnectionError

NOW = datetime(2026,11,11,tzinfo=timezone.utc)

def test_cache_prevents_second_request():
    guard=ProviderGuard(); calls=[]
    def lookup(barcode, provider):
        calls.append(1)
        return {'found':True, 'barcode':barcode}
    assert guard.fetch('UPCitemdb','12345678',lookup,NOW)[1]=='live'
    assert guard.fetch('UPCitemdb','12345678',lookup,NOW+timedelta(minutes=1))[1]=='cached'
    assert len(calls)==1

def test_429_cooldown_blocks_requests():
    guard=ProviderGuard(); calls=[]
    def failing(barcode, provider):
        calls.append(1)
        raise CatalogueConnectionError(provider,429,'rate limit','120')
    with pytest.raises(CatalogueConnectionError):guard.fetch('UPCitemdb','12345678',failing,NOW)
    assert guard.remaining('UPCitemdb',NOW)==120
    with pytest.raises(RuntimeError,match='no API request sent'):guard.fetch('UPCitemdb','99999999',failing,NOW)
    assert len(calls)==1

def test_403_cooldown_and_expiry():
    guard=ProviderGuard()
    guard.record_error('Open Food Facts',CatalogueConnectionError('Open Food Facts',403,'denied'),NOW)
    assert guard.remaining('Open Food Facts',NOW)==86400
    assert guard.remaining('Open Food Facts',NOW+timedelta(days=2))==0

def test_retry_after_date():
    assert retry_seconds('Wed, 11 Nov 2026 00:02:00 GMT',NOW)==120
    assert retry_seconds('invalid',NOW) is None

def test_cache_limit():
    guard=ProviderGuard()
    for n in range(MAX_CACHE_ITEMS+3):
        guard.record_success('UPCitemdb',str(n),{'found':True},NOW+timedelta(seconds=n))
    assert len(guard.cache)==MAX_CACHE_ITEMS

def test_no_caching_failed_lookup():
    guard=ProviderGuard()
    with pytest.raises(ValueError):guard.fetch('UPCitemdb','12345678',lambda *args: (_ for _ in ()).throw(ValueError('bad')),NOW)
    assert not guard.cache
