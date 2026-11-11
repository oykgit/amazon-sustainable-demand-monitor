# Amazon Sustainable Demand Monitor V1.0

A research-only, Streamlit dashboard for evaluating 12-month product demand consistency and resale unit economics in the UK and Ireland. **No live Amazon integration, no order placement, and no guarantee of profit.**

## Quick start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to GitHub + Render

1. Create a GitHub repository named `amazon-sustainable-demand-monitor`.
2. Upload `app.py`, `engine.py`, `requirements.txt`, `render.yaml`, `README.md`, and `tests/` into the repository's **main** branch.
3. On Render choose **New > Blueprint** and connect the GitHub repository. Confirm the configuration and deploy.
4. Open the Render URL and upload your market observations CSV.

## Data fields

`market` (UK/IE), `asin`, `product`, `month` (YYYY-MM), `demand_index` (0-100 proxy), `sale_price`, `source_cost`, `marketplace_fee`, `shipping`, `other_cost`, `competition_index` (0-100), `source` (data provenance), `verified` (true/false).

All monetary columns should be in **EUR**, including UK prices converted at a documented exchange rate. Prices must be VAT-consistent; do not mix VAT-inclusive and VAT-exclusive cost figures. Each row is one monthly observation for one ASIN and marketplace. Use legitimate licensed data or manual research; never assume access to Amazon actual sales units. This V1 does not independently verify the `verified` field: it is an operator attestation.

## Limitations

- Demand index is a proxy; scores are heuristics, not calibrated probabilities.
- `verified=true` is supplied by the operator and is not independently validated.
- A minimum of 12 unique monthly observations is required for a candidate decision; missing months are not imputed.
- The score uses historical consistency, margins, competition, price stability and source verification.
- No independent supplier verification, seller restriction checks, live fee calculation, live FX, VAT computation, or import compliance automation yet.
- The sample template is not real product evidence. No purchases are made.
- V1 uses in-memory uploads and has no persistent data store or scheduled collection.

## Roadmap

V1.1: licensed market data integration and provenance checks; V1.2: timestamped persistent history and proper month-contiguity validation; V1.3: landed cost/VAT and marketplace fee connectors; V1.4: prospective paper recommendation journal and outcome validation.
