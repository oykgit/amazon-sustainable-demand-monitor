"""eBay account deletion webhook: Phase 2D, authentication integrated, fail closed.

GET challenge supported. POST can validate authentic eBay signatures but always
returns 503 until durable processing and erasure safeguards are implemented.
Never logs raw notifications or personal identifiers.
"""
import json
import base64
import binascii
import os
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from ebay_signature import SignatureError, decode_header, verify_notification
from ebay_public_keys import EbayKeyError, EbayPublicKeyClient

PATH = '/ebay/account-deletion'
MAX_BODY = 65536
KEY_CLIENT = EbayPublicKeyClient()
LOGGER = logging.getLogger("ebay_webhook")


def challenge_response(challenge, token, endpoint):
    import hashlib
    if not challenge or not token or not endpoint:
        raise ValueError('missing challenge configuration')
    if not (32 <= len(token) <= 80) or any(not (c.isascii() and (c.isalnum() or c in '_-')) for c in token):
        raise ValueError('invalid verification token')
    return hashlib.sha256((challenge + token + endpoint).encode('utf-8')).hexdigest()


def parse_notification(body):
    if not isinstance(body, bytes) or not body or len(body) > MAX_BODY:
        raise ValueError('invalid body size')
    try:
        obj = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('invalid json') from exc
    if not isinstance(obj, dict):
        raise ValueError('invalid root')
    meta, note = obj.get('metadata'), obj.get('notification')
    if not isinstance(meta, dict) or meta.get('topic') != 'MARKETPLACE_ACCOUNT_DELETION':
        raise ValueError('invalid topic')
    if not isinstance(note, dict) or not isinstance(note.get('notificationId'), str) or not note['notificationId']:
        raise ValueError('invalid notification id')
    data = note.get('data')
    if not isinstance(data, dict) or not any(isinstance(data.get(k), str) and data[k] for k in ('userId', 'username', 'eiasToken')):
        raise ValueError('missing user identifier')
    return obj


def decode_signature_envelope(header):
    """Legacy structural parser for Phase 2 staging tests; NOT authentication."""
    if not isinstance(header, str) or not header or len(header) > 4096:
        raise ValueError('invalid signature header')
    try:
        obj = json.loads(base64.b64decode(header, validate=True))
    except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
        raise ValueError('malformed signature header') from exc
    if not isinstance(obj, dict) or not isinstance(obj.get('kid'), str) or not obj['kid'] or not isinstance(obj.get('signature'), str) or not obj['signature']:
        raise ValueError('invalid signature envelope')
    return obj


def authenticate_notification(signature_header, raw_body, key_client=None):
    """Validate signature using a trusted eBay key; returns parsed event.

    Does NOT authorize acknowledgement, deletion, or database writes.
    """
    kid, _ = decode_header(signature_header)
    trusted_pem = (key_client or KEY_CLIENT).get_public_key(kid)
    verified_kid = verify_notification(signature_header, raw_body, trusted_pem)
    if verified_kid != kid:
        raise SignatureError('signing key mismatch')
    return parse_notification(raw_body)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # BaseHTTPRequestHandler includes raw request paths and error text.
        # Never log untrusted URLs, headers, bodies or identifiers.
        return

    def reply(self, code, payload):
        route = urlsplit(self.path).path
        if self.command == "POST" and route == PATH:
            LOGGER.warning("ebay_notification_http_status=%d outcome=%s", code,
                           payload.get("error", "unspecified"))
        data = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path == '/health':
            return self.reply(200, {'status': 'phase2d_authentication_integrated', 'post_enabled': False,
                                    'signature_diagnostic_enabled': os.getenv('EBAY_PHASE2D_AUTH_TEST', '') == '1',
                                    'oauth_credentials_configured': bool(os.getenv('EBAY_CLIENT_ID') and os.getenv('EBAY_CLIENT_SECRET'))})
        if parsed.path != PATH:
            return self.reply(404, {'error': 'not_found'})
        challenge = parse_qs(parsed.query).get('challenge_code', [''])[0]
        if not challenge or len(challenge) > 2048:
            return self.reply(400, {'error': 'invalid_challenge'})
        token = os.getenv('EBAY_VERIFICATION_TOKEN', '')
        endpoint = os.getenv('EBAY_NOTIFICATION_ENDPOINT', '')
        if not token or not endpoint:
            return self.reply(503, {'error': 'not_configured'})
        try:
            digest = challenge_response(challenge, token, endpoint)
        except ValueError:
            return self.reply(503, {'error': 'invalid_configuration'})
        return self.reply(200, {'challengeResponse': digest})

    def do_POST(self):
        if urlsplit(self.path).path != PATH:
            return self.reply(404, {'error': 'not_found'})
        # Default disabled: do not accept or acknowledge live notifications.
        if os.getenv('EBAY_PHASE2D_AUTH_TEST', '') != '1':
            return self.reply(503, {'error': 'notification_processing_not_enabled'})
        # Diagnostic mode only; no storage and never a 2xx acknowledgement.
        try:
            length_text = self.headers.get('Content-Length', '')
            if not length_text.isdecimal():
                return self.reply(400, {'error': 'invalid_content_length'})
            length = int(length_text)
            if length < 1 or length > MAX_BODY:
                return self.reply(413, {'error': 'invalid_body_size'})
            body = self.rfile.read(length)
            if len(body) != length:
                return self.reply(400, {'error': 'incomplete_body'})
            authenticate_notification(self.headers.get('X-EBAY-SIGNATURE', ''), body)
        except (SignatureError, ValueError):
            return self.reply(401, {'error': 'invalid_notification'})
        except EbayKeyError:
            return self.reply(503, {'error': 'key_lookup_unavailable'})
        # Never acknowledge until Phase 2E has durable receipt + erasure.
        return self.reply(503, {'error': 'verified_but_processing_not_enabled'})


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', int(os.getenv('PORT', '10000'))), Handler).serve_forever()
