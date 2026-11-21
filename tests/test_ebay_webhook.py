import hashlib
import unittest
from ebay_webhook import challenge_response


class ChallengeTests(unittest.TestCase):
    def test_digest_order(self):
        token = 'a' * 32
        endpoint = 'https://example.onrender.com/ebay/account-deletion'
        self.assertEqual(challenge_response('xyz', token, endpoint), hashlib.sha256(('xyz' + token + endpoint).encode()).hexdigest())

    def test_token_limits(self):
        for token in ['short', 'a' * 81, 'a' * 31 + '!']:
            with self.assertRaises(ValueError):
                challenge_response('x', token, 'https://example.org')
