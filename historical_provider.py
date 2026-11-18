"""Opt-in, one-shot Keepa product metadata preview; never writes or purchases."""
import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ASIN = re.compile(r'^[A-Z0-9]{10}$')

def preview_keepa(asin, market='UK', environ=None, opener=None):
    env = os.environ if environ is None else environ
    asin = str(asin).strip().upper()
    if not ASIN.fullmatch(asin):
        return _result('INVALID_ASIN', asin, market)
    if market not in ('UK',):
        return _result('UNSUPPORTED_MARKET', asin, market)
    key = env.get('KEEPA_API_KEY', '').strip()
    enabled = env.get('RESEARCH_PROVIDER_NETWORK_ENABLED', '').lower() == 'true'
    try:
        budget = int(env.get('RESEARCH_PROVIDER_MAX_DAILY_REQUESTS', '0'))
    except (ValueError, TypeError):
        budget = 0
    if not key or not enabled or budget < 1:
        return _result('NOT_CONFIGURED', asin, market)
    # This is an operator-triggered preview, NOT an enforced shared daily quota.
    # Keepa's token consumption may differ from the count of HTTP requests.
    query = urlencode({'key': key, 'domain': 2, 'asin': asin, 'history': 1})
    url = 'https://api.keepa.com/product?' + query
    request = Request(url, headers={'Accept': 'application/json', 'User-Agent': 'AmazonSustainableDemandMonitor/1.23'})
    fetch = opener or urlopen
    try:
        with fetch(request, timeout=12) as response:
            if getattr(response, 'status', 200) != 200:
                return _result('PROVIDER_HTTP_ERROR', asin, market, requests=1)
            data = json.loads(response.read(2_000_001))
    except HTTPError as exc:
        return _result('RATE_LIMITED' if exc.code == 429 else 'PROVIDER_HTTP_ERROR', asin, market, requests=1, http_status=exc.code)
    except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        return _result('PROVIDER_RESPONSE_ERROR', asin, market, requests=1)
    if not isinstance(data, dict):
        return _result('INVALID_RESPONSE', asin, market, requests=1)
    products = data.get('products', [])
    if not isinstance(products, list):
        return _result('INVALID_RESPONSE', asin, market, requests=1)
    matches = [p for p in products if isinstance(p, dict) and p.get('asin') == asin]
    product = matches[0] if matches else None
    result = _result('PRODUCT_FOUND' if product else 'PRODUCT_NOT_FOUND', asin, market, requests=1)
    result['provider_tokens_left_reported'] = data.get('tokensLeft') if isinstance(data.get('tokensLeft'), int) else None
    if product:
        result['title'] = str(product.get('title') or '')[:200]
        result['has_csv_history_arrays'] = isinstance(product.get('csv'), list)
        result['history_verified'] = False
        result['note'] = 'Raw Keepa arrays are not yet normalized into dated price/BSR evidence. No demand or sales claim.'
    return result

def _result(status, asin, market, requests=0, http_status=None):
    return {'mode':'KEEPA_OPERATOR_TRIGGERED_READ_ONLY','status':status,'provider':'Keepa',
            'asin':asin,'market':market,'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),
            'network_requests':requests,'database_writes':0,'purchases_enabled':False,
            'amazon_sales_verified':False,'historical_demand_verified':False,
            'http_status':http_status,
            'note':'No background collection, durable quota enforcement, database writes or purchases.'}
