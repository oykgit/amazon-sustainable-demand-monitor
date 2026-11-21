# eBay notification service: phase 1, NOT ready for eBay registration

This service is deliberately **challenge-test only**. It does not process deletion notifications and returns HTTP 503 for POST. **Do not enter its URL into eBay's notification subscription form yet.** A verified signature-validation and data-deletion implementation must be completed before registration.

## Deployment

1. Add `ebay_webhook.py` at the repository root. Add `tests/test_ebay_webhook.py` in `tests/`.
2. In the existing Render account create a **separate Web Service** from the same GitHub repository. Leave the current Streamlit service unchanged.
3. Python runtime. Build command: `echo 'stdlib only'`. Start command: `python ebay_webhook.py`. Set health check path `/health`.
4. Set Render environment variable `EBAY_VERIFICATION_TOKEN` to a newly generated random 32–80-character string using only ASCII letters, numbers, `_`, or `-`. Never commit it.
5. Set `EBAY_NOTIFICATION_ENDPOINT` to the **exact** HTTPS URL that will be submitted to eBay later, e.g. `https://YOUR-NEW-SERVICE.onrender.com/ebay/account-deletion`. No trailing slash. Keep this exact string stable.
6. Verify `/health` returns `post_enabled:false`. For an isolated local challenge check, request `/ebay/account-deletion?challenge_code=test` and independently compare SHA256('test'+token+endpoint).

## Before enabling eBay notifications

Implement POST validation using eBay's notification signing scheme and official public key endpoint, persistent audit and idempotency, identification and deletion of all eBay user personal data from Neon and any other storage, privacy-preserving logs, and operational monitoring. Only acknowledge with 2xx after processing or durable verified acceptance. Do not assume storing product listings automatically qualifies for the no-persistence exemption. Verify Render's availability and choose an always-on service if required.

This update makes no eBay API calls, does not activate the Production keyset, does not write to Neon, and does not place orders.
