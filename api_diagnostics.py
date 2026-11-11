"""Safe, operator-triggered diagnostics for approved catalogue endpoints."""
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

class CatalogueConnectionError(Exception):
    def __init__(self, provider, status, explanation, retry_after=None):
        self.provider, self.status, self.retry_after = provider, status, retry_after
        super().__init__(f'{provider}: {explanation} (HTTP {status})' if status else f'{provider}: {explanation}')


def request_json(req, provider, opener=urlopen, timeout=12, max_bytes=500_000):
    import json
    try:
        with opener(req, timeout=timeout) as response:
            raw = response.read(max_bytes + 1)
            if len(raw) > max_bytes:
                raise ValueError(f'{provider}: response exceeds size limit')
            return json.loads(raw)
    except HTTPError as exc:
        status = exc.code
        retry_after = exc.headers.get('Retry-After') if exc.headers else None
        explanations = {
            401: 'authentication rejected; this endpoint may require credentials',
            403: 'access denied from this server or request; provider restrictions or quota may apply',
            404: 'requested resource was not found',
            429: 'rate limit reached; wait before retrying',
            500: 'provider server error',
            502: 'provider gateway error',
            503: 'provider temporarily unavailable',
        }
        raise CatalogueConnectionError(provider, status, explanations.get(status, 'HTTP request rejected'), retry_after) from exc
    except URLError as exc:
        raise CatalogueConnectionError(provider, None, f'network or DNS connection failed ({type(exc.reason).__name__})') from exc
    except TimeoutError as exc:
        raise CatalogueConnectionError(provider, None, 'request timed out') from exc
    except json.JSONDecodeError as exc:
        raise CatalogueConnectionError(provider, None, 'provider returned invalid JSON') from exc


def check_provider(provider, barcode='3017620422003', opener=urlopen):
    """Test the exact lookup code path, without automatic retries or writes."""
    from catalogue_sources import lookup_product
    try:
        result = lookup_product(barcode, provider, opener=opener)
        return {'provider':provider, 'reachable':True, 'product_found':result['found'],
                'message':'Request completed; a matching product was found.' if result['found'] else 'Request completed; no matching product returned.'}
    except CatalogueConnectionError as exc:
        return {'provider':provider, 'reachable':False, 'product_found':False,
                'http_status':exc.status, 'retry_after':exc.retry_after, 'message':str(exc)}
    except Exception as exc:
        return {'provider':provider, 'reachable':False, 'product_found':False,
                'message':f'{type(exc).__name__}: {exc}'}
