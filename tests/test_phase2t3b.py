import pytest

@pytest.fixture(autouse=True)
def synthetic_feed_policy(monkeypatch):
    monkeypatch.setenv('AUTHORIZED_FEED_HOST','example.org')
    monkeypatch.setenv('AUTHORIZED_FEED_PERMISSION_REF','PERM-1')

import json
import pytest
from unittest.mock import patch
from authorized_provider import validate_payload, _public_addresses
from controlled_collection import inspect_csv
from automatic_candidate_discovery import normalize
from controlled_ingestion import ingest_approved_feed, prepare_feed
from test_controlled_ingestion import sample


def test_extra_csv_header():
    raw=sample().decode().splitlines()
    with pytest.raises(ValueError, match='UNAPPROVED_SCHEMA'):
        inspect_csv(raw[0]+',username\n'+raw[1]+',private\n')


def test_unknown_json_field():
    import csv, io
    row=next(csv.DictReader(io.StringIO(sample().decode())))
    row['username']='private'
    report=validate_payload(json.dumps({'observations':[row]}).encode(),'p','PERM-1','example.org')
    assert report['rejected']==1 and 'private' not in json.dumps(report)


def test_duplicate_json_key():
    with pytest.raises(ValueError):
        validate_payload(b'{"observations":[],"observations":[]}', 'p','PERM-1')


def test_private_dns():
    with patch('authorized_provider.socket.getaddrinfo', return_value=[(0,0,0,'',('127.0.0.1',443))]):
        with pytest.raises(ValueError): _public_addresses('example.org')


def test_catalogue_minimization():
    row={'title':'Book','isbn':['9780140328721'],'author_name':['private']}
    assert normalize(row)['author']=='Not retained'
    assert normalize(dict(row,isbn=['9780140328722'])) is None
    assert normalize(dict(row,title='private@example.org')) is None


def test_secure_ingestion_no_ddl(monkeypatch):
    from unittest.mock import MagicMock
    from contextlib import contextmanager
    monkeypatch.setenv('COMMERCIAL_STORAGE_MODE','secure')
    conn=MagicMock(); cur=conn.cursor.return_value.__enter__.return_value; cur.rowcount=1
    @contextmanager
    def transaction(role,url):
        assert role=='ingestion'
        yield conn
    with patch('controlled_ingestion.storage_transaction',transaction):
        raw=sample(); result=ingest_approved_feed(raw,prepare_feed(raw)['sha256'],'I APPROVE THIS CSV INGESTION')
    assert result['inserted']==1
    assert len(cur.execute.call_args_list)==2
    assert all('CREATE' not in c.args[0] for c in cur.execute.call_args_list)
