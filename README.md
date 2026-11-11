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
