# Amazon Sustainable Demand Monitor V1.26

V1.26 combines the existing V1.25 offline Keepa JSON normalizer with the V1.24 historical evidence-quality assessment. It does not authenticate Keepa payloads or verify Amazon sales.

## Replace the files one by one in the main branch

1. `app.py` — replace
2. `keepa_evidence_bridge.py` — add
3. `tests/test_keepa_evidence_bridge.py` — add
4. `V126_README.md` — add

Keep `keepa_normalizer.py`, `historical_evidence.py`, the Neon modules, and all other files. This is an incremental patch; the existing dependencies must remain present.

## Test on Render

After deployment, open **Commercial provider readiness** and scroll to **V1.26: Keepa history → 12-month evidence report**. Upload one licensed/authorized Keepa product JSON object (or a clearly marked synthetic test payload). An optional GBP-to-EUR rate enables illustrative price assessment; without it, only sales-rank evidence is assessed. The report shows missing months, counts, basic statistics and important limitations. It does not save data.

## Limitations

- The supplied JSON is not independently authenticated. SHA-256 is an identifier, not provider verification.
- A single FX rate is not a historically accurate currency conversion.
- Rank is not units sold; coverage is not proof of demand.
- No API requests, database writes, or purchases are performed.
