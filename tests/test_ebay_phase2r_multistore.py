
"""Phase 2R.6: Multi-table consistency and connection-loss recovery.

Disposable PostgreSQL only.
No production credentials, real customer data or live acknowledgments.
"""

import os
import uuid

import psycopg2
from psycopg2 import sql
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

TABLES = (
    "synthetic_profiles",
    "synthetic_activity",
    "synthetic_preferences",
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


def connect(schema):
    conn = psycopg2.connect(TEST_DSN)

    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("SET search_path TO {}, public").format(
                    sql.Identifier(schema)
                )
            )
            cur.execute("SET statement_timeout = '10s'")
            cur.execute("SET lock_timeout = '5s'")
        conn.commit()
        return conn
    except Exception:
        conn.close()
        raise


@pytest.fixture
def environment():
    if os.getenv("EBAY_LOCAL_PG_TEST") != "1":
        pytest.skip("Disposable PostgreSQL tests disabled")

    schema = "phase2r6_" + uuid.uuid4().hex
    admin = psycopg2.connect(TEST_DSN)
    admin.autocommit = True
    db = None

    try:
        with admin.cursor() as cur:
            cur.execute(LEDGER_SCHEMA)
            cur.execute(
                sql.SQL("CREATE SCHEMA {}").format(
                    sql.Identifier(schema)
                )
            )

        db = connect(schema)

        with db.cursor() as cur:
            for table in TABLES:
                cur.execute(
                    sql.SQL("""
                        CREATE TABLE {} (
                            record_id integer
                                GENERATED ALWAYS AS IDENTITY
                                PRIMARY KEY,
                            synthetic_account text NOT NULL,
                            content text NOT NULL
                        )
                    """).format(sql.Identifier(table))
                )

        db.commit()

        yield db, admin, schema

    finally:
        if db is not None:
            db.close()

        try:
            with admin.cursor() as cur:
                cur.execute(
                    sql.SQL(
                        "DROP SCHEMA IF EXISTS {} CASCADE"
                    ).format(sql.Identifier(schema))
                )
        finally:
            admin.close()


def new_notification():
    return "multistore-" + uuid.uuid4().hex


def seed(db, account, count=2):
    with db.cursor() as cur:
        for table in TABLES:
            for index in range(count):
                cur.execute(
                    sql.SQL("""
                        INSERT INTO {}
                            (synthetic_account, content)
                        VALUES (%s, %s)
                    """).format(sql.Identifier(table)),
                    (account, f"synthetic-{index}"),
                )
    db.commit()


def counts(db, account):
    result = {}

    with db.cursor() as cur:
        for table in TABLES:
            cur.execute(
                sql.SQL("""
                    SELECT count(*)
                    FROM {}
                    WHERE synthetic_account = %s
                """).format(sql.Identifier(table)),
                (account,),
            )
            result[table] = cur.fetchone()[0]

    return result


def assert_counts(db, account, expected):
    assert counts(db, account) == {
        table: expected for table in TABLES
    }


def delete_from_table(cur, table, account):
    cur.execute(
        sql.SQL("""
            DELETE FROM {}
            WHERE synthetic_account = %s
            RETURNING record_id
        """).format(sql.Identifier(table)),
        (account,),
    )
    return len(cur.fetchall())


def erase_all(cur, notification_id):
    return sum(
        delete_from_table(cur, table, "account-A")
        for table in TABLES
    )


def partial_failure(cur, notification_id):
    delete_from_table(cur, TABLES[0], "account-A")
    delete_from_table(cur, TABLES[1], "account-A")

    raise RuntimeError(
        "Simulated failure before final storage table"
    )


def process(db, notification_id, handler):
    return process_verified_deletion(
        db,
        notification_id,
        handler,
        storage_inventory_approved=True,
    )


def prepare(db):
    notification_id = new_notification()

    seed(db, "account-A", 2)
    seed(db, "account-B", 3)

    record_verified_notification(db, notification_id)

    return notification_id


def test_successful_multistore_erasure(environment):
    db, admin, schema = environment
    notification_id = prepare(db)

    result = process(db, notification_id, erase_all)

    assert result.state == "completed"
    assert result.erased_records == 6
    assert result.acknowledged is False

    # Verify committed results from a separate connection.
    observer = connect(schema)

    try:
        assert_counts(observer, "account-A", 0)
        assert_counts(observer, "account-B", 3)

        assert read_notification_status(
            observer, notification_id
        ) == "completed"
    finally:
        observer.close()


def test_partial_multistore_failure_rolls_back(environment):
    db, admin, schema = environment
    notification_id = prepare(db)

    with pytest.raises(DeletionProcessingError):
        process(db, notification_id, partial_failure)

    observer = connect(schema)

    try:
        assert_counts(observer, "account-A", 2)
        assert_counts(observer, "account-B", 3)

        assert read_notification_status(
            observer, notification_id
        ) == "received"
    finally:
        observer.close()


def test_retry_after_partial_failure(environment):
    db, admin, schema = environment
    notification_id = prepare(db)

    with pytest.raises(DeletionProcessingError):
        process(db, notification_id, partial_failure)

    retry = connect(schema)

    try:
        result = process(
            retry, notification_id, erase_all
        )

        assert result.state == "completed"
        assert result.erased_records == 6
        assert result.acknowledged is False

        assert_counts(retry, "account-A", 0)
        assert_counts(retry, "account-B", 3)
    finally:
        retry.close()


def interrupt_transaction(db, admin, notification_id):
    backend_pid = db.get_backend_pid()

    def interrupted_handler(cur, event_id):
        deleted = delete_from_table(
            cur, TABLES[0], "account-A"
        )
        assert deleted == 2

        # Terminate only the disposable test worker.
        # Wait for PostgreSQL to confirm termination.
        with admin.cursor() as control:
            control.execute(
                "SELECT pg_terminate_backend(%s, %s)",
                (backend_pid, 5000),
            )
            assert control.fetchone()[0] is True

        # This operation must fail because the
        # original database connection is gone.
        cur.execute("SELECT 1")

        return deleted

    with pytest.raises(
        (DeletionProcessingError, psycopg2.Error)
    ):
        process(
            db,
            notification_id,
            interrupted_handler,
        )


def test_connection_loss_rolls_back_deletion(environment):
    db, admin, schema = environment
    notification_id = prepare(db)

    interrupt_transaction(
        db, admin, notification_id
    )

    observer = connect(schema)

    try:
        assert_counts(observer, "account-A", 2)
        assert_counts(observer, "account-B", 3)

        assert read_notification_status(
            observer, notification_id
        ) == "received"
    finally:
        observer.close()


def test_recovery_after_connection_loss(environment):
    db, admin, schema = environment
    notification_id = prepare(db)

    interrupt_transaction(
        db, admin, notification_id
    )

    recovery = connect(schema)

    try:
        assert_counts(recovery, "account-A", 2)

        assert read_notification_status(
            recovery, notification_id
        ) == "received"

        result = process(
            recovery,
            notification_id,
            erase_all,
        )

        assert result.state == "completed"
        assert result.erased_records == 6
        assert result.acknowledged is False

        assert_counts(recovery, "account-A", 0)
        assert_counts(recovery, "account-B", 3)

        assert read_notification_status(
            recovery, notification_id
        ) == "completed"
    finally:
        recovery.close()


def test_duplicate_multistore_notification(environment):
    db, admin, schema = environment
    notification_id = prepare(db)

    first = process(
        db, notification_id, erase_all
    )

    calls = []

    def duplicate_handler(cur, event_id):
        calls.append(event_id)
        return erase_all(cur, event_id)

    duplicate = connect(schema)

    try:
        second = process(
            duplicate,
            notification_id,
            duplicate_handler,
        )

        assert first.erased_records == 6
        assert second.erased_records == 0
        assert second.state == "completed"
        assert first.acknowledged is False
        assert second.acknowledged is False
        assert calls == []

        assert_counts(duplicate, "account-A", 0)
        assert_counts(duplicate, "account-B", 3)
    finally:
        duplicate.close()
