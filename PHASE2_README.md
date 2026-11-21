# eBay webhook Phase 2 staging

This is a **fail-closed staging update**, not an eBay-compliant production notification receiver.

## Deployment

In GitHub main branch, replace `ebay_webhook.py` at repository root. Add `tests/test_ebay_webhook_phase2.py` using the supplied test file (rename to that exact path). Keep existing `tests/test_ebay_webhook.py` unchanged. Keep the Render start command `python ebay_webhook.py` and existing `EBAY_VERIFICATION_TOKEN` and `EBAY_NOTIFICATION_ENDPOINT` variables.

The `/health` endpoint will report `{"status":"phase2_staging","post_enabled":false}`. GET challenge responses are unchanged. POST requests return HTTP 503 and are never acknowledged as processed.

## Remaining before eBay registration

1. Implement and integration-test signature verification against eBay's actual X-EBAY-SIGNATURE format and Notification API getPublicKey endpoint, including OAuth and key caching. Merely decoding the signature envelope is NOT verification.
2. Audit all existing Neon tables and future eBay collection fields for seller/user identifiers and other personal data. Implement transactional, idempotent erasure and durable notification receipt without logging personal identifiers.
3. Test genuine eBay signed notifications, retries, duplicates, bad signatures, DB outages and Render cold starts.
4. Use a reliably available HTTPS hosting instance; Render Free may sleep.
5. Only then enter the webhook endpoint/token into the eBay developer portal and send eBay's test notification.

Do not put eBay credentials or the verification token in GitHub.
