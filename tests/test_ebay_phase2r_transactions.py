
"""Phase 2R.2: Offline transactional workflow tests.

Simulates a database connection with commit and rollback behavior.
No Neon connection, customer records, or external network access.
"""

import pytest

from ebay_notification_ledger import (
    LedgerError,
    notification_fingerprint,
    read_notification_status,
    record_verified_notification,
)
from ebay_phase2h import (
    DeletionProcessingError,
    process_verified_deletion,
)


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.result = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        db = self.connection
        digest = params[0]
        normalized = " ".join(sql.split()).lower()

        if db.fail_next_execute:
            db.fail_next_execute = False
            raise RuntimeError("simulated SQL failure")

        db.statements.append(normalized)

        if "insert into" in normalized:
            if digest in db.pending:
                self.result = None
            else:
                db.pending[digest] = "received"
                self.result = (digest,)

        elif "select status" in normalized:
            state = db.pending.get(digest)
            self.result = (state,) if state is not None else None

        elif "set status='processing'" in normalized:
            db.pending[digest] = "processing"
            self.result = None

        elif "set status='completed'" in normalized:
            db.pending[digest] = "completed"
            self.result = None

        else:
            raise AssertionError(
                "Unexpected SQL: " + normalized
            )

    def fetchone(self):
        return self.result


class FakeConnection:
    def __init__(self):
        self.durable = {}
        self.pending = {}
        self.commits = 0
        self.rollbacks = 0
        self.statements = []
        self.fail_next_execute = False

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.durable = self.pending.copy()
        self.commits += 1

    def rollback(self):
        self.pending = self.durable.copy()
        self.rollbacks += 1


def test_record_notification_commits():
    db = FakeConnection()

    assert record_verified_notification(db, "event-001") is True

    digest = notification_fingerprint("event-001")

    assert db.durable[digest] == "received"
    assert db.commits == 1
    assert db.rollbacks == 0


def test_duplicate_notification_not_inserted_twice():
    db = FakeConnection()

    assert record_verified_notification(db, "event-001") is True
    assert record_verified_notification(db, "event-001") is False

    assert len(db.durable) == 1


def test_record_failure_rolls_back():
    db = FakeConnection()
    db.fail_next_execute = True

    with pytest.raises(LedgerError):
        record_verified_notification(db, "event-001")

    assert db.rollbacks == 1
    assert db.durable == {}


def test_successful_deletion_transaction():
    db = FakeConnection()
    record_verified_notification(db, "event-001")

    calls = []

    def erase(cursor, notification_id):
        calls.append(notification_id)
        return 3

    outcome = process_verified_deletion(
        db,
        "event-001",
        erase,
        storage_inventory_approved=True,
    )

    digest = notification_fingerprint("event-001")

    assert outcome.state == "completed"
    assert outcome.erased_records == 3
    assert outcome.acknowledged is False
    assert db.durable[digest] == "completed"
    assert calls == ["event-001"]


def test_completed_notification_not_erased_twice():
    db = FakeConnection()
    record_verified_notification(db, "event-001")

    calls = []

    def erase(cursor, notification_id):
        calls.append(notification_id)
        return 2

    first = process_verified_deletion(
        db, "event-001", erase,
        storage_inventory_approved=True,
    )

    second = process_verified_deletion(
        db, "event-001", erase,
        storage_inventory_approved=True,
    )

    assert first.erased_records == 2
    assert second.erased_records == 0
    assert calls == ["event-001"]
    assert second.acknowledged is False


def test_erasure_exception_rolls_back():
    db = FakeConnection()
    record_verified_notification(db, "event-001")

    def failing_erase(cursor, notification_id):
        raise RuntimeError("simulated erasure failure")

    with pytest.raises(DeletionProcessingError):
        process_verified_deletion(
            db,
            "event-001",
            failing_erase,
            storage_inventory_approved=True,
        )

    digest = notification_fingerprint("event-001")

    assert db.durable[digest] == "received"
    assert db.rollbacks == 1


@pytest.mark.parametrize("invalid_result", [
    None,
    -1,
    True,
    False,
    "3",
    2.5,
])
def test_invalid_erasure_result_rolls_back(invalid_result):
    db = FakeConnection()
    record_verified_notification(db, "event-001")

    with pytest.raises(DeletionProcessingError):
        process_verified_deletion(
            db,
            "event-001",
            lambda cursor, notification_id: invalid_result,
            storage_inventory_approved=True,
        )

    digest = notification_fingerprint("event-001")

    assert db.durable[digest] == "received"
    assert db.rollbacks == 1


def test_unstaged_notification_rejected():
    db = FakeConnection()

    with pytest.raises(DeletionProcessingError):
        process_verified_deletion(
            db,
            "missing-event",
            lambda cursor, notification_id: 0,
            storage_inventory_approved=True,
        )

    assert db.rollbacks == 1


def test_storage_approval_required():
    db = FakeConnection()
    record_verified_notification(db, "event-001")

    with pytest.raises(DeletionProcessingError):
        process_verified_deletion(
            db,
            "event-001",
            lambda cursor, notification_id: 0,
            storage_inventory_approved=False,
        )


def test_invalid_callback_rejected():
    db = FakeConnection()
    record_verified_notification(db, "event-001")

    with pytest.raises(DeletionProcessingError):
        process_verified_deletion(
            db,
            "event-001",
            None,
            storage_inventory_approved=True,
        )


def test_zero_record_erasure_allowed():
    db = FakeConnection()
    record_verified_notification(db, "event-001")

    outcome = process_verified_deletion(
        db,
        "event-001",
        lambda cursor, notification_id: 0,
        storage_inventory_approved=True,
    )

    assert outcome.state == "completed"
    assert outcome.erased_records == 0
    assert outcome.acknowledged is False


def test_read_notification_status():
    db = FakeConnection()

    assert read_notification_status(db, "event-001") is None

    record_verified_notification(db, "event-001")

    assert read_notification_status(db, "event-001") == "received"


def test_unknown_ledger_status_rejected():
    db = FakeConnection()
    digest = notification_fingerprint("event-001")

    db.durable[digest] = "unknown"
    db.pending[digest] = "unknown"

    with pytest.raises(LedgerError):
        read_notification_status(db, "event-001")


def test_processing_state_can_be_retried():
    db = FakeConnection()
    digest = notification_fingerprint("event-001")

    db.durable[digest] = "processing"
    db.pending[digest] = "processing"

    outcome = process_verified_deletion(
        db,
        "event-001",
        lambda cursor, notification_id: 1,
        storage_inventory_approved=True,
    )

    assert outcome.state == "completed"
    assert db.durable[digest] == "completed"


def test_failed_state_can_be_retried():
    db = FakeConnection()
    digest = notification_fingerprint("event-001")

    db.durable[digest] = "failed"
    db.pending[digest] = "failed"

    outcome = process_verified_deletion(
        db,
        "event-001",
        lambda cursor, notification_id: 1,
        storage_inventory_approved=True,
    )

    assert outcome.state == "completed"
    assert db.durable[digest] == "completed"


def test_unknown_processing_state_rolls_back():
    db = FakeConnection()
    digest = notification_fingerprint("event-001")

    db.durable[digest] = "unexpected"
    db.pending[digest] = "unexpected"

    with pytest.raises(DeletionProcessingError):
        process_verified_deletion(
            db,
            "event-001",
            lambda cursor, notification_id: 1,
            storage_inventory_approved=True,
        )

    assert db.rollbacks == 1


def test_sql_uses_row_lock():
    db = FakeConnection()
    record_verified_notification(db, "event-001")

    process_verified_deletion(
        db,
        "event-001",
        lambda cursor, notification_id: 0,
        storage_inventory_approved=True,
    )

    assert any(
        "for update" in statement
        for statement in db.statements
    )


def test_processing_failure_never_acknowledged():
    db = FakeConnection()
    record_verified_notification(db, "event-001")

    with pytest.raises(DeletionProcessingError):
        process_verified_deletion(
            db,
            "event-001",
            lambda cursor, notification_id: (_ for _ in ()).throw(
                RuntimeError("failure")
            ),
            storage_inventory_approved=True,
        )

    assert db.rollbacks == 1
