"""V1.19 Open Library ISBN catalogue lookup; metadata only, no DB writes.

Uses a fixed public endpoint, never arbitrary user-supplied URLs.
Follow Open Library API usage policy and attribution requirements.
"""
import json
import re
import urllib.request
from datetime import datetime, timezone

MAX_BYTES = 256_000
HOST = 'openlibrary.org'


def normalize_isbn(value):
    isbn = re.sub(r'[ -]', '', str(value)).upper()
    if not re.fullmatch(r'(?:[0-9]{13}|[0-9]{9}[0-9X])', isbn):
        raise ValueError('Enter a valid-format ISBN-10 or ISBN-13')
    if len(isbn) == 13:
        if sum(int(ch) * (1 if i % 2 == 0 else 3) for i, ch in enumerate(isbn)) % 10:
            raise ValueError('ISBN-13 check digit is invalid')
    else:
        if sum((10-i) * (10 if ch == 'X' else int(ch)) for i,ch in enumerate(isbn)) % 11:
            raise ValueError('ISBN-10 check digit is invalid')
    return isbn


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Redirect prohibited')


def preview(isbn, *, fetcher=None):
    isbn = normalize_isbn(isbn)
    url = f'https://{HOST}/isbn/{isbn}.json'
    if fetcher is None:
        req = urllib.request.Request(url, headers={
            'Accept':'application/json',
            'User-Agent':'AmazonSustainableDemandMonitor/1.19 (catalogue research; contact via repository)'})
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=10) as response:
            if response.status != 200:
                raise ValueError('Catalogue provider returned an unexpected status')
            raw = response.read(MAX_BYTES + 1)
    else:
        raw = fetcher(url)
    if isinstance(raw, str): raw = raw.encode('utf-8')
    if len(raw) > MAX_BYTES: raise ValueError('Catalogue response too large')
    data = json.loads(raw)
    if not isinstance(data, dict) or not isinstance(data.get('title'), str):
        raise ValueError('Catalogue response missing book title')
    return {
        'mode':'PUBLIC_CATALOGUE_PREVIEW_ONLY',
        'status':'CATALOGUE_METADATA_FOUND',
        'provider':'Open Library',
        'isbn':isbn,
        'title':data['title'][:300],
        'publish_date':str(data.get('publish_date',''))[:100],
        'publisher_names':[p[:120] for p in data.get('publishers',[]) if isinstance(p,str)][:10],
        'source_url':url,
        'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),
        'network_requests':1,
        'database_writes':0,
        'purchases_enabled':False,
        'amazon_price_verified':False,
        'amazon_sales_verified':False,
        'amazon_asin_verified':False,
        'note':'Book catalogue metadata only. ISBN is not an Amazon ASIN or evidence of UK/IE demand. No historical prices or sales.'
    }
