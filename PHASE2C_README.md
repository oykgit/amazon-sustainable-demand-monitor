# Phase 2C: eBay public key retrieval (isolated, no POST activation)

Add `ebay_public_keys.py` at repository root and `tests/test_ebay_public_keys.py` under `tests/`. No other code changes.

## Tests

From repository root: `python -m unittest discover -s tests -p 'test_ebay_public_keys.py' -v`

## Configuration

For future authenticated production calls, add `EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET` as **private Render environment variables** from the enabled eBay Production keyset. Never commit credentials. You do **not** need to add them merely to deploy this isolated module.

## Safety boundary

This module retrieves an OAuth application token and eBay's signing public key by validated `kid`. It caches keys in memory for one hour. It does not parse eBay signature envelopes, verify a notification signature, enable POST, acknowledge a notification, write to Neon, or delete records. The existing `ebay_webhook.py` remains unchanged, with POST disabled. Do not register the endpoint with eBay until the full signature and deletion-handling pipeline has passed end-to-end tests and service uptime is addressed.

## Official API

- OAuth token: `POST https://api.ebay.com/identity/v1/oauth2/token`
- Public key: `GET https://api.ebay.com/commerce/notification/v1/public_key/{public_key_id}`
- Scope: `https://api.ebay.com/oauth/api_scope`

The code expects the Notification API response field `key` to contain a PEM public key. Verify against a real authorized response before enabling POST. No live eBay requests were made during tests.
