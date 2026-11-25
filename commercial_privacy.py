"""Phase 2T.1 offline commercial feed boundary. No I/O or production authority."""
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

FIELDS = ('asin','marketplace','observed_at_utc','selling_price_eur','supplier_cost_eur','referral_pct','fulfilment_eur','inbound_eur','other_eur','returns_pct','source_note','source_url','authorization_reference')
NUMBERS = FIELDS[3:10]

class PrivacyError(ValueError):
    """Only fixed diagnostic codes; never include input values."""

def require(condition, code):
    if not condition:
        raise PrivacyError(code)

def text(value, maximum):
    require(type(value) is str and 0 < len(value) <= maximum, 'INVALID_TEXT')
    require(value.isprintable() and value == value.strip(), 'INVALID_TEXT')
    return value

def asin(value):
    value = text(value, 10).upper()
    require(bool(re.fullmatch(r'[A-Z0-9]{10}', value, re.ASCII)), 'INVALID_ASIN')
    return value

def barcode(value):
    require(type(value) is str and bool(re.fullmatch(r'(?:[0-9]{8}|[0-9]{12,14})', value)), 'INVALID_GTIN')
    total = sum(int(c)*(3 if i%2==0 else 1) for i,c in enumerate(reversed(value[:-1])))
    require((total+int(value[-1]))%10==0, 'INVALID_GTIN')
    return value

def source_url(value, allowed_host, product):
    # Deliberately narrow: only canonical product paths, no arbitrary URLs.
    value = text(value, 500)
    require(type(allowed_host) is str and bool(re.fullmatch(r'[a-z0-9]+(?:[.-][a-z0-9]+)+', allowed_host)), 'INVALID_HOST_POLICY')
    expected = f'https://{allowed_host}/dp/{product}'
    require(value == expected, 'UNAPPROVED_SOURCE_URL')
    return expected

def validate_feed_row(row, *, allowed_host, approved_reference, now=None):
    """Return normalized commercial data, or raise a fixed-code PrivacyError.

    Policy inputs must originate from trusted configuration, never the feed.
    This narrow pilot accepts only canonical /dp/ URLs and fixed source notes.
    It does not independently verify provider rights or detect all personal data.
    """
    require(type(row) is dict and set(row)==set(FIELDS), 'UNAPPROVED_SCHEMA')
    product = asin(row['asin'])
    require(type(row['marketplace']) is str and row['marketplace'] in ('UK','IE'), 'INVALID_MARKET')
    require(type(approved_reference) is str and bool(re.fullmatch(r'PERM-[0-9]{1,12}', approved_reference)), 'INVALID_PERMISSION_POLICY')
    require(type(row['authorization_reference']) is str and row['authorization_reference']==approved_reference, 'UNAPPROVED_PERMISSION')
    require(type(row['source_note']) is str and row['source_note']=='Authorized commercial feed', 'UNAPPROVED_SOURCE_NOTE')
    url = source_url(row['source_url'], allowed_host, product)
    stamp = text(row['observed_at_utc'], 40)
    try:
        at = datetime.fromisoformat(stamp.replace('Z','+00:00'))
        require(at.tzinfo is not None and at.utcoffset() is not None, 'INVALID_TIMESTAMP')
        at = at.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise PrivacyError('INVALID_TIMESTAMP') from None
    require(at <= (now or datetime.now(timezone.utc)), 'FUTURE_TIMESTAMP')
    result = dict(row, asin=product, observed_at_utc=at.isoformat(), source_url=url)
    for key in NUMBERS:
        v = row[key]
        require(type(v) in (str,int,float,Decimal) and len(str(v))<=40, 'INVALID_NUMBER')
        try:
            number = Decimal(str(v))
        except InvalidOperation:
            raise PrivacyError('INVALID_NUMBER') from None
        require(number.is_finite() and 0<=number<=(100 if key.endswith('_pct') else 1000000), 'INVALID_NUMBER')
        result[key] = str(number)
    return result
