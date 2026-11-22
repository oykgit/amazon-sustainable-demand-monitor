import unittest
from unittest.mock import Mock, patch
from ebay_phase2i import process_notification_offline, Phase2IError

EVENT = {'notification': {'notificationId': 'note-1', 'data': {'userId': 'account-1'}}}

class TestPhase2I(unittest.TestCase):
    def setUp(self):
        self.db = Mock()
        self.erase = Mock(return_value=0)

    def test_unapproved_inventory_never_authenticates_or_writes(self):
        with patch('ebay_phase2i.authenticate_notification') as auth:
            with self.assertRaises(Phase2IError):
                process_notification_offline('sig', b'raw', self.db, self.erase)
            auth.assert_not_called()

    @patch('ebay_phase2i.record_verified_notification')
    @patch('ebay_phase2i.authenticate_notification', side_effect=ValueError('invalid signature'))
    def test_invalid_signature_no_database_write(self, auth, ledger):
        with self.assertRaises(ValueError):
            process_notification_offline('sig', b'raw', self.db, self.erase,
                                         storage_inventory_approved=True)
        ledger.assert_not_called()
        self.erase.assert_not_called()

    @patch('ebay_phase2i.process_verified_deletion')
    @patch('ebay_phase2i.record_verified_notification')
    @patch('ebay_phase2i.authenticate_notification', return_value=EVENT)
    def test_authenticated_event_flows_to_erasure(self, auth, ledger, process):
        process.side_effect = lambda conn, nid, callback, **kw: Mock(
            state='completed', erased_records=callback(Mock(), nid))
        result = process_notification_offline('sig', b'raw', self.db, self.erase,
                                              storage_inventory_approved=True)
        self.erase.assert_called_once()
        self.assertEqual(self.erase.call_args.args[1], EVENT)
        ledger.assert_called_once_with(self.db, 'note-1')
        self.assertFalse(result['http_acknowledgment_authorized'])

    @patch('ebay_phase2i.process_verified_deletion', side_effect=RuntimeError('rollback'))
    @patch('ebay_phase2i.record_verified_notification')
    @patch('ebay_phase2i.authenticate_notification', return_value=EVENT)
    def test_transaction_failure_not_success(self, auth, ledger, process):
        with self.assertRaises(RuntimeError):
            process_notification_offline('sig', b'raw', self.db, self.erase,
                                         storage_inventory_approved=True)

    @patch('ebay_phase2i.record_verified_notification')
    @patch('ebay_phase2i.authenticate_notification', return_value={
        'notification': {'notificationId': 'note-1', 'data': {}}})
    def test_missing_account_identifier_no_write(self, auth, ledger):
        with self.assertRaises(Phase2IError):
            process_notification_offline('sig', b'raw', self.db, self.erase,
                                         storage_inventory_approved=True)
        ledger.assert_not_called()

if __name__ == '__main__':
    unittest.main()
