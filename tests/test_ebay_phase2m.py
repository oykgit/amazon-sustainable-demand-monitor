"""Offline integration tests using Phase 2I, 2H, 2L modules, no external calls."""
import importlib
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from ebay_phase2m import inspect_repository
from ebay_phase2l import AccountStore, ErasurePolicy, make_erasure_callback, ErasurePolicyError
from ebay_phase2i import process_notification_offline, Phase2IError
from ebay_phase2h import DeletionProcessingError
from ebay_notification_ledger import notification_fingerprint


class Cursor:
    def __init__(self, conn): self.conn = conn; self.rowcount = 0; self._row = None
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, sql, args=()):
        self.conn.statements.append((sql, args))
        if 'FOR UPDATE' in sql:
            self._row = (self.conn.status,) if self.conn.status else None
        elif 'information_schema.columns' in sql:
            self._row = (1,) if self.conn.schema_valid else None
        elif 'DELETE FROM' in sql:
            if self.conn.fail_delete: raise RuntimeError('simulated deletion failure')
            self.rowcount = self.conn.matched_rows
        elif "SET status='completed'" in sql:
            self.conn.pending_status = 'completed'
        elif "SET status='processing'" in sql:
            self.conn.pending_status = 'processing'
    def fetchone(self): return self._row


class Connection:
    def __init__(self, status='received', matched_rows=2):
        self.status=status; self.pending_status=None; self.matched_rows=matched_rows
        self.schema_valid=True; self.fail_delete=False
        self.statements=[]; self.commits=0; self.rollbacks=0
    def cursor(self): return Cursor(self)
    def commit(self):
        self.commits += 1
        if self.pending_status: self.status=self.pending_status; self.pending_status=None
    def rollback(self): self.rollbacks += 1; self.pending_status=None


def event():
    return {'metadata': {'topic':'MARKETPLACE_ACCOUNT_DELETION'},
            'notification': {'notificationId':'notification-123',
                             'data': {'userId':'account-abc'}}}


def policy():
    return ErasurePolicy((AccountStore('public','ebay_account_test','ebay_user_id','userId'),),
                         inventory_reviewed=True,external_storage_reviewed=True,
                         exact_identity_mapping_reviewed=True,no_other_account_stores=True)


def run(conn, *, callback=None, approved=True, authenticate=None):
    with patch('ebay_phase2i.authenticate_notification', side_effect=authenticate or (lambda *a, **k: event())), \
         patch('ebay_phase2i.record_verified_notification', return_value=True):
        return process_notification_offline('fake-signature',b'fake-body',conn,
            callback if callback is not None else make_erasure_callback(policy()),
            storage_inventory_approved=approved)


class Phase2MTests(unittest.TestCase):
    def test_successful_transaction_still_cannot_ack(self):
        conn=Connection()
        outcome=run(conn)
        self.assertEqual(outcome['erased_records'],2)
        self.assertEqual(conn.status,'completed')
        self.assertFalse(outcome['http_acknowledgment_authorized'])
        self.assertTrue(any('DELETE FROM' in q for q,_ in conn.statements))

    def test_duplicate_does_not_erase_twice(self):
        conn=Connection(status='completed')
        outcome=run(conn)
        self.assertEqual(outcome['erased_records'],0)
        self.assertFalse(any('DELETE FROM' in q for q,_ in conn.statements))

    def test_failed_delete_rolls_back(self):
        conn=Connection(); conn.fail_delete=True
        with self.assertRaises(DeletionProcessingError): run(conn)
        self.assertEqual(conn.rollbacks,1)
        self.assertEqual(conn.status,'received')

    def test_schema_drift_prevents_delete(self):
        conn=Connection(); conn.schema_valid=False
        with self.assertRaises(DeletionProcessingError): run(conn)
        self.assertFalse(any('DELETE FROM' in q for q,_ in conn.statements))

    def test_no_approved_inventory_prevents_authentication_and_writes(self):
        conn=Connection()
        with patch('ebay_phase2i.authenticate_notification') as auth, \
             patch('ebay_phase2i.record_verified_notification') as ledger:
            with self.assertRaises(Phase2IError):
                process_notification_offline('sig',b'body',conn,lambda *args:0,
                                             storage_inventory_approved=False)
            auth.assert_not_called(); ledger.assert_not_called()

    def test_authentication_failure_prevents_database_actions(self):
        conn=Connection()
        with patch('ebay_phase2i.authenticate_notification',side_effect=ValueError('invalid signature')), \
             patch('ebay_phase2i.record_verified_notification') as ledger:
            with self.assertRaises(ValueError):
                process_notification_offline('sig',b'body',conn,make_erasure_callback(policy()),
                                             storage_inventory_approved=True)
            ledger.assert_not_called()
            self.assertFalse(conn.statements)

    def test_notification_id_not_used_for_user_matching(self):
        conn=Connection()
        run(conn)
        deletes=[(q,args) for q,args in conn.statements if 'DELETE FROM' in q]
        self.assertEqual(deletes[0][1],('account-abc',))
        self.assertNotEqual(deletes[0][1],('notification-123',))

    def test_zero_store_policy_not_approved(self):
        empty=ErasurePolicy((),True,True,True,True)
        with self.assertRaises(ErasurePolicyError): make_erasure_callback(empty)

    def test_missing_repo_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            result=inspect_repository(d)
        self.assertFalse(result['offline_preflight_passed'])
        self.assertFalse(result['production_ready'])

    def test_static_preflight_not_production_certification(self):
        root=Path(__file__).resolve().parents[1]
        result=inspect_repository(root)
        self.assertFalse(result['production_ready'])
        self.assertFalse(result['live_ebay_tested'])
        self.assertFalse(result['live_neon_tested'])
        self.assertEqual(len(result['blocking_evidence']),7)


if __name__=='__main__': unittest.main()
