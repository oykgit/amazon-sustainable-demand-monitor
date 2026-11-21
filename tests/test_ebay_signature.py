import base64
import json
import unittest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from ebay_signature import decode_header, verify_notification, SignatureError


def header(sig, kid='test-key', alg='ecdsa', digest='SHA256'):
    data = {'alg': alg, 'digest': digest, 'kid': kid, 'signature': base64.b64encode(sig).decode()}
    return base64.b64encode(json.dumps(data).encode()).decode()


class TestSignature(unittest.TestCase):
    def setUp(self):
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.pem = self.key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        self.body = b'{"metadata":{"topic":"MARKETPLACE_ACCOUNT_DELETION"}}'
        self.sig = self.key.sign(self.body, ec.ECDSA(hashes.SHA256()))

    def test_valid_signature(self):
        self.assertEqual(verify_notification(header(self.sig), self.body, self.pem), 'test-key')

    def test_modified_body(self):
        with self.assertRaises(SignatureError): verify_notification(header(self.sig), self.body + b' ', self.pem)

    def test_wrong_key(self):
        other = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        with self.assertRaises(SignatureError): verify_notification(header(self.sig), self.body, other)

    def test_bad_header(self):
        with self.assertRaises(SignatureError): decode_header('not base64')

    def test_bad_algorithm(self):
        with self.assertRaises(SignatureError): decode_header(header(self.sig, alg='none'))

    def test_bad_digest(self):
        with self.assertRaises(SignatureError): decode_header(header(self.sig, digest='SHA1'))

    def test_empty_body(self):
        with self.assertRaises(SignatureError): verify_notification(header(self.sig), b'', self.pem)

    def test_non_ec_key(self):
        from cryptography.hazmat.primitives.asymmetric import rsa
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        with self.assertRaises(SignatureError): verify_notification(header(self.sig), self.body, pem)

if __name__ == '__main__': unittest.main()
