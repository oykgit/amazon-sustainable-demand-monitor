"""Evidence-gated, non-predictive ASIN research comparison. No buy signals."""
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

def compare_snapshots(records, competition=None):
    grouped = defaultdict(list)
    for r in records:
        grouped[(str(r['asin']), str(r['marketplace']))].append(r)
    output = []
    competition = competition or {}
    for (asin, market), rows in sorted(grouped.items()):
        rows = sorted(rows, key=lambda x: str(x['observed_at_utc']))
        latest = rows[-1]
        prices = [float(r['selling_price_eur']) for r in rows]
        profit = float(latest['estimated_profit_eur'])
        cost = float(latest['supplier_cost_eur'])
        roi = None if latest['estimated_roi_pct'] is None else float(latest['estimated_roi_pct'])
        span = (datetime.fromisoformat(str(rows[-1]['observed_at_utc']).replace('Z','+00:00')) - datetime.fromisoformat(str(rows[0]['observed_at_utc']).replace('Z','+00:00'))).days if len(rows)>1 else 0
        variation = (max(prices)-min(prices))/max(prices)*100 if max(prices)>0 else 0
        # Explicit heuristic subscores. Never equate these with verified demand.
        profit_score = 0 if profit<=0 else 15 if profit<5 else 25 if profit<10 else 35
        roi_score = 0 if roi is None or roi<=0 else 5 if roi<20 else 10 if roi<50 else 15
        history_score = 0 if len(rows)<2 else 5 if span<30 else 10 if span<90 else 15
        stability_score = 0 if len(rows)<2 else 15 if variation<=5 else 8 if variation<=15 else 0
        comp = competition.get((asin,market))
        comp_score = 0 if comp is None else 10 if comp=='low' else 5 if comp=='medium' else 0
        score = profit_score+roi_score+history_score+stability_score+comp_score
        warnings=[]
        if len(rows)<2: warnings.append('Only one price observation')
        elif span<30: warnings.append('Less than 30 days of price history')
        if variation>15: warnings.append('Observed price range exceeds 15%')
        if profit<=0: warnings.append('Estimated profit is not positive')
        if roi is None: warnings.append('ROI unavailable (zero supplier cost)')
        if comp is None: warnings.append('Competition not assessed')
        warnings.extend(['No verified Amazon unit sales', 'VAT/taxes and unentered fees excluded', 'Supplier/brand restrictions not verified'])
        output.append({'ASIN':asin,'Marketplace':market,'Snapshots':len(rows),'History days':span,
            'Latest price (€)':round(prices[-1],2),'Latest profit estimate (€)':round(profit,2),
            'Latest ROI estimate (%)':None if roi is None else round(roi,2),
            'Observed price range (%)':round(variation,1), 'Competition (manual)':comp or 'unknown',
            'Research completeness score / 90':score, 'Evidence level':'LIMITED: operator-entered only',
            'Warnings':'; '.join(warnings)})
    return output
