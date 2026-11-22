import unittest
from ebay_phase2k import assess_inventory, inspect_neon_read_only, refuse_unapproved_erasure


class FakeCursor:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.queries = []
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, sql):
        self.queries.append(sql)
        assert sql.strip().upper().startswith('SELECT')
    def fetchall(self): return next(self.responses)


class FakeConnection:
    def __init__(self, responses): self.cur = FakeCursor(responses)
    def cursor(self): return self.cur


class Phase2KTests(unittest.TestCase):
    def test_known_schema_still_not_authorized(self):
        r = assess_inventory([('public', 'asin_price_snapshots', 'asin')])
        self.assertFalse(r.account_erasure_ready)
        self.assertFalse(r.post_activation_authorized)
        self.assertEqual(r.unknown_tables, ())

    def test_unknown_table_detected(self):
        r = assess_inventory([('public', 'ebay_accounts', 'ebay_user_id')])
        self.assertIn('public.ebay_accounts', r.unknown_tables)
        self.assertIn('public.ebay_accounts.ebay_user_id', r.candidate_columns)

    def test_candidate_column_detected_in_known_table(self):
        r = assess_inventory([('public', 'asin_research_watchlist', 'seller_username')])
        self.assertEqual(len(r.candidate_columns), 1)

    def test_internal_fingerprint_not_personal_account_identifier(self):
        r = assess_inventory([('public', 'ebay_notification_ledger', 'notification_fingerprint')])
        self.assertEqual(r.candidate_columns, ())

    def test_metadata_only_and_extra_schema(self):
        db = FakeConnection([[('public', 'asin_price_snapshots', 'asin')], [('private',)]])
        r = inspect_neon_read_only(db)
        self.assertEqual(r.extra_schemas, ('private',))
        self.assertEqual(len(db.cur.queries), 2)

    def test_erasure_guard_always_refuses(self):
        with self.assertRaises(RuntimeError):
            refuse_unapproved_erasure(None, {'notification': {'data': {'userId': 'x'}}})

    def test_invalid_metadata_refused(self):
        with self.assertRaises(ValueError):
            assess_inventory([('public', None, 'name')])


if __name__ == '__main__': unittest.main()
