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
