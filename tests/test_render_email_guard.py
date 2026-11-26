import pytest
import render_email_guard as g
TOKEN='a'*64
ENV={'EMAIL_TEST_OPERATOR_TOKEN':TOKEN}
GOOD={'account':{'category':'PASS'},'senders':{'category':'PASS'},'sender_status':'ACTIVE','configuration':dict(key_present=True,sender_format_valid=True,recipient_format_valid=True)}
@pytest.fixture(autouse=True)
def reset(monkeypatch):
    monkeypatch.setattr(g,'_attempted',False)
    monkeypatch.setattr(g,'diagnose',lambda env: GOOD)
    monkeypatch.setattr(g,'send_report',lambda *a,**k: {'accepted':True})
@pytest.mark.parametrize('token,env', [('',ENV),('b'*64,ENV),(TOKEN,{}),('short',{'EMAIL_TEST_OPERATOR_TOKEN':'short'})])
def test_denied(token,env):
    with pytest.raises(PermissionError): g.verify(token,env)
    with pytest.raises(PermissionError): g.send_test(token,True,env)
def test_confirm():
    with pytest.raises(PermissionError): g.send_test(TOKEN,1,ENV)
def test_once():
    assert g.verify(TOKEN,ENV)==GOOD
    assert g.send_test(TOKEN,True,ENV)['status']=='ACCEPTED'
    assert g.send_test(TOKEN,True,ENV)['status']=='ATTEMPT_ALREADY_USED'
def test_preflight(monkeypatch):
    monkeypatch.setattr(g,'diagnose',lambda env: {})
    assert g.send_test(TOKEN,True,ENV)['status']=='PREFLIGHT_FAILED'
    assert not g._attempted
def test_ambiguous(monkeypatch):
    def fail(*a,**k): raise RuntimeError('private')
    monkeypatch.setattr(g,'send_report',fail)
    assert g.send_test(TOKEN,True,ENV)=={'status':'UNCONFIRMED'}
    assert g.send_test(TOKEN,True,ENV)['status']=='ATTEMPT_ALREADY_USED'
