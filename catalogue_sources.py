"""Operator-triggered, no-key catalogue lookups. Neither source supplies Amazon demand."""
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from product_catalogue import lookup_barcode
from api_diagnostics import request_json

UPC_URL = 'https://api.upcitemdb.com/prod/trial/lookup'
MAX_BYTES = 500_000
FIELDS = ['observed_at_utc','barcode','name','brand','quantity','source','source_url','amazon_sales_known','amazon_price_known','amazon_eligibility_known']

def validate_barcode(barcode):
    value = str(barcode).strip()
    if not re.fullmatch(r'\d{8,14}', value):
        raise ValueError('Enter a barcode containing 8–14 digits.')
    return value

def lookup_upcitemdb(barcode, opener=urlopen):
    barcode = validate_barcode(barcode)
    req = Request(UPC_URL + '?' + urlencode({'upc': barcode}), headers={
        'User-Agent':'AmazonSustainableDemandMonitor/1.8.1 (research-only; https://github.com/oykgit/amazon-sustainable-demand-monitor)',
        'Accept':'application/json'})
    data = request_json(req, 'UPCitemdb', opener=opener, max_bytes=MAX_BYTES)
    if not isinstance(data, dict):
        raise ValueError('Invalid catalogue response.')
    items = data.get('items', [])
    if items is None:
        items = []
    if not isinstance(items, list):
        raise ValueError('Invalid product list.')
    # Do not treat fuzzy or unrelated results as an exact barcode match.
    match = next((item for item in items if isinstance(item, dict) and barcode in
                  [str(item.get('ean','')),str(item.get('upc',''))]), None)
    return {'barcode':barcode, 'found':bool(match),
            'name':str((match or {}).get('title') or '').strip(),
            'brand':str((match or {}).get('brand') or '').strip(),
            'quantity':'', 'source':'UPCitemdb',
            'source_url':'https://www.upcitemdb.com/upc/'+barcode,
            'amazon_sales_known':False,'amazon_price_known':False,
            'amazon_eligibility_known':False}

def lookup_product(barcode, source, opener=None):
    barcode=validate_barcode(barcode)
    if source=='UPCitemdb':
        return lookup_upcitemdb(barcode, opener=opener) if opener else lookup_upcitemdb(barcode)
    if source=='Open Food Facts':
        return lookup_barcode(barcode, opener=opener) if opener else lookup_barcode(barcode)
    raise ValueError('Unsupported data source.')

def observation(result, timestamp=None):
    if not result.get('found'):
        raise ValueError('Cannot record a missing product as an observation.')
    at=timestamp or datetime.now(timezone.utc)
    if at.tzinfo is None:
        raise ValueError('Timestamp must have timezone information.')
    return {field: value for field,value in {
        'observed_at_utc':at.astimezone(timezone.utc).isoformat(),
        'barcode':validate_barcode(result['barcode']),
        'name':result.get('name',''),'brand':result.get('brand',''),
        'quantity':result.get('quantity',''),'source':result['source'],
        'source_url':result['source_url'],
        'amazon_sales_known':False,'amazon_price_known':False,
        'amazon_eligibility_known':False}.items() if field in FIELDS}

def merge_observations(existing, new):
    """Merge by source/barcode/UTC timestamp. Return a new DataFrame."""
    import pandas as pd
    if not set(FIELDS).issubset(existing.columns):
        raise ValueError('Existing CSV must have the V1.8 catalogue observation columns.')
    combined=pd.concat([existing[FIELDS],pd.DataFrame([new],columns=FIELDS)],ignore_index=True)
    return combined.drop_duplicates(subset=['source','barcode','observed_at_utc'],keep='last').sort_values('observed_at_utc').reset_index(drop=True)
