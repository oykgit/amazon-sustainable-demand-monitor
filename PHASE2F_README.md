# Phase 2F: Durable Notification Ledger (staging only)

This package is additive and does not alter `ebay_webhook.py`, the dashboard, or the existing five research tables.

## Installation
Add these files to GitHub main, one by one:
- `ebay_notification_ledger.py`
- `PHASE2F_SCHEMA.sql`
- `tests/test_ebay_notification_ledger.py`
- `PHASE2F_README.md`

## Neon
Run `PHASE2F_SCHEMA.sql` in the Neon SQL Editor connected to the **production** branch. It creates one new table only. Back up the database and inspect SQL before running it.

## Testing
Run `python -m unittest discover -s tests -p 'test_ebay_notification_ledger.py' -v` from repository root. Tests use a fake connection, not live Neon; they do not prove production transaction behavior.

## Important limitations
- The ledger is **not wired into** the HTTP POST handler.
- POST must remain disabled. Do not register the endpoint with eBay yet.
- The ledger records a verified notification only when explicitly called after signature verification. It **does not** perform deletion, determine whether deletion is required, or authorize an HTTP 2xx acknowledgement.
- Existing database fields containing arbitrary text or URLs still require privacy/data-retention review.
- Before production use, implement verified notification handling, transaction-safe erasure or a documented no-user-data policy, replay-safe processing, error handling, and real eBay end-to-end tests.
- Hosting must reliably accept incoming notifications; sleeping Render Free instances may not be suitable.
