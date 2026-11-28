import json
from phase3b_oauth_probe import NoRedirect, probe
from ebay_public_keys import EbayPublicKeyClient, TOKEN_URL


class Client:
    client_id = 'fake-id'
    client_secret = 'fake-secret'
    def _access_token(self):
        return 'fake-token'


def test_default_no_call():
    def forbidden(**kwargs):
        raise AssertionError('must not construct client')
    assert probe(client_factory=forbidden)['oauth_status'] == 'NOT_RUN'


def test_success_redacted():
    result = probe(True, lambda **kwargs: Client())
    assert result['oauth_status'] == 'PASS_TOKEN_ISSUED'
    assert 'fake-' not in json.dumps(result)
    assert result['browse_requests'] == result['database_writes'] == 0
    assert not result['browse_collection_authorized'] and not result['post_activation_authorized']


def test_missing_credentials():
    c = Client(); c.client_secret = ''
    assert probe(True, lambda **kwargs: c)['oauth_status'] == 'CREDENTIALS_MISSING'


def test_failure_redacted():
    class Failed(Client):
        def _access_token(self):
            raise RuntimeError('secret error detail')
    r = probe(True, lambda **kwargs: Failed())
    assert r['oauth_status'] == 'FAIL_OR_UNCONFIRMED'
    assert 'secret error detail' not in json.dumps(r)


def test_empty_token():
    class Empty(Client):
        def _access_token(self): return ''
    assert probe(True, lambda **kwargs: Empty())['oauth_status'] == 'FAIL_OR_UNCONFIRMED'


def test_redirect_denied():
    assert NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.com') is None


def test_real_client_contract_with_fake_transport():
    calls=[]
    class Response:
        status=200
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size): return b'{"access_token":"fake-token","expires_in":7200}'
    def transport(req, timeout):
        calls.append(req)
        assert req.full_url == TOKEN_URL and req.get_method() == 'POST'
        assert b'grant_type=client_credentials' in req.data
        return Response()
    def factory(**kwargs): return EbayPublicKeyClient('fake-id','fake-secret',opener=transport)
    assert probe(True, factory)['oauth_status'] == 'PASS_TOKEN_ISSUED'
    assert len(calls)==1
