import base64
import json
import unittest
from unittest.mock import patch
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from ebay_webhook import authenticate_notification, challenge_response, parse_notification
from ebay_signature import SignatureError
from ebay_public_keys import EbayKeyError

BODY = json.dumps({'metadata':{'topic':'MARKETPLACE_ACCOUNT_DELETION'},'notification':{'notificationId':'n1','data':{'userId':'u1'}}}).encode()

class KeyClient:
    def __init__(self, pem): self.pem = pem; self.calls = []
    def get_public_key(self, kid): self.calls.append(kid); return self.pem

class Tests(unittest.TestCase):
    def setUp(self):
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.pem = self.key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
        self.client = KeyClient(self.pem)

    def header(self, body=BODY):
        sig = self.key.sign(body, ec.ECDSA(hashes.SHA256()))
        env = {'alg':'ecdsa','digest':'SHA256','kid':'key1','signature':base64.b64encode(sig).decode()}
        return base64.b64encode(json.dumps(env).encode()).decode()

    def test_valid(self):
        self.assertEqual(authenticate_notification(self.header(), BODY, self.client)['notification']['notificationId'],'n1')
        self.assertEqual(self.client.calls, ['key1'])

    def test_modified_body(self):
        with self.assertRaises(SignatureError): authenticate_notification(self.header(), BODY+b' ', self.client)

    def test_bad_header_no_lookup(self):
        with self.assertRaises(SignatureError): authenticate_notification('bad', BODY, self.client)
        self.assertEqual(self.client.calls, [])

    def test_signed_wrong_topic(self):
        body = BODY.replace(b'MARKETPLACE_ACCOUNT_DELETION', b'OTHER')
        with self.assertRaises(ValueError): authenticate_notification(self.header(body), body, self.client)

    def test_key_lookup_failure(self):
        with patch.object(self.client,'get_public_key',side_effect=EbayKeyError('unavailable')):
            with self.assertRaises(EbayKeyError): authenticate_notification(self.header(), BODY, self.client)

    def test_challenge_preserved(self):
        self.assertEqual(len(challenge_response('TEST','a'*48,'https://example.com/ebay/account-deletion')),64)

    def test_parse_no_identifier(self):
        body = BODY.replace(b'userId', b'other_')
        with self.assertRaises(ValueError): parse_notification(body)

if __name__ == '__main__': unittest.main()
