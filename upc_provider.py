"""V1.21 UPCitemdb free-trial one-request, read-only catalogue preview.

No retries, no storage, no Amazon claims. Session cooldown is UI-managed.
"""
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from general_catalogue import normalize_gtin

HOST = 'api.upcitemdb.com'
BASE = f'https://{HOST}/prod/trial/lookup'
MAX_BYTES = 256_000

class ProviderFailure(ValueError):
    def __init__(self, code, message, retry_after=None):
        super().__init__(message)
        self.code = code
        self.retry_after = retry_after

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProviderFailure('REDIRECT_BLOCKED', 'Provider redirected outside the fixed API endpoint')

def lookup(barcode, *, fetcher=None):
    code = normalize_gtin(barcode)
    url = BASE + '?' + urllib.parse.urlencode({'upc': code})
    if fetcher is None:
        req = urllib.request.Request(url, headers={
            'Accept': 'application/json',
            'User-Agent': 'AmazonSustainableDemandMonitor/1.21 (read-only barcode research; https://github.com/oykgit/amazon-sustainable-demand-monitor)',
        })
        try:
            with urllib.request.build_opener(NoRedirect()).open(req, timeout=12) as response:
                raw = response.read(MAX_BYTES + 1)
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                raise ProviderFailure('RATE_LIMITED', 'UPCitemdb returned HTTP 429. Stop requests until the provider limit resets.', exc.headers.get('Retry-After')) from exc
            if exc.code == 403:
                raise ProviderFailure('ACCESS_DENIED', 'UPCitemdb returned HTTP 403. Do not bypass provider restrictions.') from exc
            raise ProviderFailure('HTTP_ERROR', f'UPCitemdb returned HTTP {exc.code}') from exc
        except urllib.error.URLError as exc:
            raise ProviderFailure('NETWORK_ERROR', 'UPCitemdb connection failed') from exc
        except TimeoutError as exc:
            raise ProviderFailure('TIMEOUT', 'UPCitemdb request timed out') from exc
    else:
        raw = fetcher(url)
    if isinstance(raw, str):
        raw = raw.encode('utf-8')
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise ProviderFailure('INVALID_RESPONSE', 'Provider response is invalid or too large')
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderFailure('INVALID_JSON', 'Provider did not return valid JSON') from exc
    if not isinstance(data, dict) or not isinstance(data.get('items', []), list):
        raise ProviderFailure('INVALID_SCHEMA', 'Provider returned an unexpected response structure')
    api_code = str(data.get('code', '')).upper()
    if api_code not in ('OK', 'NOT_FOUND'):
        raise ProviderFailure('PROVIDER_REJECTED', 'Provider did not accept the lookup')
    item = data['items'][0] if api_code == 'OK' and data['items'] else None
    if item is not None and not isinstance(item, dict):
        raise ProviderFailure('INVALID_SCHEMA', 'Provider product record is malformed')
    item = item or {}
    def field(name):
        value = item.get(name)
        return value[:300] if isinstance(value, str) else ''
    return {
        'mode': 'UPCITEMDB_SINGLE_LOOKUP_READ_ONLY',
        'status': 'CATALOGUE_METADATA_FOUND' if item else 'PRODUCT_NOT_FOUND',
        'provider': 'UPCitemdb free trial', 'barcode': code,
        'title': field('title'), 'brand': field('brand'), 'category': field('category'),
        'source_url': url, 'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
        'network_requests': 1, 'database_writes': 0, 'purchases_enabled': False,
        'amazon_price_verified': False, 'amazon_sales_verified': False,
        'uk_ie_marketplace_verified': False, 'twelve_month_demand_verified': False,
        'note': 'Catalogue identity only. UPCitemdb data does not verify Amazon UK/IE sales, listings, price, or sustained demand.'
    }
