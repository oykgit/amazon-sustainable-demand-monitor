# Phase 2J — Read-only production-readiness evidence gate

**Purpose:** make unresolved production requirements visible instead of implying that offline modules are production-ready. This does **not** implement account erasure or enable POST processing.

## Upload to GitHub main
Add these three new files individually: `ebay_phase2j_audit.py`, `tests/test_ebay_phase2j_audit.py`, `PHASE2J_README.md`. No changes to existing files, Neon SQL, Render settings, or the 24-button Streamlit dashboard.

## Run locally (or in GitHub Codespaces)

```bash
python -m unittest discover -s tests -p 'test_ebay_phase2j_audit.py' -v
python ebay_phase2j_audit.py
```

The report evaluates files in the current directory and checks Python syntax and the *known Phase 2D* fail-closed POST configuration. A green local report is **not** proof of deployed revision, signature compatibility, database erasure, webhook delivery, or production compliance. The report always says `production_ready: false`.

## Manual evidence required before production

1. Inventory every storage destination, log, backup, analytics service, queue, and downstream provider holding eBay-derived personal/account data. Map each account identifier to each destination; obtain explicit owner approval. Earlier searches of five Neon research tables are insufficient.
2. Verify actual eBay Marketplace Account Deletion payload, signature envelope and algorithm, public-key API response and token scope using official eBay docs and controlled test events. Never infer compatibility from mocked signatures.
3. Implement an audited, identity-based erasure handler covering the approved inventory. Test failure rollback, retries, duplicate events, concurrent requests, and zero-matching-data outcomes on an isolated Neon test database.
4. Connect the approved handler to `ebay_webhook.py`; only return 2xx once the appropriate processing/acknowledgment requirements are met. Do not turn on the Phase 2D diagnostic flag as a substitute.
5. Move to reliable always-on HTTPS hosting, monitor delivery, and complete eBay portal validation. Store API credentials in protected Render environment variables; never commit them.

**Security note:** the `ebay_phase2h.py` engine commits ledger staging separately from erasure, so a failure between steps must be retried. Test this behavior explicitly. The current webhook is intentionally disabled for live POST.
