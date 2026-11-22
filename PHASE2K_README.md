# Phase 2K: Account-data inventory and fail-closed erasure guard

## Purpose

This phase inventories Neon schema metadata and identifies potential account-related fields. It **does not** erase data, connect to the live webhook, change the database, or authorize an HTTP 2xx acknowledgment. The handler deliberately raises rather than claiming a successful no-op deletion. A clean inventory of the known five research tables is insufficient to prove there is no eBay account-related personal data in other stores, logs, backups, or future integrations.

## Files to add in GitHub main

- `ebay_phase2k.py`
- `tests/test_ebay_phase2k.py`
- `PHASE2K_README.md`

## Codespaces commands

```bash
python -m unittest discover -s tests -p 'test_ebay_phase2k.py' -v
```

The optional read-only Neon metadata inspection is exposed as `inspect_neon_read_only(connection)`. This package intentionally does not add a live database command or request secrets. To use it with a real Neon connection, a separate, reviewed connection wrapper is required. `assess_inventory()` is usable with manually supplied metadata from a trusted source.

## Blocking production tasks

1. Approve a comprehensive inventory including non-Neon storage, logs, branches, backups and retention paths.
2. Determine whether eBay account identifiers are stored and implement precisely scoped erasure against those locations, with transaction and failure handling.
3. Validate real eBay signatures/payloads, test live Neon transactions, and wire POST only after review.
4. Upgrade from sleeping Render Free hosting and configure production credentials securely.

Keep `post_enabled: false` and leave Render settings unchanged.
