import io
import json
from urllib.error import HTTPError, URLError
import pytest
from urllib.request import Request
from api_diagnostics import request_json, CatalogueConnectionError, check_provider

class Response:
    def __init__(self, payload): self.payload=payload
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, limit): return json.dumps(self.payload).encode()

def test_success():
    assert request_json(Request('https://example.com'), 'Test', opener=lambda req,timeout:Response({'ok':True})) == {'ok':True}

def test_forbidden():
    def deny(req,timeout): raise HTTPError(req.full_url,403,'Forbidden',{},io.BytesIO(b'private'))
    with pytest.raises(CatalogueConnectionError) as error:
        request_json(Request('https://example.com'),'Test',opener=deny)
    assert error.value.status == 403
    assert 'private' not in str(error.value)

def test_rate_limit():
    def deny(req,timeout): raise HTTPError(req.full_url,429,'Too Many',{'Retry-After':'60'},None)
    with pytest.raises(CatalogueConnectionError) as error:
        request_json(Request('https://example.com'),'Test',opener=deny)
    assert error.value.retry_after == '60'

def test_network():
    def deny(req,timeout): raise URLError('unreachable')
    with pytest.raises(CatalogueConnectionError) as error:
        request_json(Request('https://example.com'),'Test',opener=deny)
    assert error.value.status is None

def test_provider_diagnostic():
    def fake(req,timeout): return Response({'status':1,'product':{'product_name':'Nutella'}})
    r=check_provider('Open Food Facts',opener=fake)
    assert r['reachable'] and r['product_found']
