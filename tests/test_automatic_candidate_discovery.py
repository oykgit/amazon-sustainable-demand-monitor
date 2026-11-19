import json
import unittest
from automatic_candidate_discovery import discover, normalize

class Response:
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self):
        return json.dumps({'docs': [{'title': 'Example', 'author_name': ['A. Writer'],
          'isbn': ['9780140328721'], 'first_publish_year': 1988}]}).encode()

def fake_fetch(request, timeout):
    assert timeout == 20
    return Response()

class Tests(unittest.TestCase):
    def test_normalize(self):
        self.assertIsNone(normalize({'title':'No ISBN'}))
    def test_dedupe_and_guardrails(self):
        report = discover(('books', 'literature'), fetch=fake_fetch)
        self.assertEqual(report['lead_count'], 1)
        self.assertEqual(report['database_writes'], 0)
        self.assertFalse(report['verified_amazon_demand'])
        self.assertFalse(report['leads'][0]['buy_recommendation'])
    def test_provider_failure(self):
        def broken(*args, **kwargs): raise OSError('unavailable')
        report = discover(('books',), fetch=broken)
        self.assertEqual(report['lead_count'], 0)
        self.assertEqual(len(report['errors']), 1)
    def test_limit(self):
        with self.assertRaises(ValueError): discover(per_topic=30)
