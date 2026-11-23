
"""Phase 2Q.2: Offline HTTP and security tests for eBay webhook."""

import hashlib
import http.client
import json
import os
import threading
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.parse import quote

import pytest

import ebay_webhook
from ebay_public_keys import EbayKeyError
from ebay_signature import SignatureError


TOKEN = "TestVerificationToken_123456789012345"
ENDPOINT = "https://example.invalid/ebay/account-deletion"
PATH = "/ebay/account-deletion"


@contextmanager
def local_server():
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        ebay_webhook.Handler,
    )
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def request(port, method, path, body=None, headers=None):
    connection = http.client.HTTPConnection(
        "127.0.0.1", port, timeout=3
    )
    try:
        connection.request(
            method,
            path,
            body=body,
            headers=headers or {},
        )
        response = connection.getresponse()
        status = response.status
        data = json.loads(response.read())
        return status, data
    finally:
        connection.close()


@pytest.fixture
def port():
    with patch.dict(os.environ, {
        "EBAY_PHASE2D_AUTH_TEST": "0",
        "EBAY_VERIFICATION_TOKEN": TOKEN,
        "EBAY_NOTIFICATION_ENDPOINT": ENDPOINT,
    }):
        with local_server() as server_port:
            yield server_port


def test_health_reports_post_disabled(port):
    status, data = request(port, "GET", "/health")
    assert status == 200
    assert data["post_enabled"] is False


def test_unknown_get_path(port):
    status, data = request(port, "GET", "/unknown")
    assert status == 404
    assert data["error"] == "not_found"


@pytest.mark.parametrize("path", [
    PATH,
    PATH + "?challenge_code=",
])
def test_missing_challenge(port, path):
    status, data = request(port, "GET", path)
    assert status == 400
    assert data["error"] == "invalid_challenge"


def test_oversized_challenge(port):
    path = PATH + "?challenge_code=" + "A" * 2049
    status, data = request(port, "GET", path)
    assert status == 400
    assert data["error"] == "invalid_challenge"


def test_valid_challenge(port):
    challenge = "PHASE2Q_TEST"
    path = PATH + "?challenge_code=" + quote(challenge)
    status, data = request(port, "GET", path)

    expected = hashlib.sha256(
        (challenge + TOKEN + ENDPOINT).encode("utf-8")
    ).hexdigest()

    assert status == 200
    assert data["challengeResponse"] == expected


def test_missing_configuration(port):
    with patch.dict(os.environ, {
        "EBAY_VERIFICATION_TOKEN": "",
        "EBAY_NOTIFICATION_ENDPOINT": "",
    }):
        status, data = request(
            port, "GET", PATH + "?challenge_code=test"
        )
    assert status == 503
    assert data["error"] == "not_configured"


def test_invalid_token_configuration(port):
    with patch.dict(os.environ, {
        "EBAY_VERIFICATION_TOKEN": "short",
    }):
        status, data = request(
            port, "GET", PATH + "?challenge_code=test"
        )
    assert status == 503
    assert data["error"] == "invalid_configuration"


def test_unknown_post_path(port):
    status, data = request(
        port, "POST", "/unknown", body=b"{}"
    )
    assert status == 404
    assert data["error"] == "not_found"


def test_post_disabled_by_default(port):
    status, data = request(
        port, "POST", PATH, body=b"{}"
    )
    assert status == 503
    assert data["error"] == (
        "notification_processing_not_enabled"
    )


@pytest.mark.parametrize("content_length, expected", [
    ("abc", 400),
    ("0", 413),
    ("65537", 413),
])
def test_invalid_content_length(
    port, content_length, expected
):
    with patch.dict(os.environ, {
        "EBAY_PHASE2D_AUTH_TEST": "1",
    }):
        connection = http.client.HTTPConnection(
            "127.0.0.1", port, timeout=3
        )
        try:
            connection.putrequest("POST", PATH)
            connection.putheader(
                "Content-Length", content_length
            )
            connection.endheaders()
            response = connection.getresponse()
            status = response.status
            response.read()
        finally:
            connection.close()

    assert status == expected


def test_incomplete_body(port):
    with patch.dict(os.environ, {
        "EBAY_PHASE2D_AUTH_TEST": "1",
    }):
        connection = http.client.HTTPConnection(
            "127.0.0.1", port, timeout=3
        )
        try:
            connection.putrequest("POST", PATH)
            connection.putheader("Content-Length", "10")
            connection.endheaders()
            connection.send(b"{}")
            connection.sock.shutdown(1)
            response = connection.getresponse()
            status = response.status
            response.read()
        finally:
            connection.close()

    assert status == 400


def test_invalid_signature(port):
    with patch.dict(os.environ, {
        "EBAY_PHASE2D_AUTH_TEST": "1",
    }):
        with patch.object(
            ebay_webhook,
            "authenticate_notification",
            side_effect=SignatureError("invalid"),
        ):
            status, data = request(
                port, "POST", PATH, body=b"{}"
            )

    assert status == 401
    assert data["error"] == "invalid_notification"


def test_key_lookup_failure(port):
    with patch.dict(os.environ, {
        "EBAY_PHASE2D_AUTH_TEST": "1",
    }):
        with patch.object(
            ebay_webhook,
            "authenticate_notification",
            side_effect=EbayKeyError("unavailable"),
        ):
            status, data = request(
                port, "POST", PATH, body=b"{}"
            )

    assert status == 503
    assert data["error"] == "key_lookup_unavailable"


def test_verified_notification_never_acknowledged(port):
    with patch.dict(os.environ, {
        "EBAY_PHASE2D_AUTH_TEST": "1",
    }):
        with patch.object(
            ebay_webhook,
            "authenticate_notification",
            return_value={"verified": True},
        ):
            status, data = request(
                port, "POST", PATH, body=b"{}"
            )

    assert status == 503
    assert data["error"] == (
        "verified_but_processing_not_enabled"
    )


def test_post_never_returns_success(port):
    for mode in ("0", "1"):
        with patch.dict(os.environ, {
            "EBAY_PHASE2D_AUTH_TEST": mode,
        }):
            with patch.object(
                ebay_webhook,
                "authenticate_notification",
                return_value={"verified": True},
            ):
                status, _ = request(
                    port, "POST", PATH, body=b"{}"
                )
        assert status >= 400
