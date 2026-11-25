"""Automated, public catalogue candidate discovery; no Amazon sales or prices claimed."""
import argparse
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request
from authorized_provider import fetch_public_https, unique_object
from commercial_privacy import barcode, PrivacyError
import re

API = 'https://openlibrary.org/search.json'
DEFAULT_TOPICS = ('home organisation', 'gardening', 'cookbooks')

def normalize(doc):
    if type(doc) is not dict:
        return None
    title = doc.get('title')
    if type(title) is not str or not title.strip() or len(title)>180 or not title.isprintable() or '@' in title or '://' in title:
        return None
    isbn = None
    for value in doc.get('isbn', []) if isinstance(doc.get('isbn'), list) else []:
        try:
            if type(value) is str and len(value)==13 and value.startswith(('978','979')):
                isbn = barcode(value)
                break
        except PrivacyError:
            continue
    if not isbn:
        return None
    year = doc.get('first_publish_year')
    if type(year) is not int or not 1 <= year <= datetime.now(timezone.utc).year:
        year = None
    return {'title': title.strip(), 'author': 'Not retained', 'isbn13': isbn,
            'first_publish_year': year,
            'catalogue_source': 'Open Library', 'amazon_asin': None,
            'amazon_price_verified': False, 'amazon_sales_verified': False,
            'supplier_cost_verified': False, 'estimated_profit_eur': None,
            'roi_pct': None, 'buy_recommendation': False,
            'research_status': 'CATALOGUE_LEAD_ONLY'}

def discover(topics=DEFAULT_TOPICS, per_topic=8, fetch=None):
    if not 1 <= per_topic <= 20:
        raise ValueError('per_topic must be between 1 and 20')
    if len(topics) > 10:
        raise ValueError('Too many topics')
    leads = []
    errors = []
    seen = set()
    for topic in topics:
        if type(topic) is not str or not re.fullmatch(r'[A-Za-z][A-Za-z -]{0,59}', topic):
            errors.append({'message':'INVALID_TOPIC'})
            continue
        query = urlencode({'q': topic, 'limit': per_topic, 'fields': 'title,isbn,first_publish_year'})
        request = Request(API + '?' + query, headers={'User-Agent': 'SustainableDemandMonitor/2.0 (public catalogue research)'})
        try:
            if fetch is None:
                raw = fetch_public_https(request.full_url, 'openlibrary.org', 1000000)
            else:
                with fetch(request, timeout=20) as response:
                    raw = response.read(1000001)
            if len(raw)>1000000:
                raise ValueError('RESPONSE_LIMIT')
            payload = json.loads(raw, object_pairs_hook=unique_object)
            if type(payload) is not dict or type(payload.get('docs')) is not list:
                raise ValueError('INVALID_CATALOGUE')
            for doc in payload['docs'][:per_topic]:
                item = normalize(doc)
                if item and item['isbn13'] not in seen:
                    seen.add(item['isbn13'])
                    item['discovery_topic'] = 'Configured catalogue topic'
                    leads.append(item)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append({'error_type': type(exc).__name__,
                           'message': 'Catalogue request failed; no fallback or fabricated data'})
    return {'mode': 'AUTOMATED_PUBLIC_CATALOGUE_DISCOVERY_READ_ONLY',
            'generated_at_utc': datetime.now(timezone.utc).isoformat(),
            'provider': 'Open Library public search API', 'marketplace': 'NOT_VERIFIED',
            'lead_count': len(leads), 'leads': leads, 'errors': errors,
            'amazon_requests': 0, 'database_writes': 0, 'purchases_enabled': False,
            'verified_amazon_demand': False, 'profit_recommendations': 0,
            'warning': 'Book catalogue discovery only; no Amazon UK/IE demand, listing eligibility, sourcing, price or profit validation.'}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='automatic_candidate_discovery.json')
    args = parser.parse_args()
    topics = tuple(x.strip() for x in os.getenv('DISCOVERY_TOPICS', ','.join(DEFAULT_TOPICS)).split(',') if x.strip())
    report = discover(topics=topics)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print(f"Public catalogue leads: {report['lead_count']}; failed topics: {len(report['errors'])}; no Amazon demand verified")
    if report['errors'] and not report['leads']:
        raise SystemExit('No live catalogue results; report retained with failure details')

if __name__ == '__main__':
    main()
