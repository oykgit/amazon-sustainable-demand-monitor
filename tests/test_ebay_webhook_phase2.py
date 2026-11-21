import base64
import hashlib
import json
import unittest
from ebay_webhook import challenge_response, parse_notification, decode_signature_envelope

class Phase2Tests(unittest.TestCase):
    def test_challenge(self):
        endpoint = 'https://example.com/ebay/account-deletion'
        self.assertEqual(challenge_response('abc', 'x'*32, endpoint), hashlib.sha256(('abc'+'x'*32+endpoint).encode()).hexdigest())
    def test_reject_short_token(self):
        with self.assertRaises(ValueError): challenge_response('abc','short','https://example.com')
    def test_valid_shape(self):
        body = json.dumps({'metadata':{'topic':'MARKETPLACE_ACCOUNT_DELETION'},'notification':{'notificationId':'n1','data':{'userId':'u1'}}}).encode()
        self.assertEqual(parse_notification(body)['notification']['notificationId'], 'n1')
    def test_reject_wrong_topic(self):
        with self.assertRaises(ValueError): parse_notification(b'{"metadata":{"topic":"OTHER"},"notification":{}}')
    def test_reject_oversized(self):
        with self.assertRaises(ValueError): parse_notification(b' ' * 65537)
    def test_reject_missing_identifier(self):
        with self.assertRaises(ValueError): parse_notification(b'{"metadata":{"topic":"MARKETPLACE_ACCOUNT_DELETION"},"notification":{"notificationId":"n1","data":{}}}')
    def test_parse_envelope(self):
        header=base64.b64encode(json.dumps({'kid':'k1','signature':'abc'}).encode()).decode()
        self.assertEqual(decode_signature_envelope(header)['kid'],'k1')
    def test_reject_bad_envelope(self):
        with self.assertRaises(ValueError): decode_signature_envelope('not-base64!')

if __name__ == '__main__': unittest.main()
