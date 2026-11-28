"""Offline comparison of structured synthetic product evidence. No transport or storage."""
from decimal import Decimal, ROUND_CEILING
import re
import unicodedata
from commercial_privacy import barcode
from phase3c_browse import MARKETS, money


def normalized(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 300 or not value.isprintable():
        return None
    result = ' '.join(unicodedata.normalize('NFKC', value).casefold().split())
    return result or None


def gtin(value):
    if value is None or value == '':
        return None
    if not isinstance(value, str) or not re.fullmatch(r'(?:[0-9]{8}|[0-9]{12}|[0-9]{13}|[0-9]{14})', value) or not any(c != '0' for c in value):
        raise ValueError('INVALID_GTIN')
    return barcode(value).zfill(14)


def compare_fixture(offer, target, *, gbp_to_eur=None):
    """Inputs are explicit fixture records, not inferred listing attributes.

    Pack counts refer to saleable units in each listing. Variant must be explicit.
    FX is caller-supplied hypothetical EUR per GBP, never a current quote.
    Output intentionally excludes identifiers, titles and seller information.
    """
    if not isinstance(offer, dict) or not isinstance(target, dict):
        raise ValueError('INVALID_RECORD')
    market = offer.get('marketplace')
    if market not in MARKETS or target.get('marketplace') not in MARKETS:
        raise ValueError('INVALID_MARKET')
    currency = MARKETS[market][1]
    conflicts, missing = [], []
    a, b = gtin(offer.get('gtin')), gtin(target.get('gtin'))
    if a and b and a != b:
        conflicts.append('GTIN_CONFLICT')
    elif not a or not b:
        missing.append('GTIN_UNKNOWN')
    for key in ('brand', 'model', 'variant'):
        x, y = normalized(offer.get(key)), normalized(target.get(key))
        if x and y and x != y:
            conflicts.append(key.upper() + '_CONFLICT')
        elif not x or not y:
            missing.append(key.upper() + '_UNKNOWN')
    x, y = offer.get('pack_count'), target.get('pack_count')
    if any(type(n) is not int or not 1 <= n <= 10000 for n in (x,y)):
        missing.append('PACK_UNKNOWN')
    elif x != y:
        conflicts.append('PACK_CONFLICT')
    x, y = offer.get('condition'), target.get('condition')
    if x not in ('NEW','USED','REFURBISHED') or y not in ('NEW','USED','REFURBISHED'):
        missing.append('CONDITION_UNKNOWN')
    elif x != y:
        conflicts.append('CONDITION_CONFLICT')
    elif x != 'NEW':
        conflicts.append('NON_NEW_POLICY')
    title_a, title_b = normalized(offer.get('title')), normalized(target.get('title'))
    title_equal = bool(title_a and title_b and title_a == title_b)
    status = 'REJECT_CONFLICT' if conflicts else 'REVIEW_REQUIRED' if missing else 'STRUCTURED_MATCH_CANDIDATE'
    price = money(offer.get('price'), currency)
    shipping = money(offer.get('shipping_quote'), currency)
    subtotal = price + shipping if price is not None and price > 0 and shipping is not None else None
    fx = Decimal('1') if currency == 'EUR' else money({'currency':'EUR','value':gbp_to_eur}, 'EUR')
    eur = (subtotal * fx).quantize(Decimal('.01'), rounding=ROUND_CEILING) if subtotal is not None and fx is not None and fx > 0 else None
    return dict(phase='3.0D', mode='SYNTHETIC_OFFLINE_ONLY', match_status=status,
                conflicts=conflicts, missing_evidence=missing, title_exact_match=title_equal,
                source_market=market, target_market=target['marketplace'], source_currency=currency,
                asking_price_plus_shipping=str(subtotal) if subtotal is not None else None,
                illustrative_subtotal_eur=str(eur) if eur is not None else None,
                provenance='SYNTHETIC_FIXTURE', fx_verified=False, identity_verified=False,
                landed_cost_verified=False, demand_verified=False, purchase_recommendation=False,
                browse_requests=0, database_writes=0, browse_collection_authorized=False,
                post_activation_authorized=False)


def demo():
    identity = dict(gtin='4006381333931', brand='Example', model='X1', variant='Blue', pack_count=2, condition='NEW', title='Example X1 Blue')
    return compare_fixture(dict(identity, marketplace='UK', price={'value':'12.50','currency':'GBP'}, shipping_quote={'value':'2.00','currency':'GBP'}), dict(identity, marketplace='IE'), gbp_to_eur='1.20')

if __name__ == '__main__':
    import json
    print(json.dumps(demo(), indent=2))
