import json
import pytest
import phase2v_operational as v

class Response:
    def __init__(self,status,body): self.status=status;self.body=body
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def read(self,n): return self.body[:n]

@pytest.mark.parametrize('status,body,expected',[(200,b'{"status":"phase2d_authentication_integrated","post_enabled":false}',True),(200,b'{"post_enabled":true}',False),(200,b'{"status":"phase2d_authentication_integrated","post_enabled":0}',False)])
def test_health(status,body,expected):
    assert v.health(lambda req,timeout:Response(status,body)) is expected

@pytest.mark.parametrize('status,body',[(302,b'{}'),(200,b'[]'),(200,b'x'*65537)])
def test_bad_response(status,body):
    with pytest.raises(ValueError): v.health(lambda req,timeout:Response(status,body))

@pytest.mark.parametrize('body,expected',[(b'{"messageId":"test"}',True),(b'{}',False),(b'{"messageId":true}',False)])
def test_email(body,expected):
    env={'BREVO_API_KEY':'secret','BREVO_SENDER_EMAIL':'a@example.invalid','REPORT_RECIPIENT_EMAIL':'b@example.invalid'}
    def fake(req,timeout):
        assert req.full_url==v.BREVO and req.method=='POST'
        assert json.loads(req.data)['to']==[{'email':'b@example.invalid'}]
        return Response(201,body)
    assert v.email(env,fake) is expected

def test_default_no_calls(monkeypatch):
    def deny(*args): pytest.fail('unexpected call')
    for name in ('health','email','database'): monkeypatch.setattr(v,name,deny)
    assert set(v.run()['checks'].values())=={'NOT_RUN'}

def test_never_authorizes(monkeypatch):
    for name in ('health','email','database'): monkeypatch.setattr(v,name,lambda *a:True)
    r=v.run(hosted=True,mail=True,db=True)
    assert set(r['checks'].values())=={'PASS'} and not r['production_ready'] and not r['post_activation_authorized']

def test_sanitized_failure(monkeypatch):
    def fail(): raise RuntimeError('secret')
    monkeypatch.setattr(v,'health',fail)
    assert 'secret' not in str(v.run(hosted=True))
    assert v.run(hosted=True)['checks']['hosted_health']=='FAIL_OR_UNCONFIRMED'

def test_missing_database():
    with pytest.raises(v.DatabaseAccessError if hasattr(v,'DatabaseAccessError') else RuntimeError): v.database({})

@pytest.mark.parametrize('role,table,expected',[
    ('reader',v.PROVENANCE,(False,False,False,False,False)),
    ('reader',v.WATCHLIST,(True,False,False,False,False)),
    ('ingestion',v.WATCHLIST,(True,True,False,False,True)),
    ('ingestion',v.PROVENANCE,(False,True,False,False,False)),
    ('ingestion','asin_price_snapshots',(False,True,False,False,False)),
])
def test_permission_contract(role,table,expected):
    assert v.expected_table_permissions(role,table)==expected
