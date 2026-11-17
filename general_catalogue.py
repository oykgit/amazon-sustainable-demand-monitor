"""V1.20 read-only, operator-triggered public catalogue lookup.

Catalogue metadata is not Amazon marketplace or demand evidence.
"""
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone

PROVIDERS = {
    'Open Food Facts': 'world.openfoodfacts.org',
    'Open Beauty Facts': 'world.openbeautyfacts.org',
}
MAX_BYTES = 256_000


def normalize_gtin(value):
    code = re.sub(r'[\s-]', '', str(value))
    if not re.fullmatch(r'\d{8}|\d{12}|\d{13}|\d{14}', code):
        raise ValueError('Enter a GTIN-8, UPC-12, EAN-13 or GTIN-14 barcode')
    digits = [int(x) for x in code]
    check = (10 - sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(digits[:-1]))) % 10) % 10
    if check != digits[-1]:
        raise ValueError('Barcode check digit is invalid')
    return code


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Provider redirect blocked; no request to redirected destination')


def preview(provider, barcode, *, fetcher=None):
    if provider not in PROVIDERS:
        raise ValueError('Unsupported catalogue provider')
    code = normalize_gtin(barcode)
    host = PROVIDERS[provider]
    url = f'https://{host}/api/v2/product/{code}.json?fields=code,product_name,brands,quantity,categories,ingredients_text,image_url'
    if fetcher is None:
        req = urllib.request.Request(url, headers={
            'Accept': 'application/json',
            'User-Agent': 'AmazonSustainableDemandMonitor/1.20 (single-item catalogue research; project repository)'})
        try:
            with urllib.request.build_opener(NoRedirect()).open(req, timeout=10) as response:
                if response.status != 200:
                    raise ValueError(f'{provider} returned HTTP {response.status}')
                raw = response.read(MAX_BYTES + 1)
        except urllib.error.HTTPError as exc:
            raise ValueError(f'{provider} returned HTTP {exc.code}; provider may block hosted requests') from exc
        except urllib.error.URLError as exc:
            raise ValueError(f'{provider} network/TLS connection failed') from exc
        except TimeoutError as exc:
            raise ValueError(f'{provider} request timed out') from exc
    else:
        raw = fetcher(url)
    if isinstance(raw, str):
        raw = raw.encode('utf-8')
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise ValueError('Provider response invalid or exceeds 256 KB')
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('Provider returned invalid JSON') from exc
    if not isinstance(data, dict):
        raise ValueError('Provider returned an unexpected JSON structure')
    status = data.get('status')
    if status not in (0, 1, '0', '1'):
        raise ValueError('Provider response has no recognized product status')
    product = data.get('product') if status in (1, '1') else None
    if product is not None and not isinstance(product, dict):
        raise ValueError('Provider product record is malformed')
    product = product or {}
    def safe_field(key, max_len=300):
        val = product.get(key)
        return val[:max_len] if isinstance(val, str) else ''
    return {
        'mode': 'PUBLIC_GENERAL_CATALOGUE_PREVIEW_ONLY',
        'status': 'CATALOGUE_METADATA_FOUND' if status in (1, '1') else 'PRODUCT_NOT_FOUND',
        'provider': provider, 'barcode': code,
        'product_name': safe_field('product_name'), 'brands': safe_field('brands'),
        'quantity': safe_field('quantity'), 'categories': safe_field('categories'),
        'source_url': url,
        'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
        'network_requests': 1, 'database_writes': 0, 'purchases_enabled': False,
        'amazon_price_verified': False, 'amazon_sales_verified': False,
        'amazon_asin_verified': False, 'uk_ie_listing_verified': False,
        'note': 'Community catalogue metadata only; no Amazon UK/IE price, listing, sales or historical demand verification.'
    }
