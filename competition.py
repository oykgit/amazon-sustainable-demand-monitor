"""Conservative, operator-supplied competition snapshot analysis; no network calls."""
import pandas as pd

REQUIRED_COMPETITION = ['market','asin','observed_at','competing_listings','median_competitor_price_eur','median_review_count','source','notes']

def assess_competition(df: pd.DataFrame) -> pd.DataFrame:
    missing = set(REQUIRED_COMPETITION) - set(df.columns)
    if missing:
        raise ValueError('Missing columns: ' + ', '.join(sorted(missing)))
    d = df.copy()
    if d.empty:
        return pd.DataFrame(columns=['market','asin','observed_at','competing_listings','median_competitor_price_eur','median_review_count','competition_pressure','source','notes'])
    d['market'] = d['market'].astype(str).str.strip().str.upper()
    if not d['market'].isin(['UK','IE']).all():
        raise ValueError('market must be UK or IE')
    d['asin'] = d['asin'].astype(str).str.strip()
    if d['asin'].eq('').any() or d['asin'].eq('nan').any():
        raise ValueError('ASIN cannot be blank')
    dt = pd.to_datetime(d['observed_at'], errors='coerce')
    if dt.isna().any():
        raise ValueError('observed_at must contain valid dates')
    d['observed_at'] = dt.dt.strftime('%Y-%m-%d')
    for field in ['competing_listings','median_competitor_price_eur','median_review_count']:
        d[field] = pd.to_numeric(d[field], errors='coerce')
        if d[field].isna().any() or (d[field] < 0).any():
            raise ValueError(field + ' must be a non-negative number')
    for field in ['competing_listings','median_review_count']:
        if (d[field] % 1 != 0).any():
            raise ValueError(field + ' must be an integer')
    if d['source'].fillna('').astype(str).str.strip().eq('').any():
        raise ValueError('source is required for each observation')
    # Heuristic categories, deliberately not a calibrated probability of success.
    def pressure(r):
        if r['competing_listings'] >= 30 or r['median_review_count'] >= 1000:
            return 'HIGH (heuristic)'
        if r['competing_listings'] >= 10 or r['median_review_count'] >= 200:
            return 'MODERATE (heuristic)'
        return 'LOW OBSERVED (heuristic; incomplete coverage possible)'
    d['competition_pressure'] = d.apply(pressure, axis=1)
    return d[['market','asin','observed_at','competing_listings','median_competitor_price_eur','median_review_count','competition_pressure','source','notes']].sort_values(['market','asin','observed_at']).reset_index(drop=True)
