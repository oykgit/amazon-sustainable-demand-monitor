# Phase 2H: Transactional account-deletion engine (staging)

Add these three new files to the GitHub `main` branch:

- `ebay_phase2h.py`
- `tests/test_ebay_phase2h.py`
- `PHASE2H_README.md`

**No Render or Neon configuration changes.** The HTTP webhook is unchanged and
POST remains disabled. Existing research tables are untouched.

This engine locks a previously staged ledger record, invokes a **separately
approved** inspection-and-erasure callback, and marks completion in the same
PostgreSQL transaction. Failures roll back; duplicate completed notifications
are not reprocessed. It deliberately does not issue an HTTP acknowledgment.

A zero-match search for the word `ebay` is **not** a complete data inventory.
The callback is not provided in this package because the mapping of eBay user
identifiers to stored records and the full set of data stores have not been
verified. Do not set `storage_inventory_approved=True` in production based
solely on the existing five-table query.

Run tests with `python -m unittest discover -s tests -p 'test_ebay_phase2h.py' -v`.

Before production: inspect every storage location (including logs, backups,
external services, future eBay data tables), establish exact identity matching,
implement the real erasure callback, validate eBay's actual signature and event
shape, test real Neon transactions and concurrency, and arrange always-on hosting.
Do **not** register the endpoint with eBay yet.
