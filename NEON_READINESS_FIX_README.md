# V2.0 Neon readiness display correction

This is a targeted display correction, not a new monitoring stage. The older Overview counters were reading repository `data/*.csv` files while the new commercial panel reads Neon. They are now explicitly labeled as different stores.

The Overview also reads the existing `search_interest_observations` Neon table without modifying it, showing per-market keyword counts and average relative interest. Missing table yields zero; connectivity errors are reported without changing data.

No live Amazon provider, scheduled email, purchase execution, or paid Keepa integration is activated. The 24 navigation buttons remain unchanged.

Replace `app.py`, add `neon_readiness.py`, `tests/test_neon_readiness.py`, and `NEON_READINESS_FIX_README.md`.
