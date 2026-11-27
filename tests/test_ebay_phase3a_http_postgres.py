"""Real loopback HTTP + synthetic signature + disposable PostgreSQL only."""
from test_ebay_phase2r_e2e import (db, signing, seed, count_records, make_body,
    sign_body, new_notification_id, erase_authenticated_account, ledger_count)
from test_ebay_phase3a_http_bridge import staging
from test_ebay_phase2q_webhook import request, PATH


def test_http_commit_and_duplicate(db, signing):
    private, keys = signing
    seed(db,'synthetic-account-A',3); seed(db,'synthetic-account-B',2)
    body = make_body(new_notification_id()); header = sign_body(private,body)
    with staging(connection=db, erase=erase_authenticated_account,key_client=keys,inventory_approved=True) as port:
        assert request(port,'POST',PATH,body=body,headers={'X-EBAY-SIGNATURE':header})[0] == 200
        assert count_records(db,'synthetic-account-A') == 0
        assert count_records(db,'synthetic-account-B') == 2
        seed(db,'synthetic-account-A',1)
        assert request(port,'POST',PATH,body=body,headers={'X-EBAY-SIGNATURE':header})[0] == 200
        assert count_records(db,'synthetic-account-A') == 1


def test_http_rollback_and_retry(db, signing):
    private, keys = signing
    seed(db,'synthetic-account-A',3)
    body = make_body(new_notification_id()); header = sign_body(private,body)
    def fail(cur,event):
        erase_authenticated_account(cur,event)
        raise RuntimeError('synthetic fault')
    with staging(connection=db,erase=fail,key_client=keys,inventory_approved=True) as port:
        assert request(port,'POST',PATH,body=body,headers={'X-EBAY-SIGNATURE':header})[0] == 503
    assert count_records(db,'synthetic-account-A') == 3
    with staging(connection=db,erase=erase_authenticated_account,key_client=keys,inventory_approved=True) as port:
        assert request(port,'POST',PATH,body=body,headers={'X-EBAY-SIGNATURE':header})[0] == 200
    assert count_records(db,'synthetic-account-A') == 0


def test_http_tampering_no_write(db, signing):
    private, keys = signing
    seed(db,'synthetic-account-A',3)
    body = make_body(new_notification_id()); header = sign_body(private,body)
    before = ledger_count(db)
    with staging(connection=db,erase=erase_authenticated_account,key_client=keys,inventory_approved=True) as port:
        assert request(port,'POST',PATH,body=body+b' ',headers={'X-EBAY-SIGNATURE':header})[0] == 412
    assert count_records(db,'synthetic-account-A') == 3
    assert ledger_count(db) == before
