"""Phase 2I: end-to-end *offline* notification processing orchestrator.

No HTTP POST integration or production authorization. The erasure callback must be
implemented and independently audited before this may be used with real events.
"""
from ebay_webhook import authenticate_notification
from ebay_notification_ledger import record_verified_notification
from ebay_phase2h import process_verified_deletion


class Phase2IError(RuntimeError):
    pass


def process_notification_offline(signature_header, raw_body, connection,
                                 inspect_and_erase, *, storage_inventory_approved=False,
                                 key_client=None):
    """Authenticate, stage, and transactionally process a notification.

    `inspect_and_erase(cursor, authenticated_notification)` must perform a
    complete account-identifier match and deletion across the audited stores.
    The Phase 2H callback expects an ID, so the authenticated notification is
    captured in the closure and the ID is never used to identify an eBay user.

    Returns a diagnostic outcome only. Does not authorize HTTP acknowledgment.
    """
    if not storage_inventory_approved or not callable(inspect_and_erase):
        raise Phase2IError('approved storage inventory and erasure handler required')
    event = authenticate_notification(signature_header, raw_body, key_client=key_client)
    note = event['notification']
    notification_id = note['notificationId']
    # Authenticated payload contains the user identity; notificationId does not.
    user_data = note['data']
    if not any(user_data.get(key) for key in ('userId', 'username', 'eiasToken')):
        raise Phase2IError('authenticated event lacks an account identifier')
    # Ledger commit must happen only after successful signature verification.
    record_verified_notification(connection, notification_id)

    def approved_erasure(cursor, _notification_id):
        return inspect_and_erase(cursor, event)

    outcome = process_verified_deletion(
        connection, notification_id, approved_erasure,
        storage_inventory_approved=True,
    )
    return {'state': outcome.state, 'erased_records': outcome.erased_records,
            'http_acknowledgment_authorized': False}
