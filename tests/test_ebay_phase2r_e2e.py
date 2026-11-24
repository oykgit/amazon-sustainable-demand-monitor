
"""Phase 2R.7: Offline authenticated notification integration.

Real ECDSA signatures and disposable PostgreSQL transactions.
Synthetic identities and locally generated signing keys only.

No live eBay requests, production database access,
HTTP acknowledgments or real customer erasure.
"""

import base64
import json
import os
import uuid

import psycopg2
import pytest

from cryptography.hazmat.primitives import (
    hashes,
    serialization,
)
from cryptography.hazmat.primitives.asymmetric import ec

from ebay_signature import SignatureError
from ebay_phase2h import DeletionProcessingError
from ebay_phase2i import (
    Phase2IError,
    process_notification_offline,
)
from ebay_notification_ledger import (
    read_notification_status,
)


TEST_DSN = (
    "host=127.0.0.1 port=5432 "
    "dbname=ebay_phase2r_test "
    "user=ebay_test password=local_test_only "
    "connect_timeout=5"
)

KEY_ID = "offline-phase2r7-test-key"

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
CREATE TEMP TABLE phase2r7_synthetic_records (
    record_id integer GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    synthetic_account text NOT NULL,
    content text NOT NULL
) ON COMMIT PRESERVE ROWS;
"""


class LocalKeyClient:
    """Test-only trusted key provider. Never accesses network."""

    def __init__(self, public_key_pem):
        self.public_key_pem = public_key_pem
        self.requests = []

    def get_public_key(self, kid):
        self.requests.append(kid)

        if kid != KEY_ID:
            raise SignatureError("Unknown synthetic signing key")

        return self.public_key_pem


@pytest.fixture
def signing():
    private_key = ec.generate_private_key(
        ec.SECP256R1()
    )

    public_key_pem = (
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

    return private_key, LocalKeyClient(public_key_pem)


@pytest.fixture
def db():
    if os.getenv("EBAY_LOCAL_PG_TEST") != "1":
        pytest.skip("Disposable PostgreSQL tests disabled")

    conn = psycopg2.connect(TEST_DSN)

    try:
        with conn.cursor() as cur:
            cur.execute(LEDGER_SCHEMA)
            cur.execute(TEMP_SCHEMA)
            cur.execute("SET statement_timeout = '10s'")

        conn.commit()

        yield conn

    finally:
        conn.rollback()
        conn.close()


def new_notification_id():
    return "phase2r7-" + uuid.uuid4().hex


def make_body(
    notification_id,
    account="synthetic-account-A",
    topic="MARKETPLACE_ACCOUNT_DELETION",
):
    data = {}

    if account is not None:
        data["userId"] = account

    event = {
        "metadata": {
            "topic": topic,
        },
        "notification": {
            "notificationId": notification_id,
            "data": data,
        },
    }

    return json.dumps(
        event,
        separators=(",", ":"),
    ).encode("utf-8")


def sign_body(private_key, body):
    signature = private_key.sign(
        body,
        ec.ECDSA(hashes.SHA256()),
    )

    envelope = {
        "alg": "ecdsa",
        "digest": "SHA256",
        "kid": KEY_ID,
        "signature": base64.b64encode(
            signature
        ).decode("ascii"),
    }

    return base64.b64encode(
        json.dumps(envelope).encode("utf-8")
    ).decode("ascii")


def seed(db, account, count):
    with db.cursor() as cur:
        for index in range(count):
            cur.execute(
                """
                INSERT INTO phase2r7_synthetic_records
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
            FROM phase2r7_synthetic_records
            WHERE synthetic_account = %s
            """,
            (account,),
        )

        return cur.fetchone()[0]


def ledger_count(db):
    with db.cursor() as cur:
        cur.execute(
            "SELECT count(*) "
            "FROM public.ebay_notification_ledger"
        )

        return cur.fetchone()[0]


def erase_authenticated_account(cur, event):
    account = event["notification"]["data"]["userId"]

    if not account.startswith("synthetic-account-"):
        raise RuntimeError("Non-synthetic identity rejected")

    cur.execute(
        """
        DELETE FROM phase2r7_synthetic_records
        WHERE synthetic_account = %s
        RETURNING record_id
        """,
        (account,),
    )

    return len(cur.fetchall())


def process(
    db,
    header,
    body,
    key_client,
    handler=erase_authenticated_account,
    approved=True,
):
    return process_notification_offline(
        header,
        body,
        db,
        handler,
        storage_inventory_approved=approved,
        key_client=key_client,
    )


def assert_no_processing(
    db,
    notification_id,
    original_ledger_count,
):
    assert read_notification_status(
        db, notification_id
    ) is None

    assert ledger_count(db) == original_ledger_count

    assert count_records(
        db, "synthetic-account-A"
    ) == 3


def test_valid_signed_notification_erases_records(db, signing):
    private_key, key_client = signing
    notification_id = new_notification_id()

    seed(db, "synthetic-account-A", 3)
    seed(db, "synthetic-account-B", 4)

    body = make_body(notification_id)
    header = sign_body(private_key, body)

    result = process(
        db, header, body, key_client
    )

    assert result["state"] == "completed"
    assert result["erased_records"] == 3
    assert result["http_acknowledgment_authorized"] is False

    assert key_client.requests == [KEY_ID]

    assert count_records(
        db, "synthetic-account-A"
    ) == 0

    assert count_records(
        db, "synthetic-account-B"
    ) == 4

    assert read_notification_status(
        db, notification_id
    ) == "completed"


def test_invalid_signature_prevents_database_writes(db, signing):
    private_key, key_client = signing
    notification_id = new_notification_id()

    seed(db, "synthetic-account-A", 3)
    before = ledger_count(db)

    body = make_body(notification_id)

    wrong_key = ec.generate_private_key(
        ec.SECP256R1()
    )

    header = sign_body(wrong_key, body)

    with pytest.raises(SignatureError):
        process(db, header, body, key_client)

    assert_no_processing(
        db, notification_id, before
    )


def test_tampered_body_prevents_database_writes(db, signing):
    private_key, key_client = signing
    notification_id = new_notification_id()

    seed(db, "synthetic-account-A", 3)
    seed(db, "synthetic-account-B", 2)

    before = ledger_count(db)

    original = make_body(notification_id)
    header = sign_body(private_key, original)

    tampered = make_body(
        notification_id,
        account="synthetic-account-B",
    )

    with pytest.raises(SignatureError):
        process(
            db, header, tampered, key_client
        )

    assert_no_processing(
        db, notification_id, before
    )

    assert count_records(
        db, "synthetic-account-B"
    ) == 2


def test_missing_identity_prevents_database_writes(db, signing):
    private_key, key_client = signing
    notification_id = new_notification_id()

    seed(db, "synthetic-account-A", 3)
    before = ledger_count(db)

    body = make_body(
        notification_id,
        account=None,
    )

    header = sign_body(private_key, body)

    with pytest.raises(ValueError):
        process(db, header, body, key_client)

    assert_no_processing(
        db, notification_id, before
    )


def test_wrong_topic_prevents_database_writes(db, signing):
    private_key, key_client = signing
    notification_id = new_notification_id()

    seed(db, "synthetic-account-A", 3)
    before = ledger_count(db)

    body = make_body(
        notification_id,
        topic="UNSUPPORTED_SYNTHETIC_TOPIC",
    )

    header = sign_body(private_key, body)

    with pytest.raises(ValueError):
        process(db, header, body, key_client)

    assert_no_processing(
        db, notification_id, before
    )


def test_duplicate_authenticated_notification(db, signing):
    private_key, key_client = signing
    notification_id = new_notification_id()

    seed(db, "synthetic-account-A", 3)

    body = make_body(notification_id)
    header = sign_body(private_key, body)

    calls = []

    def handler(cur, event):
        calls.append(
            event["notification"]["notificationId"]
        )

        return erase_authenticated_account(
            cur, event
        )

    first = process(
        db, header, body, key_client, handler
    )

    second = process(
        db, header, body, key_client, handler
    )

    assert first["erased_records"] == 3
    assert second["erased_records"] == 0
    assert second["state"] == "completed"

    assert first["http_acknowledgment_authorized"] is False
    assert second["http_acknowledgment_authorized"] is False

    assert calls == [notification_id]


def test_authenticated_erasure_failure_rolls_back(db, signing):
    private_key, key_client = signing
    notification_id = new_notification_id()

    seed(db, "synthetic-account-A", 3)

    body = make_body(notification_id)
    header = sign_body(private_key, body)

    def failing_handler(cur, event):
        erased = erase_authenticated_account(
            cur, event
        )

        assert erased == 3

        raise RuntimeError(
            "Simulated failure after deletion"
        )

    with pytest.raises(DeletionProcessingError):
        process(
            db,
            header,
            body,
            key_client,
            failing_handler,
        )

    assert count_records(
        db, "synthetic-account-A"
    ) == 3

    assert read_notification_status(
        db, notification_id
    ) == "received"


def test_authenticated_retry_after_failure(db, signing):
    private_key, key_client = signing
    notification_id = new_notification_id()

    seed(db, "synthetic-account-A", 3)
    seed(db, "synthetic-account-B", 2)

    body = make_body(notification_id)
    header = sign_body(private_key, body)

    def failing_handler(cur, event):
        erase_authenticated_account(cur, event)
        raise RuntimeError("Simulated failure")

    with pytest.raises(DeletionProcessingError):
        process(
            db,
            header,
            body,
            key_client,
            failing_handler,
        )

    result = process(
        db, header, body, key_client
    )

    assert result["state"] == "completed"
    assert result["erased_records"] == 3
    assert result["http_acknowledgment_authorized"] is False

    assert count_records(
        db, "synthetic-account-A"
    ) == 0

    assert count_records(
        db, "synthetic-account-B"
    ) == 2

    assert read_notification_status(
        db, notification_id
    ) == "completed"


def test_unapproved_inventory_blocks_processing(db, signing):
    private_key, key_client = signing
    notification_id = new_notification_id()

    seed(db, "synthetic-account-A", 3)
    before = ledger_count(db)

    body = make_body(notification_id)
    header = sign_body(private_key, body)

    with pytest.raises(Phase2IError):
        process(
            db,
            header,
            body,
            key_client,
            approved=False,
        )

    assert key_client.requests == []

    assert_no_processing(
        db, notification_id, before
    )


def test_valid_notification_with_no_matching_records(db, signing):
    private_key, key_client = signing
    notification_id = new_notification_id()

    seed(db, "synthetic-account-B", 4)

    body = make_body(notification_id)
    header = sign_body(private_key, body)

    result = process(
        db, header, body, key_client
    )

    assert result["state"] == "completed"
    assert result["erased_records"] == 0
    assert result["http_acknowledgment_authorized"] is False

    assert count_records(
        db, "synthetic-account-B"
    ) == 4

    assert read_notification_status(
        db, notification_id
    ) == "completed"
