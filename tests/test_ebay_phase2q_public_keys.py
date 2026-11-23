
"""Phase 2Q.6: Offline eBay public-key retrieval security tests.

All HTTP responses are simulated locally.
No live eBay calls, database access, or production changes.
"""

import json
from unittest.mock import Mock

import pytest
from urllib.error import URLError

from ebay_public_keys import (
    EbayKeyError,
    EbayPublicKeyClient,
    KEY_BASE,
    TOKEN_URL,
)


TEST_KEY = (
    "-----BEGIN PUBLIC KEY-----\n"
    "TEST_PUBLIC_KEY_DATA\n"
    "-----END PUBLIC KEY-----"
)


class FakeResponse:
    def __init__(self, data, status=200):
        self.status = status
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit=-1):
        return self.data[:limit]


def make_client(opener=None, clock=None):
    return EbayPublicKeyClient(
        client_id="offline-test-client",
        client_secret="offline-test-secret",
        opener=opener,
        clock=clock or (lambda: 1000),
    )


def json_response(data, status=200):
    return FakeResponse(
        json.dumps(data).encode("utf-8"),
        status=status,
    )


def test_valid_oauth_token():
    calls = []

    def opener(request, timeout):
        calls.append(request)
        return json_response({
            "access_token": "offline-token",
            "expires_in": 3600,
        })

    client = make_client(opener=opener)

    assert client._access_token() == "offline-token"
    assert len(calls) == 1
    assert calls[0].full_url == TOKEN_URL
    assert calls[0].get_method() == "POST"


def test_oauth_token_cached():
    opener = Mock(return_value=json_response({
        "access_token": "cached-token",
        "expires_in": 3600,
    }))

    client = make_client(opener=opener)

    assert client._access_token() == "cached-token"
    assert client._access_token() == "cached-token"

    assert opener.call_count == 1


def test_missing_credentials_rejected():
    client = EbayPublicKeyClient(
        client_id="",
        client_secret="",
        opener=Mock(
            side_effect=AssertionError(
                "Network must not be called"
            )
        ),
    )

    with pytest.raises(
        EbayKeyError,
        match="required",
    ):
        client._access_token()


@pytest.mark.parametrize("response", [
    {},
    [],
    {"access_token": ""},
    {"access_token": 123},
    {"expires_in": 3600},
])
def test_invalid_oauth_token_response(response):
    client = make_client(
        opener=lambda request, timeout: json_response(
            response
        )
    )

    with pytest.raises(EbayKeyError):
        client._access_token()


@pytest.mark.parametrize("expires_in", [
    None,
    "invalid",
    0,
    -1,
])
def test_invalid_oauth_expiry(expires_in):
    response = {
        "access_token": "test-token",
        "expires_in": expires_in,
    }

    client = make_client(
        opener=lambda request, timeout: json_response(
            response
        )
    )

    with pytest.raises(EbayKeyError):
        client._access_token()


def test_missing_expiry_rejected():
    client = make_client(
        opener=lambda request, timeout: json_response({
            "access_token": "test-token"
        })
    )

    with pytest.raises(EbayKeyError):
        client._access_token()


def test_unexpected_http_status():
    client = make_client(
        opener=lambda request, timeout: json_response(
            {"error": "test"},
            status=503,
        )
    )

    with pytest.raises(
        EbayKeyError,
        match="unexpected eBay API status",
    ):
        client._access_token()


def test_oversized_api_response():
    client = make_client(
        opener=lambda request, timeout: FakeResponse(
            b"A" * 65537
        )
    )

    with pytest.raises(
        EbayKeyError,
        match="oversized eBay API response",
    ):
        client._access_token()


@pytest.mark.parametrize("exception", [
    URLError("offline network failure"),
    TimeoutError("offline timeout"),
    OSError("offline connection failure"),
])
def test_network_errors_fail_closed(exception):
    client = make_client(
        opener=Mock(side_effect=exception)
    )

    with pytest.raises(
        EbayKeyError,
        match="eBay API request failed",
    ):
        client._access_token()


def test_malformed_json_rejected():
    client = make_client(
        opener=lambda request, timeout: FakeResponse(
            b"{invalid-json"
        )
    )

    with pytest.raises(EbayKeyError):
        client._access_token()


@pytest.mark.parametrize("key_id", [
    None,
    "",
    123,
    "invalid/key",
    "../secret",
    "key with spaces",
    "A" * 129,
])
def test_invalid_key_ids_rejected(key_id):
    client = make_client(
        opener=Mock(
            side_effect=AssertionError(
                "Network must not be called"
            )
        )
    )

    with pytest.raises(
        EbayKeyError,
        match="invalid signing key ID",
    ):
        client.get_public_key(key_id)


def test_valid_public_key_lookup():
    calls = []

    def opener(request, timeout):
        calls.append(request.full_url)

        if request.full_url == TOKEN_URL:
            return json_response({
                "access_token": "test-token",
                "expires_in": 3600,
            })

        if request.full_url == KEY_BASE + "test-key":
            return json_response({"key": TEST_KEY})

        raise AssertionError("Unexpected URL")

    client = make_client(opener=opener)

    assert client.get_public_key("test-key") == TEST_KEY
    assert calls == [
        TOKEN_URL,
        KEY_BASE + "test-key",
    ]


def test_public_key_cached():
    calls = []

    def opener(request, timeout):
        calls.append(request.full_url)

        if request.full_url == TOKEN_URL:
            return json_response({
                "access_token": "test-token",
                "expires_in": 3600,
            })

        return json_response({"key": TEST_KEY})

    client = make_client(opener=opener)

    assert client.get_public_key("key-1") == TEST_KEY
    assert client.get_public_key("key-1") == TEST_KEY

    assert len(calls) == 2


def test_public_key_cache_expiry():
    current_time = [1000]
    key_requests = []

    def clock():
        return current_time[0]

    def opener(request, timeout):
        if request.full_url == TOKEN_URL:
            return json_response({
                "access_token": "test-token",
                "expires_in": 7200,
            })

        key_requests.append(request.full_url)
        return json_response({"key": TEST_KEY})

    client = make_client(
        opener=opener,
        clock=clock,
    )

    client.get_public_key("key-1")

    current_time[0] = 2000
    client.get_public_key("key-1")

    current_time[0] = 4601
    client.get_public_key("key-1")

    assert len(key_requests) == 2


@pytest.mark.parametrize("response", [
    {},
    [],
    {"key": None},
    {"key": 123},
    {"key": ""},
    {"key": "invalid-key"},
    {"key": "-----BEGIN PUBLIC KEY-----"},
    {"key": "-----END PUBLIC KEY-----"},
    {"key": "A" * 16385},
])
def test_invalid_public_key_responses(response):
    def opener(request, timeout):
        if request.full_url == TOKEN_URL:
            return json_response({
                "access_token": "test-token",
                "expires_in": 3600,
            })

        return json_response(response)

    client = make_client(opener=opener)

    with pytest.raises(EbayKeyError):
        client.get_public_key("test-key")


def test_failed_key_lookup_not_cached():
    key_calls = [0]

    def opener(request, timeout):
        if request.full_url == TOKEN_URL:
            return json_response({
                "access_token": "test-token",
                "expires_in": 3600,
            })

        key_calls[0] += 1

        if key_calls[0] == 1:
            return json_response({"key": "invalid"})

        return json_response({"key": TEST_KEY})

    client = make_client(opener=opener)

    with pytest.raises(EbayKeyError):
        client.get_public_key("test-key")

    assert client.get_public_key("test-key") == TEST_KEY
    assert key_calls[0] == 2


def test_different_key_ids_cached_separately():
    calls = []

    def opener(request, timeout):
        calls.append(request.full_url)

        if request.full_url == TOKEN_URL:
            return json_response({
                "access_token": "test-token",
                "expires_in": 3600,
            })

        return json_response({"key": TEST_KEY})

    client = make_client(opener=opener)

    client.get_public_key("key-one")
    client.get_public_key("key-two")
    client.get_public_key("key-one")

    key_calls = [
        url for url in calls
        if url.startswith(KEY_BASE)
    ]

    assert len(key_calls) == 2
