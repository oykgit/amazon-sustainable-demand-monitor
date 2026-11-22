import hashlib
import unittest
from ebay_notification_ledger import (
    notification_fingerprint, record_verified_notification,
    read_notification_status, LedgerError,
)

class FakeCursor:
    def __init__(self, conn): self.conn = conn; self.result = None
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, query, params):
        if self.conn.fail: raise RuntimeError('database unavailable')
        digest = params[0]
        if query.strip().startswith('INSERT'):
            self.result = (digest,) if digest not in self.conn.rows else None
            if self.result: self.conn.rows[digest] = 'received'
        elif query.strip().startswith('SELECT'):
            self.result = (self.conn.rows[digest],) if digest in self.conn.rows else None
        else: raise AssertionError('unexpected SQL')
    def fetchone(self): return self.result

class FakeConnection:
    def __init__(self): self.rows = {}; self.fail = False; self.commits = 0; self.rollbacks = 0
    def cursor(self): return FakeCursor(self)
    def commit(self): self.commits += 1
    def rollback(self): self.rollbacks += 1

class LedgerTests(unittest.TestCase):
    def test_fingerprint(self):
        self.assertEqual(notification_fingerprint('evt-1'), hashlib.sha256(b'evt-1').hexdigest())
    def test_reject_bad_id(self):
        for value in ('', 'a'*257, 'bad id', None):
            with self.subTest(value=value), self.assertRaises(ValueError): notification_fingerprint(value)
    def test_insert_and_duplicate(self):
        conn = FakeConnection()
        self.assertTrue(record_verified_notification(conn, 'evt-1'))
        self.assertFalse(record_verified_notification(conn, 'evt-1'))
        self.assertEqual(len(conn.rows), 1)
        self.assertEqual(conn.commits, 2)
    def test_read_status(self):
        conn = FakeConnection()
        self.assertIsNone(read_notification_status(conn, 'evt-1'))
        record_verified_notification(conn, 'evt-1')
        self.assertEqual(read_notification_status(conn, 'evt-1'), 'received')
    def test_failure_rolls_back(self):
        conn = FakeConnection(); conn.fail = True
        with self.assertRaises(LedgerError): record_verified_notification(conn, 'evt-1')
        self.assertEqual(conn.rollbacks, 1)
        self.assertEqual(conn.commits, 0)
    def test_no_plaintext_id(self):
        conn = FakeConnection()
        record_verified_notification(conn, 'sensitive-notification-id')
        self.assertNotIn('sensitive-notification-id', conn.rows)

if __name__ == '__main__': unittest.main()
