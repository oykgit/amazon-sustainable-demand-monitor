# Phase 2D: eBay webhook authentication integration (fail-closed)

## Upload to GitHub main branch
- Replace `ebay_webhook.py`.
- Add `tests/test_ebay_webhook_phase2d.py`.
- Add this `PHASE2D_README.md`.
- Retain `ebay_signature.py` and `ebay_public_keys.py` from Phases 2B and 2C.

## Render
- Start command remains `python ebay_webhook.py`.
- Ensure the webhook service installs `cryptography` in its **Build Command** (e.g. `pip install cryptography`), since the new webhook imports `ebay_signature.py` at startup. Do not modify the separate Streamlit dashboard's build settings.
- Keep `EBAY_VERIFICATION_TOKEN` and `EBAY_NOTIFICATION_ENDPOINT` unchanged.
- **Do not set** `EBAY_PHASE2D_AUTH_TEST=1` for normal deployment. POSTs stay disabled by default.
- `EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET` are **not needed yet** with POST disabled. Never commit credentials.
- `/health` should return `{"status":"phase2d_authentication_integrated","post_enabled":false}`.

## Safety and limitations
- In isolated tests, `authenticate_notification` verifies an ECDSA-SHA256 signature over exact raw bytes using a trusted public key returned by the Phase 2C client. This is **not** a successful live eBay integration test; eBay may have additional signature format requirements to validate against real test notifications.
- An optional diagnostic mode (`EBAY_PHASE2D_AUTH_TEST=1`) attempts authenticated POST handling but still **always returns non-2xx**. Do not enable on production; this is for a controlled testing environment only.
- No Neon writes, deletions, event receipts, or 2xx POST acknowledgements are implemented.
- Do **not** register the endpoint with eBay until Phase 2E, live compatibility testing, and always-on hosting are completed.
