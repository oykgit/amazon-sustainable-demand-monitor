# Amazon Sustainable Demand Monitor V1.2 — authorised free-feed collection

Research-only Streamlit dashboard for UK/IE, budget €500–€1,000. Does not purchase anything. **No live Amazon API, no Amazon scraping, and no guarantee of product sales or profit.**

## What's new
- Retains V1.1 CSV upload, rank snapshots, search-interest research and product screening.
- GitHub Actions workflow runs every Monday at 07:15 UTC and can collect CSV observations from **user-authorised public HTTPS endpoints**.
- Validates incoming data, rejects malformed dates, duplicate observation keys and invalid metrics, and commits merged CSV histories to `data/`.
- Streamlit reads repository-stored observations when no upload is supplied.
- No source URL configured means no collection. No history is fabricated.

## Install / deploy
Replace existing repository files one by one in the `main` branch; preserve `.github/workflows/collect.yml`, `tests/` and `data/`. Render can redeploy automatically from `main`. Existing Render settings remain unchanged.

## Enable scheduled collection (optional)
In GitHub repository **Settings → Secrets and variables → Actions**, add one or more repository secrets pointing to HTTPS CSV exports you own or are permitted to retrieve:
- `MONTHLY_RESEARCH_CSV_URL` for `engine.REQUIRED` monthly research fields
- `RANK_SNAPSHOTS_CSV_URL` for `free_sources.RANK_FIELDS`
- `SEARCH_INTEREST_CSV_URL` for `free_sources.TREND_FIELDS`

Use **Actions → V1.2 authorised CSV observation collection → Run workflow** for an initial manual test. Weekly runs then append/replace observations by their unique market/product/date key. The bot commits to `main`; branch protection or Actions permissions may prevent writes. The workflow must have **Read and write permissions** for repository contents. GitHub schedules may be delayed or disabled on inactive repositories. Render must redeploy after new commits for the dashboard to show updated data.

Do not put private credentials or customer information in CSV files, especially in public repositories. Do not use an Amazon webpage URL as a CSV feed. Only genuine CSV exports with documented provenance are supported. GitHub Actions runner has outbound network access; feed URLs should be trusted. The collector is intentionally not exposed as an unrestricted public web fetcher.

**Limitations:** There is no guaranteed free 12-month Amazon.ie or Amazon.co.uk sales history. Bestseller ranks are not units sold; search interest is not Amazon purchases. User-supplied `verified=true` is not independent verification. A 12-month claim requires 12 consecutive observed months for a product. No automatic supplier verification. Keepa or another licensed provider may eventually be needed.

Run tests: `python -m unittest discover -s tests -v` (requires `pip install -r requirements.txt`).
