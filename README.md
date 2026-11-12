# Amazon Sustainable Demand Monitor V1.4 — Free data integration

Research-only UK and Ireland dashboard. No orders, purchases or live Amazon sales claims.

## New in V1.4

- Optional **live product identification** by barcode using the public [Open Food Facts](https://world.openfoodfacts.org/) API (primarily packaged food products). No subscription or API key.
- Displays provenance and clear limitations: **Open Food Facts does not provide Amazon UK/IE sales, 12-month demand, Amazon prices, seller eligibility or sourcing costs**.
- Existing operator-authorised HTTPS CSV collector, monthly observations, historical readiness audit, and GitHub Actions remain available.
- Tests for safe barcode input, real metadata mapping and missing products.

## What V1.4 cannot yet do

No freely available verified 12-month Amazon UK/IE sales history has been connected. The existing authorised CSV ingestion requires a feed supplied by the operator. Do not use catalogue identity, Amazon rank snapshots or external search-interest proxies as proof of Amazon sales. There are no evidence-backed buy recommendations until historical demand, supplier cost and seller eligibility are independently established.

## Deploy

Replace the files in `main` with the contents of this ZIP, keeping the `.github/workflows/` and `tests/` directories. Render Auto-Deploy should build the new commit. Do not add secrets or API keys to public GitHub files.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
pytest -q
```

## Source and licensing

Open Food Facts community data is subject to its terms and Open Database License; attribution and share-alike may apply to redistributed databases. This app makes a one-product lookup on direct user request; it does not scrape Amazon or create a bulk Open Food Facts database.

## V1.5: 12-month demand intelligence
The **Demand intelligence** tab analyses user-provided, sourced monthly 0–100 demand proxies, showing coverage, missing months, stability, recent changes and possible spikes. It never fabricates history. A single 12-month window cannot prove annual seasonality. These indicators are not actual Amazon unit sales or validated purchase recommendations. No paid subscription or automated purchasing is required.


## V1.6: Profitability scenario calculator

The **Profitability scenarios** tab accepts user-entered EUR prices and costs, percentage referral fee, fulfilment, inbound shipping, packaging, other costs, returns reserve, and simplified VAT assumptions. It displays net profit, ROI on purchase cost, margin, break-even price, a threshold screen and CSV export. No live Amazon fee or tax API is connected; defaults are **illustrative assumptions, not current official rates**. VAT recoverability must be legally established and this model only adjusts the purchase cost, not other input VAT. UK inputs must be converted to EUR consistently. No automatic purchases or verified buy recommendations.

## V1.7: Vertical sidebar and competition research

All V1.6 workspaces are accessible through a **left sidebar** instead of crowded horizontal tabs. A new **Overview** workspace shows stored research readiness and key safeguards. The new **Competition analysis** workspace accepts manually sourced snapshots (market, ASIN, date, listing count, median competitor price and review count), validates inputs, and produces explicitly heuristic pressure labels and CSV export. No Amazon API, actual sales estimates, live competition collection, automatic purchases, or buying recommendations are implied. The sample CSV is illustrative, not real market data.


## V1.8: Free data integration centre

- **UPCitemdb** public trial barcode lookup added as an optional, operator-triggered source; no account or key required for the public trial endpoint. Coverage, rate limits and access conditions may change. Open Food Facts remains available.
- Both sources supply **product identity only**. They do **not** supply Amazon UK/IE prices, BSR, sales, seller restrictions, 12-month demand or sourcing costs.
- Each successful lookup can be exported with a UTC timestamp and source URL as `catalogue_observations.csv`. Previous exports can be uploaded and merged with de-duplication.
- **Persistence warning:** Render session state and local runtime files are ephemeral. Download the CSV and commit it to `data/catalogue_observations.csv` in GitHub to retain it across deployments. The app does not automatically write to GitHub.
- Future Keepa integration is planned but **not** connected. No automatic Amazon scraping, purchasing or buying recommendations.

## V1.8.1 API connection diagnostics

The Free data integration page now has a **Run connection diagnostics (both providers)** button. It tests the actual barcode lookup route from the deployed server and displays each provider's HTTP status, rate-limit Retry-After where provided, and a safe explanation. Both integrations use the same bounded JSON request handler and an application-identifying User-Agent. HTTP 403 may remain if providers block Render's egress IPs or cloud-hosted traffic; this update does not claim to bypass those restrictions. No paid API, automatic retry, scraping, or purchase functionality is introduced.

## V1.8.2: API reliability safeguards

- Adds `provider_guard.py` for a **per-Streamlit-session** product lookup cache (6-hour TTL, 100-entry limit) and provider-specific cooldowns.
- On HTTP 429, honours a parseable `Retry-After` response (capped at 24 hours); otherwise pauses that provider for one hour. On HTTP 403, pauses that provider for 24 hours by default. No automatic retries or proxy workarounds.
- Connection diagnostics respect active session cooldowns. A compact request-event log and provider status indicators are available on the Free data integration page.
- Cached product identity records are **not** Amazon price/sales data. A cached record can be reused while its provider is unavailable; it is marked as cached.
- **Limitations:** Cache, cooldowns, and events are session-local, not shared across users or server processes, and disappear on restart. They are not a global quota enforcer. Download/commit observation CSVs for longer-term retention. No external API availability or 403 resolution is guaranteed.

## V1.8.3: Optional durable PostgreSQL storage

V1.8.3 adds a `persistent_store.py` module and two buttons in **Free data integration** to save and load sourced catalogue identity observations. Storage is **not active** until a persistent PostgreSQL service is provisioned and its connection string is set as `DATABASE_URL` in the Render service **Environment** settings. Never commit credentials or database URLs to GitHub. The application reports when the database is unconfigured and retains CSV export as a backup. Render's ephemeral filesystem is **not** a durable database. PostgreSQL may incur charges or expire under a free plan: check the provider's terms before provisioning. The app does not create or purchase a database automatically. A successful product lookup is still needed to obtain new observations; this update does not resolve providers' 403/429 restrictions. Database records are product identities, **not Amazon price or demand history**. Save and load are explicit operator actions; no background ingestion is enabled.
