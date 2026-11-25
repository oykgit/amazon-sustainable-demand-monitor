"""V1.18 opt-in HTTPS JSON feed collector. Dry-run only; no database writes."""
import hashlib
import http.client
import ssl
import re
import ipaddress
import json
import os
import socket
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlsplit
from controlled_collection import COLUMNS, MAX_ROWS, inspect_csv
import csv
import io

MAX_RESPONSE_BYTES = 1_000_000


def _validated_endpoint(url, allowed_host):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.fragment or parsed.query or parsed.port not in (None, 443):
        raise ValueError('HTTPS endpoint without credentials, fragments or nonstandard ports required')
    host = (parsed.hostname or '').lower().rstrip('.')
    allowed = allowed_host.strip().lower().rstrip('.')
    if not allowed or host != allowed or host in ('localhost',) or not host or len(url)>1000:
        raise ValueError('Endpoint host must exactly match configured allowed host')
    try:
        ipaddress.ip_address(host)
        raise ValueError('IP-literal hosts are prohibited')
    except ValueError as exc:
        if str(exc) == 'IP-literal hosts are prohibited': raise
    if not re.fullmatch(r"[a-z0-9]+(?:[.-][a-z0-9]+)+", host) or any(ord(c)<33 for c in url):
        raise ValueError("INVALID_ENDPOINT")
    return host


def _public_addresses(host):
    addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    if not addresses: raise ValueError('No DNS addresses returned')
    for entry in addresses:
        addr=ipaddress.ip_address(entry[4][0])
        if not addr.is_global: raise ValueError('Provider resolves to a non-public address')
    return addresses[0][4][0]


def fetch_public_https(endpoint, host, limit):
    # Connect to the checked address, retaining hostname for TLS and Host header.
    address = _public_addresses(host)
    conn = http.client.HTTPSConnection(host, timeout=12, context=ssl.create_default_context())
    conn._create_connection = lambda target, timeout, source_address=None: socket.create_connection((address, 443), timeout, source_address)
    try:
        parsed = urlsplit(endpoint)
        path = parsed.path or '/'
        if parsed.query:
            path += '?' + parsed.query
        conn.request('GET', path, headers={'Accept':'application/json','Accept-Encoding':'identity','User-Agent':'AmazonResearchMonitor/2T3B'})
        response = conn.getresponse()
        if response.status != 200 or response.getheader('Content-Encoding','identity').lower() != 'identity':
            raise ValueError('PROVIDER_RESPONSE_REJECTED')
        payload = response.read(limit+1)
        if len(payload)>limit:
            raise ValueError('RESPONSE_LIMIT')
        return payload
    finally:
        conn.close()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def validate_payload(payload, provider, authorization_reference, allowed_host=None):
    if not provider.strip() or not authorization_reference.strip():
        raise ValueError('Provider name and permission reference required')
    if len(payload)>MAX_RESPONSE_BYTES: raise ValueError('Provider response exceeds 1 MB')
    try: data=json.loads(payload, object_pairs_hook=unique_object)
    except (ValueError,UnicodeError) as exc: raise ValueError('Provider response must be JSON') from exc
    if not isinstance(data,dict) or set(data) != {'observations'} or not isinstance(data.get('observations'),list):
        raise ValueError('Expected JSON object with observations array')
    observations=data['observations']
    if len(observations)>MAX_ROWS: raise ValueError('Provider exceeds 250-row quota')
    if not all(isinstance(row,dict) for row in observations): raise ValueError('Observation must be an object')
    stream=io.StringIO(); writer=csv.DictWriter(stream,fieldnames=COLUMNS,extrasaction='ignore');writer.writeheader()
    for row in observations:
        if set(row) != set(COLUMNS) or any(type(v) not in (str,int,float) for v in row.values()):
            writer.writerow({})
        else:
            writer.writerow(row)
    result=inspect_csv(stream.getvalue().encode('utf-8'), allowed_host=allowed_host, approved_reference=authorization_reference)
    return {'mode':'AUTHORIZED_PROVIDER_DRY_RUN_ONLY','provider':'Configured authorized feed',
            'checked_at_utc':datetime.now(timezone.utc).isoformat(),'payload_sha256':hashlib.sha256(payload).hexdigest(),
            'records_seen':result['records_seen'],'accepted':result['accepted'],'rejected':result['rejected'],
            'rejected_rows':result['rejected_rows'],'accepted_rows':result['accepted_rows'],
            'database_writes':0,'purchases_enabled':False,'amazon_sales_verified':False,
            'note':'Provider and permission are configured by operator, not independently verified. No automatic ingestion.'}


def collect(endpoint=None, allowed_host=None, provider=None, authorization_reference=None, *, fetcher=None):
    endpoint=endpoint or os.getenv('AUTHORIZED_FEED_URL','')
    allowed_host=allowed_host or os.getenv('AUTHORIZED_FEED_HOST','')
    provider=provider or os.getenv('AUTHORIZED_FEED_PROVIDER','')
    authorization_reference=authorization_reference or os.getenv('AUTHORIZED_FEED_PERMISSION_REF','')
    if not all([endpoint,allowed_host,provider,authorization_reference]):
        return {'mode':'AUTHORIZED_PROVIDER_DRY_RUN_ONLY','status':'NOT_CONFIGURED','network_requests':0,
                'database_writes':0,'purchases_enabled':False,'note':'Set authorized endpoint, exact host, provider and permission reference.'}
    host=_validated_endpoint(endpoint,allowed_host)
    if not re.fullmatch(r'PERM-[0-9]{1,12}', authorization_reference):
        raise ValueError('INVALID_PERMISSION_POLICY')
    if fetcher is None:
        payload=fetch_public_https(endpoint, host, MAX_RESPONSE_BYTES)
    else:
        payload=fetcher(endpoint)
    if isinstance(payload,str):payload=payload.encode('utf-8')
    report=validate_payload(payload,provider,authorization_reference,host)
    report['network_requests']=1
    report['status']='PREVIEW_COMPLETE'
    return report


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='authorized_provider_report.json')
    args=parser.parse_args()
    try: report=collect()
    except Exception as exc:
        report={'mode':'AUTHORIZED_PROVIDER_DRY_RUN_ONLY','status':'FAILED','error_type':type(exc).__name__,
                'note':'Provider collection failed. No records saved.','database_writes':0,'purchases_enabled':False}
    with open(args.output,'w',encoding='utf-8') as f:json.dump(report,f,indent=2)
    print(json.dumps({k:v for k,v in report.items() if k not in ('accepted_rows','rejected_rows')},indent=2))
    if report['status']=='FAILED':raise SystemExit(1)
