"""eBay account-deletion webhook, phase 2 staging (fail closed).

GET challenge remains operational. POST refuses to acknowledge until the
production signing-key integration and data-erasure inventory are approved.
"""
import base64
import hashlib
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

PATH = '/ebay/account-deletion'
MAX_BODY = 65536


def challenge_response(challenge, token, endpoint):
    if not challenge or not token or not endpoint:
        raise ValueError('missing challenge configuration')
    if not (32 <= len(token) <= 80) or any(not (c.isascii() and c.isalnum() or c in '_-') for c in token):
        raise ValueError('invalid verification token')
    return hashlib.sha256((challenge + token + endpoint).encode('utf-8')).hexdigest()


def parse_notification(body):
    """Validate structural shape only. NEVER interpret this as authentication."""
    if not isinstance(body, bytes) or not body or len(body) > MAX_BODY:
        raise ValueError('invalid body size')
    try:
        obj = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('invalid json') from exc
    if not isinstance(obj, dict):
        raise ValueError('invalid root')
    meta = obj.get('metadata')
    note = obj.get('notification')
    if not isinstance(meta, dict) or meta.get('topic') != 'MARKETPLACE_ACCOUNT_DELETION':
        raise ValueError('invalid topic')
    if not isinstance(note, dict) or not isinstance(note.get('notificationId'), str) or not note['notificationId']:
        raise ValueError('invalid notification id')
    data = note.get('data')
    if not isinstance(data, dict) or not any(isinstance(data.get(k), str) and data[k] for k in ('userId','username','eiasToken')):
        raise ValueError('missing user identifier')
    return obj


def decode_signature_envelope(header):
    """Parse the base64 JSON envelope. This is NOT signature verification."""
    if not isinstance(header, str) or len(header) > 4096:
        raise ValueError('invalid signature header')
    try:
        envelope = json.loads(base64.b64decode(header, validate=True))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('malformed signature header') from exc
    if not isinstance(envelope, dict) or not isinstance(envelope.get('kid'), str) or not envelope['kid']:
        raise ValueError('missing signing key id')
    if not isinstance(envelope.get('signature'), str) or not envelope['signature']:
        raise ValueError('missing signature')
    return envelope


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, payload):
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
            return self.reply(200, {'status': 'phase2_staging', 'post_enabled': False})
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
        # IMPORTANT: Do not acknowledge any notification before authentication,
        # durable receipt and a verified erasure process are implemented.
        # Do not log or persist the raw request: it may contain personal data.
        return self.reply(503, {'error': 'production_notification_processing_not_enabled'})


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', int(os.getenv('PORT', '10000'))), Handler).serve_forever()
