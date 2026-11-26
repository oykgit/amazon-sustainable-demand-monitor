"""Staging-only integration tests; no production endpoints or credentials."""
import csv
import io
import json
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from urllib.error import HTTPError
import pytest
import authorized_provider
import automated_research_report as report
import commercial_intelligence
import dashboard_commercial
import brevo_reporting
import controlled_ingestion as ingestion
from controlled_collection import COLUMNS
from restoration_guard import (assess_restore, ExternalManifest, Obligation,
                               Reconciliation, RestorationError)

ENV = {'BREVO_API_KEY':'synthetic-only', 'BREVO_SENDER_EMAIL':'sender@example.invalid',
       'REPORT_RECIPIENT_EMAIL':'recipient@example.invalid'}
APPROVAL = 'I APPROVE THIS CSV INGESTION'

@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    for key in ('DATABASE_URL','DATABASE_READER_URL','DATABASE_INGESTION_URL','DATABASE_ADMIN_URL',
                'EBAY_CLIENT_ID','EBAY_CLIENT_SECRET','BREVO_API_KEY','BREVO_SENDER_EMAIL','REPORT_RECIPIENT_EMAIL'):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv('COMMERCIAL_STORAGE_MODE','secure')
    monkeypatch.setenv('AUTHORIZED_FEED_HOST','example.invalid')
    monkeypatch.setenv('AUTHORIZED_FEED_PERMISSION_REF','PERM-1')
    def deny(*args, **kwargs):
        raise AssertionError('Unexpected external transport')
    monkeypatch.setattr(authorized_provider,'fetch_public_https',deny)
    monkeypatch.setattr(brevo_reporting,'urlopen',deny)


def row(**changes):
    data=dict(asin='ZZTEST0001',marketplace='UK',observed_at_utc='2025-01-01T12:00:00Z',
              selling_price_eur='20',supplier_cost_eur='8',referral_pct='15',fulfilment_eur='3',
              inbound_eur='1',other_eur='0',returns_pct='3',source_note='Authorized commercial feed',
              source_url='https://example.invalid/dp/ZZTEST0001',authorization_reference='PERM-1')
    return dict(data,**changes)


def preview(data):
    return authorized_provider.collect('https://example.invalid/feed','example.invalid','Synthetic','PERM-1',
        fetcher=lambda _:json.dumps({'observations':[data]}).encode())


def csv_bytes(data):
    out=io.StringIO(); writer=csv.DictWriter(out,fieldnames=COLUMNS);writer.writeheader();writer.writerow(data)
    return out.getvalue().encode()


def deliver(summary, opener):
    assessment=commercial_intelligence.assess(summary)
    assert assessment['verified_commercial_opportunities']==0
    rows=dashboard_commercial.display_rows(assessment)
    assert all(r['Verified buy recommendation'] is False for r in rows)
    body=json.dumps({'synthetic_test_only':True,'assessment':assessment},allow_nan=False)
    return brevo_reporting.send_report('Synthetic staging report',body,env=ENV,opener=opener)


class Response:
    def __enter__(self): return self
    def __exit__(self,*args): return False
    status = 201
    def read(self, size=-1): return b'{"messageId":"synthetic-message"}'


def fake_delivery(request, timeout):
    assert request.full_url==brevo_reporting.API_URL and timeout==15
    payload=json.loads(request.data)
    assert payload['to']==[{'email':'recipient@example.invalid'}]
    body=json.loads(payload['textContent'])
    assert body['synthetic_test_only'] is True
    assert body['assessment']['products'][0]['scenario_profit_eur']==4.4
    assert 'private@example.invalid' not in payload['textContent']
    return Response()


def test_collection_to_report_to_simulated_delivery():
    data=row(); result=preview(data)
    assert result['accepted']==1 and result['rejected']==0
    prepared=ingestion.prepare_feed(csv_bytes(data))
    snapshot=prepared['rows'][0][0]
    summary=report.summarize([snapshot],[dict(snapshot,name='private@example.invalid')],[])
    assert not summary['verified_demand']
    assert deliver(summary,fake_delivery)['message_id']=='synthetic-message'


def test_invalid_provider_row_cannot_ingest():
    data=row(supplier_cost_eur='-1')
    assert preview(data)['rejected']==1
    with pytest.raises(ValueError): ingestion.prepare_feed(csv_bytes(data))


def test_delivery_rejection_not_success():
    summary=report.summarize([ingestion.prepare_feed(csv_bytes(row()))['rows'][0][0]],[],[])
    def rejected(request,timeout):
        raise HTTPError(request.full_url,401,'rejected',{},io.BytesIO(b'{"code":"unauthorized"}'))
    with pytest.raises(RuntimeError,match='HTTP 401'): deliver(summary,rejected)


def test_restore_reconciliation_requires_actual_zero_in_synthetic_store():
    t=datetime(2025,1,1,tzinfo=timezone.utc); key='a'*64
    manifest=ExternalManifest('synthetic',t,t+timedelta(hours=3),(Obligation(key,t+timedelta(hours=1)),))
    restored={key:['synthetic-record']}
    def check():
        return assess_restore(restore_id='synthetic',restored_to=t,restored_at=t+timedelta(hours=2),
            checked_at=t+timedelta(hours=3),manifest=manifest,
            reconciliations=(Reconciliation(key,t+timedelta(hours=3),len(restored.get(key,[]))),),
            inventory_verified=True,external_stores_verified=True,ingestion_suspended=True)
    with pytest.raises(RestorationError): check()
    restored.pop(key)
    assert check()['production_resume_authorized'] is False


@pytest.mark.skipif(os.getenv('PHASE2U_LOCAL_PG')!='1',reason='Disposable CI PostgreSQL required')
def test_secure_database_collection_to_delivery():
    import psycopg
    import price_history, asin_store, research_watchlist
    from secure_database import database_transaction, DatabaseAccessError
    params=dict(host='127.0.0.1',port=5432,dbname='phase2u_test',user='phase2u_admin',password='local_test_only',sslmode='disable',connect_timeout=5)
    with psycopg.connect(**params) as conn:
        assert conn.execute('SELECT current_database()').fetchone()[0]=='phase2u_test'
        conn.execute('CREATE ROLE u_reader LOGIN PASSWORD \'reader_test_only\'')
        conn.execute('CREATE ROLE u_writer LOGIN PASSWORD \'writer_test_only\'')
        conn.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
        for module in (price_history,asin_store,research_watchlist): module._init(conn)
        conn.execute('''CREATE TABLE asin_price_feed_provenance (asin text, marketplace text, observed_at_utc text,
            source_note text, source_url text NOT NULL, authorization_reference text NOT NULL, feed_sha256 text NOT NULL,
            PRIMARY KEY(asin,marketplace,observed_at_utc,source_note))''')
        conn.execute('GRANT USAGE ON SCHEMA public TO u_reader,u_writer')
        conn.execute('GRANT SELECT ON ALL TABLES IN SCHEMA public TO u_reader,u_writer')
        conn.execute('GRANT INSERT ON asin_price_snapshots,asin_price_feed_provenance TO u_writer')
        conn.execute('GRANT USAGE ON SEQUENCE asin_price_snapshots_id_seq TO u_writer')
    def local(role,environ=None):
        assert role in ('reader','ingestion')
        return dict(params,user='u_reader' if role=='reader' else 'u_writer',password='reader_test_only' if role=='reader' else 'writer_test_only')
    with patch('secure_database.connection_parameters',side_effect=local):
        data=row(); assert preview(data)['accepted']==1
        raw=csv_bytes(data); digest=ingestion.prepare_feed(raw)['sha256']
        assert ingestion.ingest_approved_feed(raw,digest,APPROVAL)['inserted']==1
        assert ingestion.ingest_approved_feed(raw,digest,APPROVAL)['duplicates_skipped']==1
        with database_transaction('reader') as conn:
            assert conn.execute('SELECT count(*) FROM asin_price_feed_provenance WHERE feed_sha256=%s',(digest,)).fetchone()[0]==1
        with pytest.raises(DatabaseAccessError):
            with database_transaction('ingestion') as conn: conn.execute('DELETE FROM asin_price_snapshots')
        summary=report.run(); assert summary['products_count']==1
        assert deliver(summary,fake_delivery)['accepted'] is True
