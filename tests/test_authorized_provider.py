import json
import unittest
from authorized_provider import collect, validate_payload, _validated_endpoint

class ProviderTests(unittest.TestCase):
    def test_unconfigured(self):
        result=collect(endpoint='',allowed_host='',provider='',authorization_reference='')
        self.assertEqual(result['status'],'NOT_CONFIGURED')
        self.assertEqual(result['network_requests'],0)
    def test_bad_endpoint(self):
        with self.assertRaises(ValueError): _validated_endpoint('http://example.com/data','example.com')
    def test_host_mismatch(self):
        with self.assertRaises(ValueError): _validated_endpoint('https://evil.example/data','example.com')
    def test_private_ip(self):
        with self.assertRaises(ValueError): _validated_endpoint('https://127.0.0.1/data','127.0.0.1')
    def test_bad_json(self):
        with self.assertRaises(ValueError): validate_payload(b'not-json','provider','permission')
    def test_bad_shape(self):
        with self.assertRaises(ValueError): validate_payload(b'{}','provider','permission')
    def test_empty_feed(self):
        result=collect('https://feed.example.org/data','feed.example.org','Sample','Approved',fetcher=lambda _:b'{"observations":[]}')
        self.assertEqual(result['status'],'PREVIEW_COMPLETE')
        self.assertEqual(result['database_writes'],0)
        self.assertEqual(result['accepted'],0)
    def test_quota(self):
        with self.assertRaises(ValueError):validate_payload(json.dumps({'observations':[{}]*251}).encode(),'p','permission')
    def test_rejected_missing_fields(self):
        report=validate_payload(b'{"observations":[{}]}','p','permission')
        self.assertEqual(report['rejected'],1)
        self.assertFalse(report['purchases_enabled'])

if __name__=='__main__':unittest.main()
