# Amazon Sustainable Demand Monitor V1.1 — Free Data Edition

A research-only Streamlit application for Amazon UK and Ireland. No paid API, scraping, automatic orders or claims of access to actual Amazon sales. It accepts lawful manually collected / exported CSV observations and keeps demand proxies separate from financial screens.

## Deploy / upgrade

Replace the files one by one in the **main** branch of your GitHub repository: `app.py`, `engine.py`, `free_sources.py` (new), `requirements.txt`, `render.yaml`, `README.md`, `tests/test_engine.py`, and `tests/test_free_sources.py` (new). Preserve the root paths exactly; do **not** upload the enclosing ZIP folder as an extra directory. Render should auto-deploy if enabled; otherwise use its deploy control. Keep the existing Render start command.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
python -m pytest -q
```

## Data sources, legally and practically

1. **Manual Amazon product research:** record publicly displayed product category ranks and source URLs over time, in compliance with Amazon's terms. Do not use prohibited scraping. The application imports CSV snapshots, not webpages.
2. **Historical research CSV:** use existing data you lawfully collected or can legitimately export, with a documented consistent 0–100 `demand_index`. Do not convert bestseller rank directly into units sold or manufacture backdated records.
3. **Google Trends or similar:** manually export relative search interest for a selected keyword and geography where permitted, then map into the provided CSV template. Relative interest is NOT Amazon sales.
4. **Supplier and cost research:** manually enter authentic offers and fees in the historical research CSV. `verified=true` is **self-attestation**, not a programmatic verification.

V1.1 does not promise a free historical Amazon API: Amazon's public pages do not supply a complete, dependable, downloadable year of per-product unit sales. There is no automatic free data feed in this release. Ireland coverage is particularly limited. Amazon UK signals must not be treated as Ireland sales.

## File formats

Use the download-template buttons in each dashboard tab. Monthly research CSV requires `market,asin,product,month,demand_index,sale_price,source_cost,marketplace_fee,shipping,other_cost,competition_index,source,verified`. All money in **EUR** (convert UK prices with documented FX), and keep VAT treatment consistent. Each row = one product, marketplace and month.

Rank snapshot CSV: `market,asin,product,observed_at,best_seller_rank,category,source_url`. Search interest CSV: `market,keyword,month,search_interest,source`. A product category rank cannot be compared to another category or converted to units sold without a validated model.

## Limitations / next step

- Uploads are in-memory, not persisted. Back up source CSVs and exported reports. No scheduler or live API.
- Existing V1.0 financial heuristic remains; a `TEST PURCHASE CANDIDATE` flag is not a guarantee or independent validation of demand, suppliers, or costs.
- No price/stock/seller-eligibility checking, actual sales, or Irish historical Amazon API.
- A full year of *contiguous* monthly observations is needed for a 12-month historical screen. V1.1 improves this validation and rejects future months.
- Next version: optional paid licensed data source only with user approval, audit trail, forward tracking, validated fees and separate UK/IE eligibility.
