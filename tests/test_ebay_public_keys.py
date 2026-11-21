import json
import unittest
from unittest.mock import Mock
from ebay_public_keys import EbayPublicKeyClient, EbayKeyError, TOKEN_URL, KEY_BASE

PEM = '-----BEGIN PUBLIC KEY-----\nTEST\n-----END PUBLIC KEY-----'

class Response:
    status = 200
    def __init__(self, payload): self.payload = json.dumps(payload).encode()
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, n): return self.payload[:n]

class TestClient(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.now = [100]
        def opener(req, timeout):
            self.calls.append(req)
            if req.full_url == TOKEN_URL:
                return Response({'access_token':'token123','expires_in':7200})
            if req.full_url == KEY_BASE + 'abc123':
                return Response({'key':PEM})
            return Response({})
        self.client = EbayPublicKeyClient('id','secret',opener=opener,clock=lambda:self.now[0])

    def test_oauth_and_key(self):
        self.assertEqual(self.client.get_public_key('abc123'), PEM)
        self.assertEqual(self.calls[0].get_method(), 'POST')
        self.assertIn('Basic ', self.calls[0].get_header('Authorization'))
        self.assertEqual(self.calls[1].get_header('Authorization'), 'Bearer token123')

    def test_key_cache(self):
        self.client.get_public_key('abc123')
        self.now[0] += 3599
        self.client.get_public_key('abc123')
        self.assertEqual(len(self.calls), 2)
        self.now[0] += 2
        self.client.get_public_key('abc123')
        self.assertEqual(len(self.calls), 3)

    def test_bad_ids_do_not_make_requests(self):
        for key_id in ('../x', '', 'a/b', 'x'*129, None):
            with self.assertRaises(EbayKeyError): self.client.get_public_key(key_id)
        self.assertEqual(len(self.calls), 0)

    def test_missing_credentials(self):
        c = EbayPublicKeyClient('', '', opener=lambda *a, **kw: None)
        with self.assertRaises(EbayKeyError): c.get_public_key('abc123')

    def test_invalid_key_response(self):
        def opener(req, timeout):
            return Response({'access_token':'token','expires_in':3600}) if req.full_url == TOKEN_URL else Response({'key':'garbage'})
        c = EbayPublicKeyClient('id','secret',opener=opener)
        with self.assertRaises(EbayKeyError): c.get_public_key('abc123')

    def test_no_secret_in_errors(self):
        c = EbayPublicKeyClient('id','TOPSECRET',opener=lambda *args, **kw: (_ for _ in ()).throw(OSError('failure')))
        with self.assertRaises(EbayKeyError) as cm: c.get_public_key('abc123')
        self.assertNotIn('TOPSECRET', str(cm.exception))

if __name__ == '__main__': unittest.main()
