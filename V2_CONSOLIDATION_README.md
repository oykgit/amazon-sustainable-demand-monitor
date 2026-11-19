# V2.0 Consolidation Repair 2: Connected product assessment

Based on the deployed V2.0 Repair 1 `app.py` (including `import io`) and the repository's existing Neon modules. This is a read-only join; no migrations, background requests, or purchases.

## Replace the files one by one in the main branch

1. `app.py` — replace
2. `consolidated_assessment.py` — add
3. `tests/test_consolidated_assessment.py` — add
4. `V2_CONSOLIDATION_README.md` — add

Keep `interest_store.py` and all other existing files unchanged. Do not overwrite `.env`, Render environment variables or Neon tables.

## Test on Render

1. Wait for Live, open **ASIN research comparison**.
2. Click **Load consolidated research from Neon**.
3. Confirm existing ASIN snapshots and identities appear.
4. Optionally select a Google Trends keyword **for the same market**; no association is inferred automatically.
5. Download **Export consolidated product assessment CSV**.
6. Refresh and repeat. No save button is present in the consolidated section.

## Interpretation

- The report joins latest operator-recorded product identity to the existing snapshot comparison and optional Google Trends observations.
- Search interest is a 0–100 relative web-search index, not sales volume.
- The original research score remains an evidence/economics heuristic, not a buy signal.
- No live provider calls, Neon writes, database migrations, or purchases are made by the new section.
- A keyword-to-ASIN association is session-only; the CSV documents the chosen association.
