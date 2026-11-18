# Amazon Sustainable Demand Monitor V1.23

Preserves V1.22.1 three-band horizontal navigation (4 buttons x 2 rows per band). Adds an **opt-in, operator-triggered** Keepa product lookup in Commercial provider readiness. No scheduled commercial calls, database writes, purchasing, or verified 12-month demand calculations.

## Install (main branch)
Replace `app.py`; add `historical_provider.py` and `tests/test_historical_provider.py`. Keep all other files, including `provider_readiness.py`, database modules, and workflows. Do not upload API credentials to GitHub.

## Configure (optional)
In Render environment variables set `KEEPA_API_KEY` to your own active key, `RESEARCH_PROVIDER_NETWORK_ENABLED=true`, and `RESEARCH_PROVIDER_MAX_DAILY_REQUESTS=1` to opt into a manual one-product test. These settings **do not enforce a durable shared daily budget**, and Keepa may charge more than one token per request. Without all three, the lookup returns `NOT_CONFIGURED` and sends no request. Keepa terms, subscription, and token allowance must be verified by the account holder. The current lookup uses Keepa domain=2 (Amazon UK). No Ireland-specific Amazon marketplace or sales data is claimed.

## Safety and limitations
- A user must click the button to initiate each request; this feature does not run on a schedule.
- Only summarized metadata and a flag indicating historical arrays are returned. Raw history is **not** normalized, validated, or saved.
- No evidence of sales volumes, 12-month sustained demand, or product buying eligibility is established.
- No network calls occur during configuration diagnostics or if credentials/opt-in are missing.
- `RESEARCH_PROVIDER_MAX_DAILY_REQUESTS` is a readiness prerequisite, **not** a quota counter. Do not repeatedly click until a durable quota is implemented.
- Keepa credentials are sent only to its HTTPS API endpoint in a query parameter as required by its API; do not paste API URLs or Render secrets into chats or logs.

## Test
`python -m pytest -q tests/test_historical_provider.py`
