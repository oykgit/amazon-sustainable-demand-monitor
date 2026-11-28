import pytest
from phase3c_browse import search_request, summarize_fixture, classify_status, demo

@pytest.mark.parametrize('market,header', [('UK','EBAY_GB'),('IE','EBAY_IE')])
def test_market(market,header):
    r=search_request(market=market,keyword='storage box')
    assert r['headers']['X-EBAY-C-MARKETPLACE-ID']==header
    assert 'q=storage+box' in r['url']
    assert 'Authorization' not in r['headers']

def test_gtin():
    assert 'gtin=9780140328721' in search_request(market='UK',gtin='9780140328721')['url']

@pytest.mark.parametrize('kw', ['','https://bad.example','x\nX','x'*81])
def test_invalid_keyword(kw):
    with pytest.raises(ValueError): search_request(market='UK',keyword=kw)

@pytest.mark.parametrize('limit',[0,21,True])
def test_limit(limit):
    with pytest.raises(ValueError): search_request(market='UK',keyword='box',limit=limit)

def test_exclusive():
    with pytest.raises(ValueError): search_request(market='UK',keyword='box',gtin='9780140328721')

def test_demo():
    r=demo(); assert r['minimum_asking_price']=='12.50'; assert r['shipping_quote_present_count']==1
    assert not r['browse_collection_authorized'] and r['browse_requests']==r['database_writes']==0
    assert not r['purchase_recommendation'] and not r['demand_verified']

def row():
    return {'itemId':'v1|123|0','buyingOptions':['FIXED_PRICE'],'price':{'value':'12.50','currency':'GBP'},'seller':{'username':'private-test'},'title':'private-test','itemWebUrl':'private-test'}

def test_privacy_duplicate():
    r=summarize_fixture({'itemSummaries':[row(),row()]},'UK'); assert r['valid_price_count']==1; assert 'private-test' not in str(r); assert r['shipping_quote_present_count']==0

@pytest.mark.parametrize('value',['NaN','-1','Infinity','0','1e3'])
def test_bad_price(value):
    x=row(); x['price']['value']=value; assert summarize_fixture({'itemSummaries':[x]},'UK')['valid_price_count']==0

def test_wrong_currency():
    assert summarize_fixture({'itemSummaries':[row()]},'IE')['valid_price_count']==0

def test_auction():
    x=row(); x['buyingOptions']=['AUCTION']; assert summarize_fixture({'itemSummaries':[x]},'UK')['unique_fixed_price_count']==0

def test_empty():
    assert summarize_fixture({'total':0},'UK')['returned_count']==0

@pytest.mark.parametrize('payload',[{}, {'errors':[]}, {'itemSummaries':'x'}, {'itemSummaries':[None]}])
def test_invalid_payload(payload):
    with pytest.raises(ValueError): summarize_fixture(payload,'UK')

@pytest.mark.parametrize('status,expected',[(401,'AUTHENTICATION_REQUIRED'),(403,'ACCESS_DENIED'),(429,'RATE_LIMITED'),(503,'UPSTREAM_UNAVAILABLE')])
def test_status(status,expected): assert classify_status(status)==expected
