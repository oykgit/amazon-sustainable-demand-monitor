"""Offline Browse contract. No network transport, credentials or persistence."""
from urllib.parse import urlencode
from decimal import Decimal, InvalidOperation
import re
from commercial_privacy import barcode

MARKETS = {'UK': ('EBAY_GB', 'GBP'), 'IE': ('EBAY_IE', 'EUR')}
BASE = 'https://api.ebay.com/buy/browse/v1/item_summary/search'


def search_request(*, market, keyword=None, gtin=None, limit=10):
    if market not in MARKETS or type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError('INVALID_SEARCH_POLICY')
    if (keyword is None) == (gtin is None):
        raise ValueError('ONE_SEARCH_INPUT_REQUIRED')
    if keyword is not None:
        if not isinstance(keyword, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 -]{0,79}', keyword):
            raise ValueError('INVALID_KEYWORD')
        params = {'q': keyword}
    else:
        params = {'gtin': barcode(gtin)}
    params.update(limit=limit, filter='buyingOptions:{FIXED_PRICE}')
    return {'url': BASE + '?' + urlencode(params), 'headers': {'X-EBAY-C-MARKETPLACE-ID': MARKETS[market][0], 'Accept': 'application/json'}}


def money(obj, currency):
    if not isinstance(obj, dict) or obj.get('currency') != currency:
        return None
    value = obj.get('value')
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{1,8}(?:\.[0-9]{1,4})?', value):
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def summarize_fixture(payload, market, limit=10):
    """Only aggregate synthetic fixture data; never return identity or free text."""
    if market not in MARKETS or type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError('INVALID_SEARCH_POLICY')
    if not isinstance(payload, dict) or 'errors' in payload:
        raise ValueError('INVALID_RESPONSE')
    rows = payload.get('itemSummaries', []) if payload.get('total') == 0 else payload.get('itemSummaries')
    if not isinstance(rows, list) or len(rows) > limit or any(not isinstance(r, dict) for r in rows):
        raise ValueError('INVALID_RESPONSE')
    currency = MARKETS[market][1]
    prices, shipping_known, fixed, seen = [], 0, 0, set()
    for row in rows:
        ident = row.get('itemId')
        if not isinstance(ident, str) or not re.fullmatch(r'v1\|[0-9]+\|[0-9]+', ident) or ident in seen:
            continue
        seen.add(ident)
        options = row.get('buyingOptions')
        if not isinstance(options, list) or 'FIXED_PRICE' not in options:
            continue
        fixed += 1
        price = money(row.get('price'), currency)
        if price is None or price <= 0:
            continue
        prices.append(price)
        shipping = row.get('shippingOptions')
        if isinstance(shipping, list) and any(isinstance(s, dict) and money(s.get('shippingCost'), currency) is not None for s in shipping):
            shipping_known += 1
    return dict(phase='3.0C', mode='SYNTHETIC_OFFLINE_ONLY', market=market, currency=currency,
                returned_count=len(rows), unique_fixed_price_count=fixed, valid_price_count=len(prices),
                shipping_quote_present_count=shipping_known, minimum_asking_price=str(min(prices)) if prices else None,
                maximum_asking_price=str(max(prices)) if prices else None, demand_verified=False,
                landed_cost_verified=False, purchase_recommendation=False, browse_requests=0,
                database_writes=0, browse_collection_authorized=False, post_activation_authorized=False)


def classify_status(status):
    return {200:'RESPONSE_REVIEW_REQUIRED',401:'AUTHENTICATION_REQUIRED',403:'ACCESS_DENIED',429:'RATE_LIMITED'}.get(status, 'UPSTREAM_UNAVAILABLE' if isinstance(status,int) and 500<=status<=599 else 'REQUEST_REJECTED')


def demo():
    row = {'itemId':'v1|123|0','buyingOptions':['FIXED_PRICE'],'price':{'value':'12.50','currency':'GBP'},'shippingOptions':[{'shippingCost':{'value':'2.00','currency':'GBP'}}]}
    return summarize_fixture({'itemSummaries':[row]}, 'UK')

if __name__ == '__main__':
    import json
    print(json.dumps(demo(), indent=2))
