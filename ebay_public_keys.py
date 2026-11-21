"""eBay production OAuth + Notification API public-key lookup.

Isolated utility only: it does not enable webhook POSTs or delete records.
"""
import base64
import json
import os
import re
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

TOKEN_URL = 'https://api.ebay.com/identity/v1/oauth2/token'
KEY_BASE = 'https://api.ebay.com/commerce/notification/v1/public_key/'
SCOPE = 'https://api.ebay.com/oauth/api_scope'
KEY_ID = re.compile(r'^[A-Za-z0-9_-]{1,128}$')

class EbayKeyError(Exception):
    pass

class EbayPublicKeyClient:
    def __init__(self, client_id=None, client_secret=None, opener=None, clock=None):
        self.client_id = client_id if client_id is not None else os.getenv('EBAY_CLIENT_ID', '')
        self.client_secret = client_secret if client_secret is not None else os.getenv('EBAY_CLIENT_SECRET', '')
        self.opener = opener or urlopen
        self.clock = clock or time.monotonic
        self._lock = threading.RLock()
        self._token = None
        self._token_until = 0
        self._keys = {}

    def _request(self, request):
        try:
            with self.opener(request, timeout=8) as response:
                if response.status != 200:
                    raise EbayKeyError('unexpected eBay API status')
                raw = response.read(65537)
                if len(raw) > 65536:
                    raise EbayKeyError('oversized eBay API response')
                return json.loads(raw)
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            raise EbayKeyError('eBay API request failed') from exc

    def _access_token(self):
        now = self.clock()
        if self._token and now < self._token_until:
            return self._token
        if not self.client_id or not self.client_secret:
            raise EbayKeyError('EBAY_CLIENT_ID and EBAY_CLIENT_SECRET are required')
        basic = base64.b64encode(f'{self.client_id}:{self.client_secret}'.encode()).decode('ascii')
        body = urlencode({'grant_type': 'client_credentials', 'scope': SCOPE}).encode()
        request = Request(TOKEN_URL, data=body, method='POST', headers={
            'Authorization': f'Basic {basic}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
        })
        data = self._request(request)
        if not isinstance(data, dict) or not isinstance(data.get('access_token'), str) or not data['access_token']:
            raise EbayKeyError('OAuth response missing access_token')
        try:
            lifetime = int(data['expires_in'])
        except (KeyError, ValueError, TypeError) as exc:
            raise EbayKeyError('OAuth response missing valid expires_in') from exc
        if lifetime <= 0:
            raise EbayKeyError('OAuth token already expired')
        self._token = data['access_token']
        self._token_until = now + max(0, lifetime - 60)
        return self._token

    def get_public_key(self, key_id):
        """Return eBay's PEM public key, cached up to one hour.

        key_id must come from the *validated* decoded X-EBAY-SIGNATURE header.
        Caller must still verify the signature over the unmodified raw body.
        """
        if not isinstance(key_id, str) or not KEY_ID.fullmatch(key_id):
            raise EbayKeyError('invalid signing key ID')
        with self._lock:
            now = self.clock()
            cached = self._keys.get(key_id)
            if cached and now < cached[1]:
                return cached[0]
            request = Request(KEY_BASE + quote(key_id, safe=''), method='GET', headers={
                'Authorization': 'Bearer ' + self._access_token(),
                'Accept': 'application/json',
            })
            data = self._request(request)
            if not isinstance(data, dict) or not isinstance(data.get('key'), str):
                raise EbayKeyError('public key missing from eBay response')
            key = data['key']
            if len(key) > 16384 or '-----BEGIN PUBLIC KEY-----' not in key or '-----END PUBLIC KEY-----' not in key:
                raise EbayKeyError('invalid public key format')
            self._keys[key_id] = (key, now + 3600)
            return key
