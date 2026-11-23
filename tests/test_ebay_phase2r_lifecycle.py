
"""Phase 2R.1: Offline notification lifecycle tests.

No external network requests, database writes, or actual erasure.
Uses mocks to verify orchestration and fail-closed behavior.
"""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

import ebay_phase2i
from ebay_phase2i import (
    Phase2IError,
    process_notification_offline,
)


EVENT = {
    "metadata": {
        "topic": "MARKETPLACE_ACCOUNT_DELETION"
    },
    "notification": {
        "notificationId": "offline-notification-001",
        "data": {
            "userId": "offline-user-001"
        },
    },
}


def run_offline(
    *,
    approved=True,
    callback=None,
    event=None,
    outcome=None,
):
    connection = Mock(name="offline_connection")
    erasure = callback if callback is not None else Mock(
        return_value=0
    )

    authenticated = EVENT if event is None else event
    processing_result = outcome or SimpleNamespace(
        state="completed",
        erased_records=0,
    )

    with (
        patch.object(
            ebay_phase2i,
            "authenticate_notification",
            return_value=authenticated,
        ) as auth,
        patch.object(
            ebay_phase2i,
            "record_verified_notification",
        ) as ledger,
        patch.object(
            ebay_phase2i,
            "process_verified_deletion",
            return_value=processing_result,
        ) as processor,
    ):
        result = process_notification_offline(
            "offline-signature",
            b'{"offline":true}',
            connection,
            erasure,
            storage_inventory_approved=approved,
        )

    return result, auth, ledger, processor, erasure


def test_successful_offline_lifecycle():
    result, auth, ledger, processor, erasure = run_offline()

    auth.assert_called_once()
    ledger.assert_called_once()
    processor.assert_called_once()

    assert result["state"] == "completed"
    assert result["erased_records"] == 0
    assert result["http_acknowledgment_authorized"] is False


def test_notification_id_used_for_ledger():
    _, _, ledger, processor, _ = run_offline()

    assert ledger.call_args.args[1] == (
        "offline-notification-001"
    )

    assert processor.call_args.args[1] == (
        "offline-notification-001"
    )


def test_callback_receives_authenticated_event():
    captured = []

    def erasure(cursor, event):
        captured.append((cursor, event))
        return 0

    connection = Mock()
    cursor = Mock()

    def fake_processing(
        conn, notification_id, callback, **kwargs
    ):
        callback(cursor, notification_id)
        return SimpleNamespace(
            state="completed",
            erased_records=0,
        )

    with (
        patch.object(
            ebay_phase2i,
            "authenticate_notification",
            return_value=EVENT,
        ),
        patch.object(
            ebay_phase2i,
            "record_verified_notification",
        ),
        patch.object(
            ebay_phase2i,
            "process_verified_deletion",
            side_effect=fake_processing,
        ),
    ):
        result = process_notification_offline(
            "offline-signature",
            b"offline-body",
            connection,
            erasure,
            storage_inventory_approved=True,
        )

    assert len(captured) == 1
    assert captured[0][0] is cursor
    assert captured[0][1] is EVENT
    assert result["http_acknowledgment_authorized"] is False


def test_missing_storage_approval_rejected():
    with pytest.raises(
        Phase2IError,
        match="approved storage inventory",
    ):
        process_notification_offline(
            "signature",
            b"body",
            Mock(),
            Mock(),
            storage_inventory_approved=False,
        )


@pytest.mark.parametrize("callback", [
    None,
    "not-callable",
    123,
    {},
])
def test_invalid_erasure_callback_rejected(callback):
    with pytest.raises(Phase2IError):
        process_notification_offline(
            "signature",
            b"body",
            Mock(),
            callback,
            storage_inventory_approved=True,
        )


def test_invalid_signature_does_not_stage():
    connection = Mock()
    erasure = Mock()

    with (
        patch.object(
            ebay_phase2i,
            "authenticate_notification",
            side_effect=ValueError(
                "invalid authentication"
            ),
        ),
        patch.object(
            ebay_phase2i,
            "record_verified_notification",
        ) as ledger,
        patch.object(
            ebay_phase2i,
            "process_verified_deletion",
        ) as processor,
    ):
        with pytest.raises(ValueError):
            process_notification_offline(
                "bad-signature",
                b"bad-body",
                connection,
                erasure,
                storage_inventory_approved=True,
            )

    ledger.assert_not_called()
    processor.assert_not_called()
    erasure.assert_not_called()


@pytest.mark.parametrize("data", [
    {},
    {"userId": ""},
    {"username": None},
    {"eiasToken": ""},
])
def test_missing_account_identifier_rejected(data):
    event = {
        "notification": {
            "notificationId": "offline-id",
            "data": data,
        }
    }

    connection = Mock()
    erasure = Mock()

    with (
        patch.object(
            ebay_phase2i,
            "authenticate_notification",
            return_value=event,
        ),
        patch.object(
            ebay_phase2i,
            "record_verified_notification",
        ) as ledger,
    ):
        with pytest.raises(Phase2IError):
            process_notification_offline(
                "signature",
                b"body",
                connection,
                erasure,
                storage_inventory_approved=True,
            )

    ledger.assert_not_called()


def test_ledger_failure_prevents_processing():
    erasure = Mock()

    with (
        patch.object(
            ebay_phase2i,
            "authenticate_notification",
            return_value=EVENT,
        ),
        patch.object(
            ebay_phase2i,
            "record_verified_notification",
            side_effect=RuntimeError("ledger failure"),
        ),
        patch.object(
            ebay_phase2i,
            "process_verified_deletion",
        ) as processor,
    ):
        with pytest.raises(RuntimeError):
            process_notification_offline(
                "signature",
                b"body",
                Mock(),
                erasure,
                storage_inventory_approved=True,
            )

    processor.assert_not_called()
    erasure.assert_not_called()


def test_processing_failure_propagates():
    with (
        patch.object(
            ebay_phase2i,
            "authenticate_notification",
            return_value=EVENT,
        ),
        patch.object(
            ebay_phase2i,
            "record_verified_notification",
        ),
        patch.object(
            ebay_phase2i,
            "process_verified_deletion",
            side_effect=RuntimeError(
                "transaction rollback"
            ),
        ),
    ):
        with pytest.raises(
            RuntimeError,
            match="transaction rollback",
        ):
            process_notification_offline(
                "signature",
                b"body",
                Mock(),
                Mock(),
                storage_inventory_approved=True,
            )


@pytest.mark.parametrize("state", [
    "completed",
    "duplicate",
    "pending",
    "failed",
])
def test_all_states_never_authorize_http_ack(state):
    result, *_ = run_offline(
        outcome=SimpleNamespace(
            state=state,
            erased_records=0,
        )
    )

    assert result["http_acknowledgment_authorized"] is False


def test_no_direct_http_response():
    result, *_ = run_offline()

    assert "http_status" not in result
    assert "http_response" not in result
    assert result["http_acknowledgment_authorized"] is False
