"""Read-only commercial dashboard view of Neon evidence, using Stage 2B assessment."""
from automated_research_report import run
from commercial_intelligence import assess


def load_dashboard():
    """Read latest stored observations, without writes or external provider calls."""
    return assess(run())


def display_rows(report):
    rows = []
    for product in report.get('products', []):
        rows.append({
            'ASIN': product.get('asin'),
            'Market': product.get('marketplace'),
            'Product': product.get('name') or 'Unknown',
            'Estimated profit (EUR)': product.get('scenario_profit_eur'),
            'Estimated ROI (%)': product.get('scenario_roi_pct'),
            'Research priority': product.get('research_priority'),
            'Evidence gaps': '; '.join(product.get('evidence_gaps') or []),
            'Verified buy recommendation': False,
        })
    return rows
