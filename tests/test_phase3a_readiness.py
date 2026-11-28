from contextlib import contextmanager
from unittest.mock import MagicMock
import pytest
from phase3a_readiness import inventory, run, SQL

def fixture(rows, identity=('monitor_reader','on')):
    conn=MagicMock(); cur=conn.cursor.return_value.__enter__.return_value
    cur.fetchone.return_value=identity; cur.fetchall.return_value=rows
    @contextmanager
    def tx(role):
        assert role=='reader'
        yield conn
    return tx,cur

def test_inventory():
    tx,cur=fixture([('public','ledger','r','fingerprint','text',False,False),('public','ledger','r','status','text',False,False)])
    result=inventory(tx)
    assert len(result)==1 and len(result[0]['columns'])==2
    assert result[0]['reader_select'] is False
    assert cur.execute.call_args.args==(SQL,)

@pytest.mark.parametrize('identity',[('admin','on'),('monitor_reader','off')])
def test_wrong_session(identity):
    tx,cur=fixture([],identity)
    with pytest.raises(ValueError): inventory(tx)
    cur.fetchall.assert_not_called()

def test_delete_permission():
    tx,_=fixture([('public','ledger','r','id','text',True,True)])
    with pytest.raises(ValueError): inventory(tx)

def test_empty():
    tx,_=fixture([])
    with pytest.raises(ValueError): inventory(tx)

def test_default_no_io():
    def forbidden(): raise AssertionError('unexpected call')
    r=run(inventory_fn=forbidden,client_factory=forbidden)
    assert r['inventory_status']==r['oauth_status']=='NOT_RUN'
    assert not r['production_ready'] and not r['post_activation_authorized']

def test_success_not_approval():
    class Client:
        def _access_token(self): return 'secret-token'
    r=run(db=True,oauth=True,inventory_fn=lambda:[{'table':'test'}],client_factory=Client)
    assert r['oauth_status']=='PASS_TOKEN_ISSUED'
    assert r['inventory_status']=='METADATA_COLLECTED_REVIEW_REQUIRED'
    assert 'secret-token' not in str(r)
    for k in ('production_ready','post_activation_authorized','browse_collection_authorized','storage_inventory_approved','restoration_enforcement_verified','live_signature_verified'): assert r[k] is False
    assert r['database_writes']==0

def test_error_redaction():
    def fail(): raise RuntimeError('private credential')
    r=run(db=True,oauth=True,inventory_fn=fail,client_factory=fail)
    assert r['inventory_status']==r['oauth_status']=='FAIL_OR_UNCONFIRMED'
    assert 'private credential' not in str(r)
