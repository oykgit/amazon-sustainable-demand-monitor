"""Explicit, one-shot production OAuth probe; no public route or data collection."""
import argparse
import json
from urllib.request import HTTPRedirectHandler, build_opener
from ebay_public_keys import EbayPublicKeyClient


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def probe(authorized=False, client_factory=EbayPublicKeyClient):
    result = dict(phase='3.0B', oauth_status='NOT_RUN', token_exposed=False,
                  browse_requests=0, database_writes=0,
                  browse_collection_authorized=False, post_activation_authorized=False)
    if not authorized:
        return result
    try:
        client = client_factory(opener=build_opener(NoRedirect()).open)
        if not client.client_id or not client.client_secret:
            result['oauth_status'] = 'CREDENTIALS_MISSING'
            return result
        token = client._access_token()
        if not isinstance(token, str) or not token:
            raise ValueError('invalid token')
        result['oauth_status'] = 'PASS_TOKEN_ISSUED'
    except Exception:
        result['oauth_status'] = 'FAIL_OR_UNCONFIRMED'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authorize-token-request', action='store_true')
    args = parser.parse_args()
    result = probe(args.authorize_token_request)
    print(json.dumps(result, indent=2))
    return 0 if result['oauth_status'] in ('NOT_RUN', 'PASS_TOKEN_ISSUED') else 1


if __name__ == '__main__':
    raise SystemExit(main())
