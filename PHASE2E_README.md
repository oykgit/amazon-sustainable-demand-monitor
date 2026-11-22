# Phase 2E: Safe Neon schema assessment (staging)

This is a conservative preparatory step for eBay account-deletion handling, not a completed production notification processor.

## Add to the GitHub repository root
- `ebay_deletion_safeguards.py`
- `tests/test_ebay_deletion_safeguards.py`
- `PHASE2E_README.md`

No existing files should be replaced. Do not modify Render environment variables, build/start commands, or `ebay_webhook.py`.

## What it does
- Classifies public schema metadata without reading user records.
- Flags unreviewed tables and columns that may contain eBay user identifiers.
- Always reports `ready_for_processing=False` even for an apparently clean schema.
- Does not delete data, create tables, write receipts, or return webhook acknowledgments.

## Important remaining work
1. Review the **actual live Neon schema**, including any future eBay-derived tables, against deletion requirements.
2. Design a transactional, idempotent receipt/deletion mechanism, including failures and replay protection.
3. Verify eBay signature compatibility against official test notifications and credentials.
4. Test service uptime and production webhook behavior. Render Free sleeps.
5. Only then enable POST and register the endpoint with eBay.

## Run tests
`python -m unittest discover -s tests -p 'test_ebay_deletion_safeguards.py' -v`

No secrets are needed for these tests.
