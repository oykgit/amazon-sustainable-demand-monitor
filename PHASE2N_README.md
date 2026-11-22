# Phase 2N: Production evidence gate (NOT activation)

This release is non-destructive and does not modify `ebay_webhook.py`, Render settings, or Neon tables. It does not make external requests and does not enable POST.

## Upload to GitHub main
- `ebay_phase2n.py`
- `tests/test_ebay_phase2n.py`
- `PHASE2N_NEON_INVENTORY_READ_ONLY.sql`
- `PHASE2N_README.md`

## Codespaces commands
```
python -m unittest discover -s tests -p 'test_ebay_phase2n.py' -v
python ebay_phase2n.py
```
The report must show `production_ready: false`. A separate audited sign-off and real integration testing are required.

## Next operator action
Run the SQL in Neon SQL Editor, and review the results without exposing customer data or credentials. SQL only describes schema; review Render logs, backups, exports and other data stores separately. Confirm actual eBay notification format and signing using official eBay test delivery. Test the real Neon transaction flow using disposable records and safe rollbacks. Upgrade from sleeping Render Free instance before production webhook registration. Configure secrets only through Render environment variables, never GitHub. Do not enable POST or submit the endpoint to eBay until erasure handling, eBay verification, delivery monitoring and approval are demonstrated.

**Important:** The previous Phase 2L erasure callback has not been wired into live HTTP processing. The Phase 2M tests were offline simulations. Phase 2N cannot truthfully declare production activation complete.
