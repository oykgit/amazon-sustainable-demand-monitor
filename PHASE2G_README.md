# Phase 2G: authenticated notification ledger staging

Add `ebay_phase2g.py`, `tests/test_ebay_phase2g.py`, and this README to the repository root (tests under `tests/`).

This module connects Phase 2D authentication to Phase 2F ledger recording **for controlled tests only**.
It is **not imported by the running HTTP handler**. `ebay_webhook.py` stays unchanged, so POST remains disabled.
No Render environment variables, Neon schema changes, or build/start-command changes are needed.

The staging function authenticates a notification before writing its fingerprint, then reads back its status.
It deliberately returns `may_acknowledge: false` and `deletion_complete: false`, even for a duplicate
or a ledger row marked `completed`: status alone does not prove required user-data erasure.

## Test
Install `cryptography` and run `python -m unittest discover -s tests -p 'test_ebay_phase2g.py' -v`.

## Not production-ready
Before enabling POST, verify the eBay signature envelope and key retrieval against eBay's real notification,
implement and test deletion of any eBay personal data across all relevant stores, handle race conditions and
retries, verify real Neon transactions, provide an always-on endpoint, and test eBay's notification delivery.
Do not register the webhook URL with eBay yet.
