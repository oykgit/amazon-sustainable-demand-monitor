"""Phase 2G: authenticated notification -> durable ledger, staging only.

No HTTP acknowledgments, user-data deletion, or production POST activation.
The caller must keep returning non-2xx until deletion handling is implemented.
"""
from ebay_webhook import authenticate_notification
from ebay_notification_ledger import record_verified_notification, read_notification_status, LedgerError

class Phase2GError(RuntimeError):
    pass

def stage_verified_notification(signature_header, raw_body, connection, key_client=None):
    """Verify BEFORE database access, then persist fingerprint; return diagnostic status.

    This is NOT a deletion completion signal. Never acknowledge eBay based on it.
    """
    event = authenticate_notification(signature_header, raw_body, key_client=key_client)
    notification_id = event["notification"]["notificationId"]
    try:
        created = record_verified_notification(connection, notification_id)
        status = read_notification_status(connection, notification_id)
    except Exception as exc:
        raise Phase2GError("durable staging failed") from exc
    if status not in {"received", "processing", "completed", "failed"}:
        raise Phase2GError("missing or invalid durable status")
    return {"new_record": created, "ledger_status": status, "deletion_complete": False,
            "may_acknowledge": False}
