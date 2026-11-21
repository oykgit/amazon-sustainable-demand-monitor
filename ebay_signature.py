"""Offline cryptographic verification for eBay JSON event notifications.

This module does NOT fetch eBay signing keys, accept HTTP requests, or authorize
notification processing. Supply only a trusted PEM public key retrieved through
eBay's authenticated getPublicKey API.
"""
import base64
import binascii
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


class SignatureError(ValueError):
    """Invalid signature envelope, key, or cryptographic signature."""


def decode_header(header):
    if not isinstance(header, str) or not header or len(header) > 4096:
        raise SignatureError('invalid signature header')
    try:
        raw = base64.b64decode(header, validate=True)
        envelope = json.loads(raw.decode('utf-8'))
    except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
        raise SignatureError('malformed signature envelope') from exc
    if not isinstance(envelope, dict):
        raise SignatureError('invalid signature envelope')
    if envelope.get('alg') != 'ecdsa' or envelope.get('digest') != 'SHA256':
        raise SignatureError('unsupported signature algorithm')
    kid = envelope.get('kid')
    sig = envelope.get('signature')
    if not isinstance(kid, str) or not kid or len(kid) > 256 or not isinstance(sig, str):
        raise SignatureError('invalid key identifier or signature')
    try:
        signature = base64.b64decode(sig, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise SignatureError('invalid signature encoding') from exc
    if not signature or len(signature) > 256:
        raise SignatureError('invalid signature length')
    return kid, signature


def verify_notification(header, raw_body, trusted_public_key_pem):
    """Verify ECDSA-SHA256 over exact raw bytes. Return signing key ID on success.

    Does not establish key trust; caller MUST authenticate key retrieval from eBay.
    """
    kid, signature = decode_header(header)
    if not isinstance(raw_body, bytes) or not raw_body or len(raw_body) > 65536:
        raise SignatureError('invalid payload')
    try:
        key = serialization.load_pem_public_key(trusted_public_key_pem.encode('ascii') if isinstance(trusted_public_key_pem, str) else trusted_public_key_pem)
    except (ValueError, TypeError) as exc:
        raise SignatureError('invalid public key') from exc
    if not isinstance(key, ec.EllipticCurvePublicKey):
        raise SignatureError('unsupported public key type')
    try:
        key.verify(signature, raw_body, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature as exc:
        raise SignatureError('signature verification failed') from exc
    return kid
