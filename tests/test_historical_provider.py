from historical_provider import preview_keepa
import json
class Response:
    status=200
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def read(self, n): return json.dumps({'products':[{'asin':'B008S8RJKK','title':'Example','csv':[1,2]}], 'tokensLeft':10}).encode()
def test_default_no_network():
    assert preview_keepa('B008S8RJKK',environ={})['status']=='NOT_CONFIGURED'
def test_bad_asin():
    assert preview_keepa('invalid!',environ={})['status']=='INVALID_ASIN'
def test_unsupported_market():
    assert preview_keepa('B008S8RJKK',market='IE',environ={})['status']=='UNSUPPORTED_MARKET'
def test_one_request():
    calls=[]
    def opener(request,timeout):
        calls.append((request.full_url,timeout)); return Response()
    r=preview_keepa('B008S8RJKK',environ={'KEEPA_API_KEY':'testkey','RESEARCH_PROVIDER_NETWORK_ENABLED':'true','RESEARCH_PROVIDER_MAX_DAILY_REQUESTS':'1'},opener=opener)
    assert r['status']=='PRODUCT_FOUND' and r['database_writes']==0 and not r['historical_demand_verified']
    assert len(calls)==1 and 'domain=2' in calls[0][0]
    assert 'testkey' not in str(r)
