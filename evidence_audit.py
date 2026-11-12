"""Conservative evidence audit of manually documented ASIN price snapshots.

This is descriptive research bookkeeping, not an Amazon demand or buy signal.
"""
from collections import defaultdict
from datetime import datetime, timezone


def _utc(value):
    parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Observation timestamp must include timezone')
    return parsed.astimezone(timezone.utc)


def audit_snapshots(records, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('Audit timestamp must include timezone')
    grouped = defaultdict(list)
    for row in records:
        grouped[(str(row['asin']), str(row['marketplace']))].append(row)
    output = []
    for (asin, market), group in sorted(grouped.items()):
        dates = sorted(_utc(r['observed_at_utc']) for r in group)
        latest = dates[-1]
        age_days = max(0, (now - latest).days)
        span_days = max(0, (latest - dates[0]).days)
        distinct_days = len({d.date() for d in dates})
        notes = [str(r.get('source_note') or '').strip() for r in group]
        latest_row = max(group, key=lambda r: _utc(r['observed_at_utc']))
        issues = []
        if len(group) < 2:
            issues.append('Single price snapshot')
        if distinct_days < 3:
            issues.append('Fewer than 3 distinct observation days')
        if span_days < 30:
            issues.append('Less than 30 days between first and last snapshot')
        if age_days > 30:
            issues.append('Latest observation older than 30 days')
        if not all(notes):
            issues.append('Missing source note')
        if not any('http' in note.lower() or 'reference' in note.lower() or 'invoice' in note.lower() for note in notes):
            issues.append('No traceable URL/reference/invoice in source notes')
        if float(latest_row.get('supplier_cost_eur') or 0) <= 0:
            issues.append('Supplier cost missing or zero')
        if float(latest_row.get('fulfilment_eur') or 0) <= 0:
            issues.append('Fulfilment estimate missing or zero')
        issues.extend(['Amazon unit sales unverified', 'Selling prices operator-entered, not independently verified',
                       'VAT, taxes and unentered expenses not validated', 'Brand/resale permissions unverified'])
        status = 'MORE OBSERVATIONS NEEDED' if distinct_days < 3 or span_days < 30 else 'REVIEW DOCUMENTATION'
        output.append({
            'ASIN': asin, 'Marketplace': market, 'Snapshots': len(group),
            'Distinct observation days': distinct_days, 'History days': span_days,
            'Latest observation (UTC)': latest.strftime('%Y-%m-%d %H:%M'),
            'Age (days)': age_days, 'Evidence status': status,
            'Audit warnings': '; '.join(issues),
        })
    return output
