import io,json
from urllib.error import HTTPError
from brevo_diagnostic import diagnose
from test_phase2v import Response
ENV={'BREVO_API_KEY':'secret','BREVO_SENDER_EMAIL':'a@example.invalid','REPORT_RECIPIENT_EMAIL':'b@example.invalid'}
def test_success():
    def fake(req,timeout):
        assert req.get_method()=='GET'
        return Response(200,b'{"senders":[{"email":"a@example.invalid","active":true}]}' if req.full_url.endswith('/senders') else b'{}')
    r=diagnose(ENV,fake)
    assert r['sender_status']=='ACTIVE' and not r['email_sent'] and 'example.invalid' not in str(r)
def test_ip():
    def fake(req,timeout):
        raise HTTPError(req.full_url,401,'secret',{},io.BytesIO(b'{"message":"Unauthorized IP address secret"}'))
    r=diagnose(ENV,fake)
    assert r['account']=={'http_status':401,'category':'IP_RESTRICTION_REPORTED'} and 'secret' not in str(r)
def test_missing():
    assert diagnose({},lambda *a: 1)['account']['category']=='MISSING_OR_INVALID_KEY_FORMAT'
def test_generic():
    def fake(req,timeout):
        raise HTTPError(req.full_url,403,'secret',{},io.BytesIO(b'{}'))
    assert diagnose(ENV,fake)['account']['category']=='ACCESS_FORBIDDEN'
