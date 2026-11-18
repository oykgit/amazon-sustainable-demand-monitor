"""Offline bridge between V1.25 normalized Keepa history and V1.24 evidence analysis."""
import hashlib
import json
from keepa_normalizer import normalize
from historical_evidence import analyse


def assess_keepa_payload(product, asin, fx_gbp_to_eur=None, as_of=None):
    """Analyze supplied JSON only; never calls Keepa or writes to Neon.

    Prices require an operator-supplied GBP/EUR rate, and that conversion is
    NOT historically accurate for each date. Amazon prices are preferred to
    NEW prices to prevent merging two price series into one misleading group.
    """
    normalized = normalize(product, asin, fx_gbp_to_eur=fx_gbp_to_eur)
    canonical = json.dumps(product, sort_keys=True, separators=(',', ':'), allow_nan=False)
    digest = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    obs = normalized['observations']
    has_amazon = any(r['source_field'] == 'AMAZON' for r in obs)
    chosen_price = 'AMAZON' if has_amazon else 'NEW'
    rows = []
    skipped = {'gbp_without_fx': 0, 'alternative_price_series': 0}
    for r in obs:
        if r['evidence_type'] == 'SALES_RANK':
            evidence_type, value = 'SALES_RANK', r['value']
        else:
            if r['source_field'] != chosen_price:
                skipped['alternative_price_series'] += 1
                continue
            if 'price_eur_operator_estimate' not in r:
                skipped['gbp_without_fx'] += 1
                continue
            evidence_type, value = 'PRICE_EUR', r['price_eur_operator_estimate']
            if value <= 0:
                skipped['gbp_without_fx'] += 1
                continue
        rows.append({'asin': r['asin'], 'market': r['market'],
                     'observed_date': r['observed_date'],
                     'source_provider': 'Keepa JSON (operator supplied; origin unverified)',
                     'source_reference': f'local-json-sha256:{digest}:{r["source_field"]}',
                     'evidence_type': evidence_type, 'value': value})
    report = analyse(rows, as_of=as_of)
    report['mode'] = 'KEEPA_NORMALIZED_EVIDENCE_OFFLINE_READ_ONLY'
    report['normalization'] = {'normalized_points': len(obs),
        'assessed_points': len(rows), 'skipped': skipped,
        'chosen_price_series': chosen_price,
        'payload_sha256': digest, 'provider_origin_authenticated': False,
        'fx_rate_operator_supplied': fx_gbp_to_eur is not None}
    report['network_requests'] = 0
    report['database_writes'] = 0
    report['purchases_enabled'] = False
    report['historical_demand_verified'] = False
    report['limitations'] = [
        'JSON fingerprint is a local content identifier, NOT proof of Keepa origin.',
        'Sales rank does not establish actual sales units or sustained demand.',
        'A single operator-supplied FX rate across historical dates is illustrative, not date-specific.',
        'Observation counts and month coverage do not authenticate underlying data.',
        'Keepa price history may be sparse and rank samples may not represent continuous demand.',
        'No provider requests, database writes, or purchases occur.']
    return report
