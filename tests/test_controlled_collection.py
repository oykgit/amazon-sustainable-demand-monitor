import pytest

@pytest.fixture(autouse=True)
def synthetic_feed_policy(monkeypatch):
    monkeypatch.setenv('AUTHORIZED_FEED_HOST','example.org')
    monkeypatch.setenv('AUTHORIZED_FEED_PERMISSION_REF','PERM-1')

import csv
import io
import unittest
from controlled_collection import inspect_csv, COLUMNS

class TestPreview(unittest.TestCase):
    def feed(self, **updates):
        row=dict(asin='B008S8RJKK',marketplace='UK',observed_at_utc='2026-11-12T12:00:00+00:00',selling_price_eur='20',supplier_cost_eur='10',referral_pct='15',fulfilment_eur='2',inbound_eur='0.5',other_eur='0.5',returns_pct='3',source_note='Authorized commercial feed',source_url='https://example.org/dp/B008S8RJKK',authorization_reference='PERM-1')
        row.update(updates);f=io.StringIO();w=csv.DictWriter(f,fieldnames=COLUMNS);w.writeheader();w.writerow(row);return f.getvalue()
    def test_valid(self):
        r=inspect_csv(self.feed());self.assertEqual((r['accepted'],r['database_writes'],r['network_requests']),(1,0,0))
    def test_missing_permission(self):
        self.assertEqual(inspect_csv(self.feed(authorization_reference=''))['rejected'],1)
    def test_future_timestamp(self):
        self.assertEqual(inspect_csv(self.feed(observed_at_utc='2099-01-01T00:00:00Z'))['rejected'],1)
    def test_bad_asin(self):
        self.assertEqual(inspect_csv(self.feed(asin='INVALID'))['rejected'],1)
    def test_quota(self):
        with self.assertRaises(ValueError):inspect_csv(self.feed(),max_rows=0)
    def test_missing_columns(self):
        with self.assertRaises(ValueError):inspect_csv('asin,marketplace\na,b\n')
if __name__=='__main__':unittest.main()
