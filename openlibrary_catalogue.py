"""Read-only Open Library ISBN metadata lookup with constrained redirects."""
import json
import re
import urllib.error
import urllib.parse
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
    elif sum((10-i) * (10 if ch == 'X' else int(ch)) for i, ch in enumerate(isbn)) % 11:
        raise ValueError('ISBN-10 check digit is invalid')
    return isbn


def validate_redirect(url):
    """Only follow canonical Open Library book JSON redirects, never other hosts."""
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != 'https' or parsed.hostname != HOST or parsed.port not in (None, 443)
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or not re.fullmatch(r'/books/OL[0-9]+M\.json', parsed.path)):
        raise ValueError('Open Library redirected to an unapproved destination')
    return url


class SafeOpenLibraryRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        super().__init__()
        self.redirect_count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if self.redirect_count >= 2:
            raise ValueError('Open Library redirect limit exceeded')
        validate_redirect(newurl)
        self.redirect_count += 1
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def preview(isbn, *, fetcher=None):
    isbn = normalize_isbn(isbn)
    url = f'https://{HOST}/isbn/{isbn}.json'
    if fetcher is None:
        req = urllib.request.Request(url, headers={
            'Accept': 'application/json',
            'User-Agent': 'AmazonSustainableDemandMonitor/1.19.1 (catalogue research; contact via repository)'})
        opener = urllib.request.build_opener(SafeOpenLibraryRedirect())
        try:
            with opener.open(req, timeout=10) as response:
                if response.status != 200:
                    raise ValueError('Open Library returned an unexpected HTTP status')
                raw = response.read(MAX_BYTES + 1)
        except urllib.error.HTTPError as exc:
            raise ValueError(f'Open Library HTTP {exc.code}') from exc
        except urllib.error.URLError as exc:
            raise ValueError('Open Library connection failed (network or TLS)') from exc
        except TimeoutError as exc:
            raise ValueError('Open Library request timed out') from exc
    else:
        raw = fetcher(url)
    if isinstance(raw, str):
        raw = raw.encode('utf-8')
    if not isinstance(raw, bytes):
        raise ValueError('Open Library response was not bytes or text')
    if len(raw) > MAX_BYTES:
        raise ValueError('Catalogue response too large')
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('Open Library returned invalid JSON') from exc
    if not isinstance(data, dict) or not isinstance(data.get('title'), str) or not data['title'].strip():
        raise ValueError('Catalogue response missing book title')
    publishers = data.get('publishers', [])
    if not isinstance(publishers, list):
        publishers = []
    return {
        'mode': 'PUBLIC_CATALOGUE_PREVIEW_ONLY',
        'status': 'CATALOGUE_METADATA_FOUND',
        'provider': 'Open Library',
        'isbn': isbn,
        'title': data['title'][:300],
        'publish_date': str(data.get('publish_date', ''))[:100],
        'publisher_names': [p[:120] for p in publishers if isinstance(p, str)][:10],
        'source_url': url,
        'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
        'network_requests': 1,
        'database_writes': 0,
        'purchases_enabled': False,
        'amazon_price_verified': False,
        'amazon_sales_verified': False,
        'amazon_asin_verified': False,
        'note': 'Book catalogue metadata only. ISBN is not an Amazon ASIN or evidence of UK/IE demand. No historical prices or sales.'
    }
