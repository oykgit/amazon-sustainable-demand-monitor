"""Offline ledger exception regression tests."""
from unittest.mock import MagicMock
import pytest
from ebay_notification_ledger import LedgerError, record_verified_notification


@pytest.mark.parametrize('failure_point', ['execute', 'commit'])
@pytest.mark.parametrize('cleanup', ['rollback_ok', 'rollback_failed', 'close_failed'])
def test_ledger_preserves_original_error(failure_point, cleanup):
    db = MagicMock()
    cur = db.cursor.return_value.__enter__.return_value
    original = RuntimeError('synthetic original failure')
    if failure_point == 'execute':
        cur.execute.side_effect = original
    else:
        db.commit.side_effect = original
    if cleanup != 'rollback_ok':
        db.rollback.side_effect = RuntimeError('rollback failed')
    if cleanup == 'close_failed':
        db.close.side_effect = RuntimeError('close failed')
    with pytest.raises(LedgerError) as error:
        record_verified_notification(db, 'phase2r8-test')
    assert error.value.__cause__ is original
    db.rollback.assert_called_once()
    if cleanup == 'rollback_ok':
        db.close.assert_not_called()
    else:
        db.close.assert_called_once()
        assert 'reconcile durable state' in str(error.value)
    if failure_point == 'execute':
        db.commit.assert_not_called()
    else:
        db.commit.assert_called_once()
