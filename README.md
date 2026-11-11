# Amazon Sustainable Demand Monitor V1.3 — Free-data audit and CI

Research-only dashboard for Amazon UK and Ireland; budget €500–€1,000. **No live Amazon API, no automated Amazon scraping, no verified sales volumes and no purchase execution.**

## New in V1.3
- **Data readiness** tab shows whether each stored feed is absent, invalid, stale or current, including latest observation date.
- Per-product 12-month coverage audit identifies missing months separately for UK and Ireland.
- Downloadable coverage audit CSV.
- GitHub Actions CI tests on each commit to `main`, useful for diagnosing a failed code update.
- Existing V1.2 upload, stored-data, scheduled authorised CSV collection and analysis preserved.

## Install
Replace files one by one in GitHub `main` using the ZIP, preserving folder paths. Render Auto-Deploy set to **On Commit** should start after a new commit. This is a fresh commit and can serve as the auto-deploy test. If Render does not deploy, check Render Events and GitHub Actions; CI and deployment are separate.

## What is NOT provided
There is no preconfigured authorised historical Amazon data source. Weekly GitHub Actions collection only works after you add one or more permitted HTTPS CSV feeds as repository secrets (`MONTHLY_RESEARCH_CSV_URL`, `RANK_SNAPSHOTS_CSV_URL`, `SEARCH_INTEREST_CSV_URL`). A GitHub Actions success with no secrets means a no-op, not successful data collection. Rank and search interest are proxies, not actual Amazon units sold. `verified=true` is only an operator assertion, not independent confirmation. Do not buy inventory based on a preliminary screen alone.

## Run tests
`pip install -r requirements.txt` then `python -m unittest discover -s tests -v`.
