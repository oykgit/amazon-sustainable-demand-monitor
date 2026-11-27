"""Loopback-only HTTP transaction bridge. Never imported by production webhook.
Dependencies must be injected by isolated tests; no environment-based activation.
"""
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit
from ebay_webhook import Handler, PATH, MAX_BODY
from ebay_phase2i import process_notification_offline
from ebay_signature import SignatureError
from ebay_public_keys import EbayKeyError


def make_staging_server(*, connection, erase, key_client, inventory_approved=False):
    if inventory_approved is not True or not callable(erase) or key_client is None:
        raise ValueError('explicit synthetic staging policy required')
    # The fixture connection is single-user. Serialize all handler work.
    import threading
    lock = threading.Lock()

    class StagingHandler(Handler):
        def do_POST(self):
            if urlsplit(self.path).path != PATH:
                return self.reply(404, {'error': 'not_found'})
            self.connection.settimeout(5)
            length = self.headers.get('Content-Length', '')
            if not length.isascii() or not length.isdecimal() or len(length) > 8:
                return self.reply(400, {'error': 'invalid_content_length'})
            if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length', [])) != 1:
                return self.reply(400, {'error': 'invalid_framing'})
            size = int(length)
            if not 0 < size <= MAX_BODY:
                return self.reply(413, {'error': 'invalid_body_size'})
            try:
                body = self.rfile.read(size)
            except OSError:
                return self.reply(400, {'error': 'incomplete_body'})
            if len(body) != size:
                return self.reply(400, {'error': 'incomplete_body'})
            try:
                with lock:
                    result = process_notification_offline(
                        self.headers.get('X-EBAY-SIGNATURE', ''), body,
                        connection, erase, storage_inventory_approved=True,
                        key_client=key_client)
            except (SignatureError, ValueError):
                return self.reply(412, {'error': 'invalid_notification'})
            except EbayKeyError:
                return self.reply(503, {'error': 'key_lookup_unavailable'})
            except Exception:
                return self.reply(503, {'error': 'transaction_not_confirmed'})
            if (not isinstance(result, dict) or result.get('state') != 'completed'
                    or result.get('http_acknowledgment_authorized') is not False):
                return self.reply(503, {'error': 'transaction_not_confirmed'})
            # This success belongs ONLY to a synthetic loopback client. Never eBay.
            return self.reply(200, {'mode': 'SYNTHETIC_STAGING_ONLY', 'state': 'completed',
                                    'production_acknowledgment_authorized': False})

    return ThreadingHTTPServer(('127.0.0.1', 0), StagingHandler)
