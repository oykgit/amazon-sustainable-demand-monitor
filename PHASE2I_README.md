# Phase 2I: Offline integration of authenticated notification and transactional erasure

Add `ebay_phase2i.py`, `tests/test_ebay_phase2i.py`, and this README to the `main` branch. Do not replace any existing file.

This integrates the existing Phase 2D signature-authentication entry point, Phase 2F ledger and Phase 2H transactional deletion engine in **offline staging**. The account-data callback receives the **authenticated full event**, including user account identifiers; notification IDs must never be treated as user IDs. It refuses to run without explicit storage-inventory approval and a callable erasure handler. It never authorizes an HTTP 2xx response.

**Not production-ready:** No real account-data erasure callback is supplied; the previously queried database columns are not a complete audit of all stores. No live Neon transactions or real eBay-signed notification have been tested. The running `ebay_webhook.py` remains unchanged and POST remains disabled. Do not register the URL with eBay yet. An always-on host is required for reliable delivery.

Test with `python -m unittest discover -s tests -p 'test_ebay_phase2i.py' -v` after installing the existing project dependencies.
