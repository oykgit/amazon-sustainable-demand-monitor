"""Phase-one eBay challenge endpoint. POST is deliberately not enabled.

Do NOT register this URL with eBay until a compliant POST handler has been
implemented and tested for signature validation and deletion processing.
"""
import hashlib
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

PATH = '/ebay/account-deletion'


def challenge_response(challenge, token, endpoint):
    if not challenge or not token or not endpoint:
        raise ValueError('missing challenge configuration')
    if not (32 <= len(token) <= 80) or any(not (c.isalnum() and c.isascii() or c in '_-') for c in token):
        raise ValueError('invalid verification token')
    return hashlib.sha256((challenge + token + endpoint).encode('utf-8')).hexdigest()


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
            return self.reply(200, {'status': 'ready_for_challenge_test_only', 'post_enabled': False})
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
        # Never acknowledge a deletion notification before its authenticity
        # and corresponding data-erasure obligations can be handled.
        return self.reply(503, {'error': 'notification_processing_not_enabled'})


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', int(os.getenv('PORT', '10000'))), Handler).serve_forever()
