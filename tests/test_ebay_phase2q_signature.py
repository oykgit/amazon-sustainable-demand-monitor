
"""Phase 2Q.3: Offline ECDSA-SHA256 security tests.

Uses locally generated test keys only.
No eBay, Neon, Render, or external network requests.
"""

import base64
import json

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from ebay_signature import (
    SignatureError,
    decode_header,
    verify_notification,
)


TEST_KID = "phase2q-local-test-key"


def encode_envelope(envelope):
    return base64.b64encode(
        json.dumps(envelope).encode("utf-8")
    ).decode("ascii")


def make_header(signature, kid=TEST_KID):
    return encode_envelope({
        "alg": "ecdsa",
        "digest": "SHA256",
        "kid": kid,
        "signature": base64.b64encode(
            signature
        ).decode("ascii"),
    })


@pytest.fixture(scope="module")
def signing_key():
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture(scope="module")
def public_pem(signing_key):
    return signing_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


@pytest.fixture
def signed_message(signing_key):
    body = (
        b'{"metadata":{"topic":'
        b'"MARKETPLACE_ACCOUNT_DELETION"}}'
    )
    signature = signing_key.sign(
        body,
        ec.ECDSA(hashes.SHA256()),
    )
    return make_header(signature), body


def test_valid_ecdsa_signature(
    signed_message, public_pem
):
    header, body = signed_message

    assert verify_notification(
        header, body, public_pem
    ) == TEST_KID


def test_public_key_as_string(
    signed_message, public_pem
):
    header, body = signed_message

    assert verify_notification(
        header, body, public_pem.decode("ascii")
    ) == TEST_KID


def test_decode_valid_header(signed_message):
    header, _ = signed_message
    kid, signature = decode_header(header)

    assert kid == TEST_KID
    assert isinstance(signature, bytes)
    assert signature


@pytest.mark.parametrize("header", [
    None,
    "",
    123,
    "A" * 4097,
    "not-base64!",
    base64.b64encode(b"not-json").decode(),
    encode_envelope([]),
])
def test_invalid_header_rejected(header):
    with pytest.raises(SignatureError):
        decode_header(header)


@pytest.mark.parametrize("changes", [
    {"alg": "rsa"},
    {"digest": "SHA512"},
    {"kid": ""},
    {"kid": 123},
    {"kid": "K" * 257},
    {"signature": 123},
])
def test_invalid_envelope_fields(changes):
    envelope = {
        "alg": "ecdsa",
        "digest": "SHA256",
        "kid": TEST_KID,
        "signature": "AQID",
    }
    envelope.update(changes)

    with pytest.raises(SignatureError):
        decode_header(encode_envelope(envelope))


@pytest.mark.parametrize("signature", [
    "",
    "not-base64!",
    base64.b64encode(b"A" * 257).decode(),
])
def test_invalid_signature_encoding(signature):
    header = encode_envelope({
        "alg": "ecdsa",
        "digest": "SHA256",
        "kid": TEST_KID,
        "signature": signature,
    })

    with pytest.raises(SignatureError):
        decode_header(header)


@pytest.mark.parametrize("body", [
    None,
    "",
    b"",
    b"A" * 65537,
])
def test_invalid_payload(
    signed_message, public_pem, body
):
    header, _ = signed_message

    with pytest.raises(SignatureError):
        verify_notification(
            header, body, public_pem
        )


def test_modified_payload_rejected(
    signed_message, public_pem
):
    header, body = signed_message

    with pytest.raises(
        SignatureError,
        match="signature verification failed",
    ):
        verify_notification(
            header, body + b" ", public_pem
        )


def test_different_key_rejected(signed_message):
    header, body = signed_message

    other_key = ec.generate_private_key(
        ec.SECP256R1()
    )
    other_pem = other_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    with pytest.raises(SignatureError):
        verify_notification(
            header, body, other_pem
        )


@pytest.mark.parametrize("pem", [
    None,
    b"invalid-public-key",
    "invalid-public-key",
])
def test_invalid_public_key(
    signed_message, pem
):
    header, body = signed_message

    with pytest.raises(SignatureError):
        verify_notification(header, body, pem)


def test_rsa_public_key_rejected(signed_message):
    header, body = signed_message

    rsa_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    rsa_pem = rsa_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    with pytest.raises(
        SignatureError,
        match="unsupported public key type",
    ):
        verify_notification(
            header, body, rsa_pem
        )


def test_wrong_signature_rejected(
    signed_message, public_pem, signing_key
):
    _, body = signed_message

    wrong_signature = signing_key.sign(
        b"different message",
        ec.ECDSA(hashes.SHA256()),
    )

    with pytest.raises(SignatureError):
        verify_notification(
            make_header(wrong_signature),
            body,
            public_pem,
        )


def test_exact_raw_bytes_required(
    signing_key, public_pem
):
    original = b'{"a":1,"b":2}'
    reformatted = b'{ "a": 1, "b": 2 }'

    signature = signing_key.sign(
        original,
        ec.ECDSA(hashes.SHA256()),
    )
    header = make_header(signature)

    assert verify_notification(
        header, original, public_pem
    ) == TEST_KID

    with pytest.raises(SignatureError):
        verify_notification(
            header, reformatted, public_pem
        )


def test_no_automatic_processing_authorization(
    signed_message, public_pem
):
    header, body = signed_message

    result = verify_notification(
        header, body, public_pem
    )

    # Verification returns only the key identifier.
    # It does not authorize notification processing.
    assert result == TEST_KID
    assert isinstance(result, str)
