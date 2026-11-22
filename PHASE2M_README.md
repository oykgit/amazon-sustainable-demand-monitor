# Phase 2M: End-to-End Offline Integration Preflight

**This release does not contact eBay, connect to Neon, erase live data, modify `ebay_webhook.py`, or enable POST.**

Add these files to the GitHub `main` branch:

- `ebay_phase2m.py`
- `tests/test_ebay_phase2m.py`
- `PHASE2M_README.md`

Run from GitHub Codespaces in the repository root:

```bash
python -m unittest discover -s tests -p 'test_ebay_phase2m.py' -v
python ebay_phase2m.py
```

The integration tests exercise the **actual Phase 2I orchestration**, Phase 2H transaction engine, and Phase 2L erasure callback using fake authenticated events and a simulated database. They check success, idempotence, rollback, schema drift, rejection without approval, authentication failure, identifier matching, and fail-closed preflight. They do not test real eBay signature compatibility or live PostgreSQL transaction semantics.

`offline_preflight_passed=true` only means the required files, Python syntax, and static POST-disabled guard passed. `production_ready` is intentionally **always false**. All seven live-evidence requirements must be independently satisfied before any live POST activation.

## Required live-evidence work (not performed here)

1. Review every storage destination, including database tables, object stores, logs, caches, exports, backups, and connected providers; document the retention and erasure policy.
2. Approve exact user identity mappings and implement/test the appropriate erasure or documented no-account-data handling.
3. Confirm the payload and signature verification against official eBay test notifications and public-key API.
4. Use disposable, isolated Neon test data to test actual PostgreSQL rollback, duplicates, completion, and concurrent delivery.
5. Wire HTTP POST only after validation, with correct retry/ack semantics. Never return 2xx before the required durable work has completed.
6. Move the webhook to reliable always-on HTTPS hosting and add monitoring.
7. Configure production credentials privately and obtain eBay production keyset activation.

**No Render changes. No SQL migrations. No new environment variables. Do not register the webhook with eBay yet.**
