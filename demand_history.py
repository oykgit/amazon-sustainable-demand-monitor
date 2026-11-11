"""Transparent descriptive analytics for observed monthly demand proxies, not sales forecasts."""
import pandas as pd
import numpy as np

FIELDS = ['market', 'asin', 'product', 'month', 'demand_index', 'source']

def analyse_history(frame, as_of=None):
    missing = set(FIELDS) - set(frame.columns)
    if missing:
        raise ValueError('Missing columns: ' + ', '.join(sorted(missing)))
    d = frame.copy()
    d['month'] = pd.to_datetime(d['month'], errors='coerce')
    d['demand_index'] = pd.to_numeric(d['demand_index'], errors='coerce')
    d = d.dropna(subset=['month', 'demand_index', 'market', 'asin'])
    d = d[d.demand_index.between(0, 100)]
    d['month'] = d.month.dt.to_period('M')
    today = pd.Period(as_of, freq='M') if as_of else pd.Timestamp.now().to_period('M')
    start = today - 11
    d = d[(d.month >= start) & (d.month <= today)]
    d['source'] = d['source'].fillna('').astype(str)
    d = d.sort_values('month').drop_duplicates(['market', 'asin', 'month'], keep='last')
    results = []
    for (market, asin), g in d.groupby(['market', 'asin']):
        g = g.sort_values('month')
        values = g.demand_index.to_numpy(dtype=float)
        n = len(g)
        mean = float(np.mean(values))
        cv = float(np.std(values) / mean) if mean > 0 else (0.0 if np.all(values == 0) else float('inf'))
        stability = round(max(0, 100 * (1 - min(cv, 1))), 1)
        early = float(np.mean(values[:min(3, n)]))
        late = float(np.mean(values[-min(3, n):]))
        change = round(late - early, 1) if n >= 6 else None
        spike = bool(n >= 6 and np.max(values) >= max(30, 1.8 * np.median(values)) and np.max(values) - np.median(values) >= 20)
        complete = n == 12
        sourced = bool(g.source.str.strip().ne('').all())
        results.append(dict(market=market, asin=asin, product=str(g.iloc[-1]['product']), months=n,
                            missing_months=', '.join(str(p) for p in pd.period_range(start, today, freq='M') if p not in set(g.month)),
                            mean_demand_index=round(mean, 1), stability_score=stability,
                            recent_change_points=change, possible_spike=spike,
                            full_12_months=complete, sources_recorded=sourced,
                            evidence_status='12 MONTHS OBSERVED (PROXY ONLY)' if complete and sourced else 'INSUFFICIENT HISTORY',
                            interpretation=('CONSISTENT PROXY' if stability >= 70 and not spike else 'VARIABLE / POSSIBLY SEASONAL') if complete and sourced else 'NOT ASSESSABLE'))
    return pd.DataFrame(results)
