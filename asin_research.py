"""ASIN-first, marketplace-specific operator observations (not Amazon API data)."""
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

MARKETPLACES = {'UK': 'https://www.amazon.co.uk/dp/', 'IE': 'https://www.amazon.ie/dp/'}

def validate_asin(value):
    asin = str(value).strip().upper()
    if not re.fullmatch(r'[A-Z0-9]{10}', asin):
        raise ValueError('ASIN must contain exactly 10 letters or digits.')
    return asin

def validate_marketplace(value):
    if value not in MARKETPLACES:
        raise ValueError('Marketplace must be UK or IE.')
    return value

def asin_url(asin, marketplace):
    return MARKETPLACES[validate_marketplace(marketplace)] + validate_asin(asin)

def make_observation(asin, marketplace, name, ean_upc='', source_url='', at=None):
    asin = validate_asin(asin)
    marketplace = validate_marketplace(marketplace)
    name = str(name).strip()
    if not 1 <= len(name) <= 300:
        raise ValueError('Product name must contain 1–300 characters.')
    ean_upc = str(ean_upc).strip()
    if ean_upc and not re.fullmatch(r'\d{8,14}', ean_upc):
        raise ValueError('EAN/UPC must contain 8–14 digits, or be blank.')
    source_url = str(source_url).strip() or asin_url(asin, marketplace)
    parsed = urlparse(source_url)
    if parsed.scheme != 'https' or not parsed.netloc or len(source_url) > 1000 or parsed.username or parsed.password:
        raise ValueError('Source URL must be a valid HTTPS URL without credentials.')
    at = at or datetime.now(timezone.utc)
    if at.tzinfo is None:
        raise ValueError('Observation time must include timezone.')
    return {'observed_at_utc': at.astimezone(timezone.utc).isoformat(), 'asin': asin,
            'marketplace': marketplace, 'name': name, 'ean_upc': ean_upc,
            'source_url': source_url, 'source': 'Operator documented',
            'amazon_sales_known': False, 'amazon_price_known': False,
            'amazon_eligibility_known': False}
