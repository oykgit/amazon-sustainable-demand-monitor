
"""Phase 2R.5: Disposable-record erasure transaction tests.

Uses only the fixed local PostgreSQL test database.
No production Neon connection, eBay API calls, or customer data.
"""

import os
import uuid

import psycopg2
import pytest

from ebay_notification_ledger import (
    read_notification_status,
    record_verified_notification,
)
from ebay_phase2h import (
    DeletionProcessingError,
    process_verified_deletion,
)


TEST_DSN = (
    "host=127.0.0.1 port=5432 "
    "dbname=ebay_phase2r_test "
    "user=ebay_test password=local_test_only "
    "connect_timeout=5"
)

LEDGER_SCHEMA = """
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

TEMP_SCHEMA = """
CREATE TEMP TABLE ebay_phase2r_synthetic_records (
    record_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    synthetic_account text NOT NULL,
    content text NOT NULL
) ON COMMIT PRESERVE ROWS;
"""


@pytest.fixture
def db():
    if os.getenv("EBAY_LOCAL_PG_TEST") != "1":
        pytest.skip("Disposable PostgreSQL test not enabled")

    conn = psycopg2.connect(TEST_DSN)

    try:
        with conn.cursor() as cur:
            cur.execute(LEDGER_SCHEMA)
            cur.execute(TEMP_SCHEMA)
        conn.commit()

        yield conn
    finally:
        conn.rollback()
        conn.close()


def new_notification():
    return "erasure-" + uuid.uuid4().hex


def seed(db, account, count):
    with db.cursor() as cur:
        for index in range(count):
            cur.execute(
                """
                INSERT INTO ebay_phase2r_synthetic_records
                    (synthetic_account, content)
                VALUES (%s, %s)
                """,
                (account, f"synthetic-record-{index}"),
            )
    db.commit()


def count_records(db, account):
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT count(*)
            FROM ebay_phase2r_synthetic_records
            WHERE synthetic_account = %s
            """,
            (account,),
        )
        return cur.fetchone()[0]


def erasure_for(account):
    """Use a synthetic account identifier, not notification ID."""

    def erase(cur, notification_id):
        cur.execute(
            """
            DELETE FROM ebay_phase2r_synthetic_records
            WHERE synthetic_account = %s
            RETURNING record_id
            """,
            (account,),
        )
        return len(cur.fetchall())

    return erase


def process(db, notification_id, handler):
    return process_verified_deletion(
        db,
        notification_id,
        handler,
        storage_inventory_approved=True,
    )


def test_actual_synthetic_records_deleted(db):
    notification_id = new_notification()
    seed(db, "account-A", 3)
    record_verified_notification(db, notification_id)

    result = process(
        db, notification_id, erasure_for("account-A")
    )

    assert result.state == "completed"
    assert result.erased_records == 3
    assert result.acknowledged is False
    assert count_records(db, "account-A") == 0
    assert read_notification_status(
        db, notification_id
    ) == "completed"


def test_unrelated_records_remain_untouched(db):
    notification_id = new_notification()
    seed(db, "account-A", 2)
    seed(db, "account-B", 4)
    record_verified_notification(db, notification_id)

    result = process(
        db, notification_id, erasure_for("account-A")
    )

    assert result.erased_records == 2
    assert count_records(db, "account-A") == 0
    assert count_records(db, "account-B") == 4


def test_failure_after_delete_rolls_back_everything(db):
    notification_id = new_notification()
    seed(db, "account-A", 3)
    record_verified_notification(db, notification_id)

    def failing_handler(cur, event_id):
        cur.execute(
            """
            DELETE FROM ebay_phase2r_synthetic_records
            WHERE synthetic_account = %s
            """,
            ("account-A",),
        )
        raise RuntimeError("simulated failure after deletion")

    with pytest.raises(DeletionProcessingError):
        process(db, notification_id, failing_handler)

    assert count_records(db, "account-A") == 3
    assert read_notification_status(
        db, notification_id
    ) == "received"


def test_invalid_result_rolls_back_real_delete(db):
    notification_id = new_notification()
    seed(db, "account-A", 2)
    record_verified_notification(db, notification_id)

    def invalid_handler(cur, event_id):
        cur.execute(
            """
            DELETE FROM ebay_phase2r_synthetic_records
            WHERE synthetic_account = %s
            """,
            ("account-A",),
        )
        return -1

    with pytest.raises(DeletionProcessingError):
        process(db, notification_id, invalid_handler)

    assert count_records(db, "account-A") == 2
    assert read_notification_status(
        db, notification_id
    ) == "received"


def test_duplicate_does_not_delete_new_records(db):
    notification_id = new_notification()
    seed(db, "account-A", 2)
    record_verified_notification(db, notification_id)

    calls = []

    def handler(cur, event_id):
        calls.append(event_id)
        return erasure_for("account-A")(cur, event_id)

    first = process(db, notification_id, handler)

    assert first.erased_records == 2
    assert count_records(db, "account-A") == 0

    # New synthetic data after the first completed notification.
    seed(db, "account-A", 1)

    second = process(db, notification_id, handler)

    assert second.erased_records == 0
    assert second.acknowledged is False
    assert calls == [notification_id]
    assert count_records(db, "account-A") == 1


def test_zero_matching_records(db):
    notification_id = new_notification()
    seed(db, "account-B", 2)
    record_verified_notification(db, notification_id)

    result = process(
        db, notification_id, erasure_for("account-A")
    )

    assert result.state == "completed"
    assert result.erased_records == 0
    assert result.acknowledged is False
    assert count_records(db, "account-B") == 2
    assert read_notification_status(
        db, notification_id
    ) == "completed"
