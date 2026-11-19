"""Automated, public catalogue candidate discovery; no Amazon sales or prices claimed."""
import argparse
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = 'https://openlibrary.org/search.json'
DEFAULT_TOPICS = ('home organisation', 'gardening', 'cookbooks')

def normalize(doc):
    title = str(doc.get('title') or '').strip()
    author = (doc.get('author_name') or ['Unknown author'])
    isbn = next((str(x) for x in doc.get('isbn', []) if len(str(x)) == 13 and str(x).isdigit()), None)
    if not title or not isbn:
        return None
    return {'title': title[:180], 'author': str(author[0])[:120], 'isbn13': isbn,
            'first_publish_year': doc.get('first_publish_year'),
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
    fetch = fetch or urlopen
    leads = []
    errors = []
    seen = set()
    for topic in topics:
        if not str(topic).strip():
            continue
        query = urlencode({'q': topic, 'limit': per_topic, 'fields': 'title,author_name,isbn,first_publish_year'})
        request = Request(API + '?' + query, headers={'User-Agent': 'SustainableDemandMonitor/2.0 (public catalogue research)'})
        try:
            with fetch(request, timeout=20) as response:
                payload = json.loads(response.read().decode('utf-8'))
            for doc in payload.get('docs', [])[:per_topic]:
                item = normalize(doc)
                if item and item['isbn13'] not in seen:
                    seen.add(item['isbn13'])
                    item['discovery_topic'] = topic
                    leads.append(item)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append({'topic': topic, 'error_type': type(exc).__name__,
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
