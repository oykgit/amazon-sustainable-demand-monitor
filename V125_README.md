# V1.25 Keepa historical JSON normalization

## Deployment
Replace the files one by one in the main branch:
- `app.py` — replace
- `keepa_normalizer.py` — add
- `tests/test_keepa_normalizer.py` — add
- `V125_README.md` — add

Keep all existing modules, GitHub Actions workflows, Render secrets, and Neon database untouched. This package is an incremental patch, not a full repository.

## Test
After Render is Live, open **Commercial provider readiness**, scroll to **V1.25: Keepa historical JSON normalizer**. It accepts one Keepa product JSON object (or a `products` wrapper containing exactly one product). If no Keepa data is available, simply verify the new section appears; do not invent provider data.

Keepa `csv` array indexes handled: 0 Amazon price, 1 New price, 3 Sales Rank. Dates are Keepa minutes since 2011-01-01 UTC. UK prices are stored as GBP (pence / 100). Optional FX conversion is an unverified operator estimate. Missing and out-of-stock sentinels are excluded. Rank is not sales volume.

This module is offline and read-only; it does not fetch Keepa data, authenticate provenance, write Neon, or enable purchases. The existing V1.24 coverage checker remains a separate tool.
