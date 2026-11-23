
"""Phase 2R.4: Real PostgreSQL concurrency and recovery tests.

Disposable local PostgreSQL only. No Neon, eBay API, or actual erasure.
"""

import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import psycopg2
import pytest

from ebay_notification_ledger import (
    notification_fingerprint,
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
def setup_db():
    if os.getenv("EBAY_LOCAL_PG_TEST") != "1":
        pytest.skip("Disposable PostgreSQL tests disabled")

    conn = psycopg2.connect(TEST_DSN)
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
        conn.commit()
        yield conn
    finally:
        conn.rollback()
        conn.close()


def new_id():
    return "concurrency-" + uuid.uuid4().hex


def worker_connection():
    conn = psycopg2.connect(TEST_DSN)
    with conn.cursor() as cur:
        cur.execute("SET lock_timeout = '5s'")
    conn.commit()
    return conn


def wait_for_lock(observer, backend_pid, timeout=4):
    """Confirm that a worker is actually waiting on a PG lock."""
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        with observer.cursor() as cur:
            cur.execute(
                """
                SELECT wait_event_type
                FROM pg_stat_activity
                WHERE pid = %s
                """,
                (backend_pid,),
            )
            row = cur.fetchone()

        observer.rollback()

        if row and row[0] == "Lock":
            return

        time.sleep(0.02)

    pytest.fail("Second worker did not reach a PostgreSQL lock wait")


def run_worker(conn, notification_id, handler):
    return process_verified_deletion(
        conn,
        notification_id,
        handler,
        storage_inventory_approved=True,
    )


def test_concurrent_success_only_erases_once(setup_db):
    notification_id = new_id()
    record_verified_notification(setup_db, notification_id)

    first_conn = worker_connection()
    second_conn = worker_connection()
    first_entered = threading.Event()
    release_first = threading.Event()
    calls = []
    calls_lock = threading.Lock()

    def first_handler(cur, event_id):
        with calls_lock:
            calls.append("first")
        first_entered.set()
        if not release_first.wait(4):
            raise RuntimeError("First worker release timed out")
        return 2

    def second_handler(cur, event_id):
        with calls_lock:
            calls.append("second")
        return 2

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(
                run_worker,
                first_conn,
                notification_id,
                first_handler,
            )

            assert first_entered.wait(3)

            second_pid = second_conn.get_backend_pid()
            second = pool.submit(
                run_worker,
                second_conn,
                notification_id,
                second_handler,
            )

            try:
                wait_for_lock(setup_db, second_pid)
                assert not second.done()
            finally:
                release_first.set()

            first_result = first.result(timeout=6)
            second_result = second.result(timeout=6)

        assert first_result.state == "completed"
        assert first_result.erased_records == 2
        assert second_result.state == "completed"
        assert second_result.erased_records == 0
        assert first_result.acknowledged is False
        assert second_result.acknowledged is False
        assert calls == ["first"]
        assert read_notification_status(
            setup_db, notification_id
        ) == "completed"

    finally:
        release_first.set()
        first_conn.close()
        second_conn.close()


def test_failed_worker_allows_waiting_worker_to_retry(setup_db):
    notification_id = new_id()
    record_verified_notification(setup_db, notification_id)

    first_conn = worker_connection()
    second_conn = worker_connection()
    first_entered = threading.Event()
    release_first = threading.Event()
    calls = []
    calls_lock = threading.Lock()

    def failing_handler(cur, event_id):
        with calls_lock:
            calls.append("first")
        first_entered.set()
        if not release_first.wait(4):
            raise RuntimeError("First worker release timed out")
        raise RuntimeError("Simulated transactional failure")

    def recovery_handler(cur, event_id):
        with calls_lock:
            calls.append("recovery")
        return 1

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(
                run_worker,
                first_conn,
                notification_id,
                failing_handler,
            )

            assert first_entered.wait(3)

            second_pid = second_conn.get_backend_pid()
            second = pool.submit(
                run_worker,
                second_conn,
                notification_id,
                recovery_handler,
            )

            try:
                wait_for_lock(setup_db, second_pid)
                assert not second.done()
            finally:
                release_first.set()

            with pytest.raises(DeletionProcessingError):
                first.result(timeout=6)

            recovery = second.result(timeout=6)

        assert recovery.state == "completed"
        assert recovery.erased_records == 1
        assert recovery.acknowledged is False
        assert calls == ["first", "recovery"]
        assert read_notification_status(
            setup_db, notification_id
        ) == "completed"

    finally:
        release_first.set()
        first_conn.close()
        second_conn.close()


def test_completed_notification_cannot_repeat_erasure(setup_db):
    notification_id = new_id()
    record_verified_notification(setup_db, notification_id)

    calls = []

    def handler(cur, event_id):
        calls.append(event_id)
        return 1

    first = run_worker(setup_db, notification_id, handler)
    second = run_worker(setup_db, notification_id, handler)

    assert first.erased_records == 1
    assert second.erased_records == 0
    assert calls == [notification_id]
    assert first.acknowledged is False
    assert second.acknowledged is False


def test_rollback_preserves_original_status(setup_db):
    notification_id = new_id()
    record_verified_notification(setup_db, notification_id)

    def failing_handler(cur, event_id):
        raise RuntimeError("Simulated failure")

    with pytest.raises(DeletionProcessingError):
        run_worker(
            setup_db,
            notification_id,
            failing_handler,
        )

    assert read_notification_status(
        setup_db, notification_id
    ) == "received"


def test_notification_fingerprint_remains_stable(setup_db):
    notification_id = new_id()
    digest = notification_fingerprint(notification_id)

    record_verified_notification(setup_db, notification_id)

    with setup_db.cursor() as cur:
        cur.execute(
            """
            SELECT notification_fingerprint
            FROM public.ebay_notification_ledger
            WHERE notification_fingerprint = %s
            """,
            (digest,),
        )
        row = cur.fetchone()

    assert row == (digest,)
    assert len(digest) == 64
