"""Read-only, explicit association of ASIN research and Google Trends evidence.

A search keyword is not an ASIN identifier. This module never infers links,
verifies Amazon sales, or issues purchase recommendations.
"""
from collections import defaultdict
from datetime import datetime


def consolidate(comparisons, identities, interest, links=None):
    """Build one row per compared ASIN/market. links maps (ASIN, market) -> keyword.

    Input interest may be a pandas DataFrame or a list of dictionaries.
    """
    links = links or {}
    if hasattr(interest, 'to_dict'):
        interest = interest.to_dict('records')
    identities_by_key = {}
    for item in identities:
        key = (str(item.get('asin','')).upper(), str(item.get('marketplace','')).upper())
        if key not in identities_by_key or str(item.get('observed_at_utc','')) > str(identities_by_key[key].get('observed_at_utc','')):
            identities_by_key[key] = item
    by_keyword = defaultdict(list)
    for item in interest:
        key = (str(item['market']).upper(), str(item['keyword']).strip().casefold())
        by_keyword[key].append(item)
    output = []
    for comparison in comparisons:
        row = dict(comparison)
        key = (str(row['ASIN']).upper(), str(row['Marketplace']).upper())
        identity = identities_by_key.get(key, {})
        row['Product identity (operator recorded)'] = str(identity.get('name') or 'Not recorded')
        row['Identity source URL (unverified)'] = str(identity.get('source_url') or '')
        keyword = str(links.get(key) or '').strip()
        row['Explicitly linked search keyword'] = keyword
        evidence = by_keyword.get((key[1], keyword.casefold()), []) if keyword else []
        months = {str(item['month']) for item in evidence}
        row['Google Trends observed months'] = len(months)
        row['Google Trends average relative interest'] = (round(sum(float(item['search_interest']) for item in evidence) / len(evidence), 2) if evidence else None)
        row['Search interest status'] = ('LINKED: relative web search interest only' if evidence else 'NO EXPLICIT MATCHED INTEREST EVIDENCE')
        row['Amazon sales volume verified'] = False
        row['Sustained Amazon demand verified'] = False
        row['Purchase recommendation'] = 'NOT PROVIDED'
        output.append(row)
    return output
