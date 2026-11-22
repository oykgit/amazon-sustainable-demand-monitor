# Phase 2L: Explicit account-data erasure callback (offline)

**Status:** Staging only; does not enable POST, does not modify Render or Neon.

`ebay_phase2l.py` provides an erasure callback compatible with the existing
`ebay_phase2i.process_notification_offline` callback interface. Phase 2H owns
the database transaction and rollback. The callback requires an operator-approved
inventory of **all** storage systems, identity mappings, and known tables.

**No account-data tables are currently approved.** The `ebay_user_cache` in
unit tests is fictional and must **not** be created or treated as real. Therefore
this package cannot yet authorize erasure or any successful webhook response.

The actual observed Neon tables are product research tables plus the notification
ledger. An audited zero-account-data workflow would require its own explicit
approval and proof that no other stores, logs, exports, branches, or backups hold
relevant data. This module intentionally rejects an empty store policy.

## Upload
Add these files to GitHub `main` one by one:
- `ebay_phase2l.py`
- `tests/test_ebay_phase2l.py`
- `PHASE2L_README.md`

## Codespaces test
`python -m unittest discover -s tests -p 'test_ebay_phase2l.py' -v`

## Security and next steps
1. Complete an inventory of Neon and non-Neon storage and document exact
   account identifier mappings. Review whether eBay product data contains
   personal data and how it is retained.
2. Independently review the eBay event schema and signature format against
   official documentation and real signed tests.
3. Add an approved policy for actual account-data stores or a separately
   reviewed no-data outcome, and test against disposable Neon fixtures.
4. Wire the approved workflow into HTTP POST only after success, retry and
   idempotency semantics are verified. Never log raw personal identifiers.
5. Use reliable always-on hosting before production activation.

Do not configure eBay Production credentials, register the webhook, or enable
POST processing based on these unit tests alone.
