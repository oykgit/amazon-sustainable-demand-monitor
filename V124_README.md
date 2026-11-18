# V1.24 Historical Evidence Quality

This patch is based on the V1.23 app.py and retains its three colored horizontal navigation bands (4 columns × 2 rows each). No buttons were added or removed.

## Replace the files one by one in the main branch
- `app.py` — replace
- `historical_evidence.py` — add
- `tests/test_historical_evidence.py` — add
- `V124_README.md` — add

Keep all other repository files unchanged. The existing Neon database and GitHub Actions workflows are not modified.

## Test
Deploy to Render, open **Commercial provider readiness**, scroll to **V1.24: Historical evidence quality**, and upload an authorized CSV with columns:
`asin,market,observed_date,source_provider,source_reference,evidence_type,value`

Allowed `evidence_type` values: `PRICE_EUR`, `SALES_RANK`. Dates: YYYY-MM-DD. Values: positive numbers; rank integers. Maximum 5000 rows / 1MB.

No synthetic CSV should be represented as real provider data. Even a sufficient coverage gate is NOT verification of Amazon sales or demand. No network requests, database writes, or purchases.
