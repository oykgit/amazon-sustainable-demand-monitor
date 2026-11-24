
"""Phase 2R.8 exception-handling regression tests.

No production database access or external requests.
"""

from unittest.mock import MagicMock

import pytest

from ebay_phase2h import (
    DeletionProcessingError,
    process_verified_deletion,
)


NOTIFICATION_ID = "phase2r8-synthetic-notification"


def make_connection(status="received"):
    connection = MagicMock()

    cursor = (
        connection.cursor.return_value
        .__enter__.return_value
    )

    cursor.fetchone.return_value = (status,)

    return connection, cursor


def run_processing(connection, handler):
    return process_verified_deletion(
        connection,
        NOTIFICATION_ID,
        handler,
        storage_inventory_approved=True,
    )


def test_original_exception_preserved_after_rollback():
    connection, cursor = make_connection()

    original = RuntimeError(
        "Synthetic erasure failure"
    )

    handler = MagicMock(side_effect=original)

    with pytest.raises(
        DeletionProcessingError
    ) as error:
        run_processing(connection, handler)

    assert error.value.__cause__ is original

    connection.rollback.assert_called_once()
    connection.commit.assert_not_called()
    connection.close.assert_not_called()


def test_rollback_failure_preserves_original_exception():
    connection, cursor = make_connection()

    original = RuntimeError(
        "Synthetic connection failure"
    )

    handler = MagicMock(side_effect=original)

    connection.rollback.side_effect = RuntimeError(
        "Synthetic rollback failure"
    )

    with pytest.raises(
        DeletionProcessingError
    ) as error:
        run_processing(connection, handler)

    assert error.value.__cause__ is original

    assert "rollback failed" in str(error.value)

    connection.rollback.assert_called_once()
    connection.close.assert_called_once()
    connection.commit.assert_not_called()


def test_close_failure_does_not_mask_original_exception():
    connection, cursor = make_connection()

    original = RuntimeError(
        "Synthetic transaction failure"
    )

    handler = MagicMock(side_effect=original)

    connection.rollback.side_effect = RuntimeError(
        "Rollback unavailable"
    )

    connection.close.side_effect = RuntimeError(
        "Close unavailable"
    )

    with pytest.raises(
        DeletionProcessingError
    ) as error:
        run_processing(connection, handler)

    assert error.value.__cause__ is original

    connection.rollback.assert_called_once()
    connection.close.assert_called_once()


def test_cursor_creation_failure():
    connection, cursor = make_connection()

    original = RuntimeError(
        "Cursor unavailable"
    )

    connection.cursor.side_effect = original

    handler = MagicMock(return_value=1)

    with pytest.raises(
        DeletionProcessingError
    ) as error:
        run_processing(connection, handler)

    assert error.value.__cause__ is original

    handler.assert_not_called()
    connection.rollback.assert_called_once()
    connection.commit.assert_not_called()


def test_commit_failure_does_not_return_success():
    connection, cursor = make_connection()

    original = RuntimeError(
        "Commit outcome uncertain"
    )

    connection.commit.side_effect = original

    handler = MagicMock(return_value=3)

    with pytest.raises(
        DeletionProcessingError
    ) as error:
        run_processing(connection, handler)

    assert error.value.__cause__ is original

    handler.assert_called_once()
    connection.commit.assert_called_once()
    connection.rollback.assert_called_once()


def test_commit_and_rollback_failure():
    connection, cursor = make_connection()

    original = RuntimeError(
        "Connection lost during commit"
    )

    connection.commit.side_effect = original

    connection.rollback.side_effect = RuntimeError(
        "Connection no longer available"
    )

    handler = MagicMock(return_value=3)

    with pytest.raises(
        DeletionProcessingError
    ) as error:
        run_processing(connection, handler)

    assert error.value.__cause__ is original

    assert "reconcile durable state" in str(error.value)

    connection.close.assert_called_once()


def test_successful_processing_remains_unchanged():
    connection, cursor = make_connection()

    handler = MagicMock(return_value=4)

    result = run_processing(connection, handler)

    assert result.state == "completed"
    assert result.erased_records == 4
    assert result.acknowledged is False

    handler.assert_called_once_with(
        cursor,
        NOTIFICATION_ID,
    )

    connection.commit.assert_called_once()
    connection.rollback.assert_not_called()


def test_completed_notification_still_skips_erasure():
    connection, cursor = make_connection(
        status="completed"
    )

    handler = MagicMock(return_value=4)

    result = run_processing(connection, handler)

    assert result.state == "completed"
    assert result.erased_records == 0
    assert result.acknowledged is False

    handler.assert_not_called()
    connection.commit.assert_called_once()


def test_inventory_approval_still_required():
    connection, cursor = make_connection()

    handler = MagicMock(return_value=4)

    with pytest.raises(DeletionProcessingError):
        process_verified_deletion(
            connection,
            NOTIFICATION_ID,
            handler,
            storage_inventory_approved=False,
        )

    connection.cursor.assert_not_called()
    connection.commit.assert_not_called()
    connection.rollback.assert_not_called()
    handler.assert_not_called()


@pytest.mark.parametrize(
    "invalid_result",
    [-1, True, False, None, "3", 2.5],
)
def test_invalid_erasure_results_remain_rejected(
    invalid_result,
):
    connection, cursor = make_connection()

    handler = MagicMock(
        return_value=invalid_result
    )

    with pytest.raises(DeletionProcessingError):
        run_processing(connection, handler)

    connection.rollback.assert_called_once()
    connection.commit.assert_not_called()
