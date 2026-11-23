
"""Phase 2R.3: Disposable PostgreSQL integration tests.

Only runs against the explicitly named local test database.
Never uses DATABASE_URL or production Neon credentials.
"""

import os
import uuid

import psycopg2
import pytest

from ebay_notification_ledger import (
    notification_fingerprint,
    record_verified_notification,
    read_notification_status,
)
from ebay_phase2h import (
    DeletionProcessingError,
    process_verified_deletion,
)


TEST_DSN = (
    "host=127.0.0.1 port=5432 "
    "dbname=ebay_phase2r_test "
    "user=ebay_test password=local_test_only"
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS public.ebay_notification_ledger (
    notification_fingerprint text PRIMARY KEY
        CHECK (length(notification_fingerprint) = 64),
    status text NOT NULL DEFAULT 'received'
        CHECK (status IN (
            'received', 'processing', 'completed', 'failed'
        )),
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
"""


@pytest.fixture
def db():
    if os.getenv("EBAY_LOCAL_PG_TEST") != "1":
        pytest.skip("Disposable PostgreSQL test not enabled")

    connection = psycopg2.connect(TEST_DSN)

    try:
        with connection.cursor() as cursor:
            cursor.execute(SCHEMA)
        connection.commit()

        yield connection
    finally:
        connection.rollback()
        connection.close()


def new_id():
    return "offline-" + uuid.uuid4().hex


def test_real_postgres_insert_and_duplicate(db):
    notification_id = new_id()

    assert record_verified_notification(
        db, notification_id
    ) is True

    assert record_verified_notification(
        db, notification_id
    ) is False

    assert read_notification_status(
        db, notification_id
    ) == "received"


def test_real_postgres_successful_transaction(db):
    notification_id = new_id()
    record_verified_notification(db, notification_id)

    outcome = process_verified_deletion(
        db,
        notification_id,
        lambda cursor, notification_id: 0,
        storage_inventory_approved=True,
    )

    assert outcome.state == "completed"
    assert outcome.erased_records == 0
    assert outcome.acknowledged is False
    assert read_notification_status(
        db, notification_id
    ) == "completed"


def test_real_postgres_rollback(db):
    notification_id = new_id()
    record_verified_notification(db, notification_id)

    def fail(cursor, notification_id):
        raise RuntimeError("simulated erasure failure")

    with pytest.raises(DeletionProcessingError):
        process_verified_deletion(
            db,
            notification_id,
            fail,
            storage_inventory_approved=True,
        )

    assert read_notification_status(
        db, notification_id
    ) == "received"


def test_real_postgres_duplicate_processing(db):
    notification_id = new_id()
    record_verified_notification(db, notification_id)

    calls = []

    def handler(cursor, notification_id):
        calls.append(notification_id)
        return 0

    first = process_verified_deletion(
        db, notification_id, handler,
        storage_inventory_approved=True,
    )

    second = process_verified_deletion(
        db, notification_id, handler,
        storage_inventory_approved=True,
    )

    assert first.state == "completed"
    assert second.state == "completed"
    assert second.erased_records == 0
    assert calls == [notification_id]
    assert second.acknowledged is False


def test_real_postgres_missing_notification(db):
    notification_id = new_id()

    with pytest.raises(DeletionProcessingError):
        process_verified_deletion(
            db,
            notification_id,
            lambda cursor, notification_id: 0,
            storage_inventory_approved=True,
        )

    assert read_notification_status(
        db, notification_id
    ) is None


def test_real_postgres_fingerprint_storage(db):
    notification_id = new_id()
    record_verified_notification(db, notification_id)

    digest = notification_fingerprint(notification_id)

    with db.cursor() as cursor:
        cursor.execute(
            "SELECT notification_fingerprint, status "
            "FROM public.ebay_notification_ledger "
            "WHERE notification_fingerprint = %s",
            (digest,),
        )
        row = cursor.fetchone()

    assert row == (digest, "received")
    assert notification_id != digest
