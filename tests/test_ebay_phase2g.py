import unittest
from unittest.mock import patch, MagicMock
from ebay_phase2g import stage_verified_notification, Phase2GError

class Phase2GTests(unittest.TestCase):
    def setUp(self):
        self.conn = MagicMock()
        self.event = {"notification": {"notificationId": "event-123"}}

    @patch("ebay_phase2g.read_notification_status", return_value="received")
    @patch("ebay_phase2g.record_verified_notification", return_value=True)
    @patch("ebay_phase2g.authenticate_notification")
    def test_verified_new_event_is_never_acknowledgeable(self, auth, record, status):
        auth.return_value = self.event
        result = stage_verified_notification("header", b"payload", self.conn)
        self.assertTrue(result["new_record"])
        self.assertFalse(result["may_acknowledge"])
        self.assertFalse(result["deletion_complete"])
        record.assert_called_once_with(self.conn, "event-123")

    @patch("ebay_phase2g.read_notification_status", return_value="received")
    @patch("ebay_phase2g.record_verified_notification", return_value=False)
    @patch("ebay_phase2g.authenticate_notification", return_value={"notification": {"notificationId": "event-123"}})
    def test_duplicate_never_acknowledged(self, auth, record, status):
        result = stage_verified_notification("header", b"payload", self.conn)
        self.assertFalse(result["new_record"])
        self.assertFalse(result["may_acknowledge"])

    @patch("ebay_phase2g.record_verified_notification")
    @patch("ebay_phase2g.authenticate_notification", side_effect=ValueError("bad signature"))
    def test_bad_signature_never_touches_database(self, auth, record):
        with self.assertRaises(ValueError):
            stage_verified_notification("bad", b"payload", self.conn)
        record.assert_not_called()

    @patch("ebay_phase2g.record_verified_notification", side_effect=RuntimeError("DB unavailable"))
    @patch("ebay_phase2g.authenticate_notification", return_value={"notification": {"notificationId": "event-123"}})
    def test_db_failure_is_not_success(self, auth, record):
        with self.assertRaises(Phase2GError):
            stage_verified_notification("header", b"payload", self.conn)

    @patch("ebay_phase2g.read_notification_status", return_value=None)
    @patch("ebay_phase2g.record_verified_notification", return_value=True)
    @patch("ebay_phase2g.authenticate_notification", return_value={"notification": {"notificationId": "event-123"}})
    def test_missing_status_fails_closed(self, auth, record, status):
        with self.assertRaises(Phase2GError):
            stage_verified_notification("header", b"payload", self.conn)

if __name__ == "__main__":
    unittest.main()
