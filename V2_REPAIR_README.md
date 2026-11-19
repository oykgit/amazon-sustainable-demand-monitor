# V2.0 consolidation repair 1: search-interest persistence

This is a targeted patch to the existing V1.26 application, **not a completed V2.0 release**.

## Replace the files one by one in the main branch

1. `app.py` — replace
2. `interest_store.py` — add
3. `tests/test_interest_store.py` — add
4. `V2_REPAIR_README.md` — add

Keep all other repository files and Neon database tables unchanged. No schema migration of existing tables is performed; a separate `search_interest_observations` table is created on first access.

## Manual acceptance test

1. Deploy to Render; keep `DATABASE_URL` set in Render, do not share credentials.
2. Open **External search interest** and upload the genuine monthly Google Trends CSV (Ireland, drawer organiser).
3. Verify that the summary reports 12 months, then click **Save validated search-interest observations to Neon** once.
4. Confirm the inserted count (expect 12 if never saved; otherwise existing records are not overwritten).
5. Refresh the application and open **Data readiness**. The `interest` row should show the number of stored Neon search-interest rows. Export them if desired.
6. Upload and save the same CSV again only if checking duplicate protection: expect zero inserted and 12 existing.

Search interest is not Amazon demand or unit sales. An import is never automatically saved. Rows with the same market, keyword, and month are not overwritten even if values differ; correcting an existing record requires a separate reviewed workflow. The current patch does not add automatic external collection or automatic purchasing.

## Validation

68 local unit tests passed. Database persistence on your live Neon instance has **not** been tested here; follow the manual acceptance steps above.
