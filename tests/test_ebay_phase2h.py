import unittest
from unittest.mock import MagicMock
from ebay_phase2h import process_verified_deletion, DeletionProcessingError

class TestPhase2H(unittest.TestCase):
    def setUp(self):
        self.db=MagicMock()
        self.cur=self.db.cursor.return_value.__enter__.return_value
        self.cur.fetchone.return_value=('received',)

    def run_it(self, handler, approved=True):
        return process_verified_deletion(self.db, 'event-123', handler,
                                         storage_inventory_approved=approved)

    def test_successful_transaction(self):
        outcome=self.run_it(lambda cur, event: 2)
        self.assertEqual(outcome.erased_records, 2)
        self.assertFalse(outcome.acknowledged)
        self.db.commit.assert_called_once()

    def test_no_matching_records_still_requires_approved_handler(self):
        outcome=self.run_it(lambda cur, event: 0)
        self.assertEqual(outcome.state, 'completed')
        self.assertFalse(outcome.acknowledged)

    def test_unapproved_inventory_refused(self):
        with self.assertRaises(DeletionProcessingError):
            self.run_it(lambda cur, event: 0, False)
        self.db.commit.assert_not_called()

    def test_missing_ledger_entry(self):
        self.cur.fetchone.return_value=None
        with self.assertRaises(DeletionProcessingError):
            self.run_it(lambda cur, event: 0)
        self.db.rollback.assert_called_once()

    def test_duplicate_completed_not_reprocessed(self):
        self.cur.fetchone.return_value=('completed',)
        handler=MagicMock()
        result=self.run_it(handler)
        handler.assert_not_called()
        self.assertFalse(result.acknowledged)

    def test_erasure_failure_rolls_back(self):
        def fail(cur, event):
            raise RuntimeError('database failure')
        with self.assertRaises(DeletionProcessingError):
            self.run_it(fail)
        self.db.rollback.assert_called_once()
        self.db.commit.assert_not_called()

    def test_invalid_erasure_result_rolls_back(self):
        with self.assertRaises(DeletionProcessingError):
            self.run_it(lambda cur, event: True)
        self.db.rollback.assert_called_once()

    def test_bad_notification_id_rejected(self):
        with self.assertRaises(ValueError):
            process_verified_deletion(self.db, 'bad id!', lambda cur, event: 0,
                                      storage_inventory_approved=True)
        self.db.commit.assert_not_called()

if __name__ == '__main__':
    unittest.main()
