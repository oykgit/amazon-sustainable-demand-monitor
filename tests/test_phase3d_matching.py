import pytest
from phase3d_matching import compare_fixture, demo, gtin

@pytest.fixture
def records():
    base = dict(gtin='4006381333931', brand='Example', model='X1', variant='Blue', pack_count=2, condition='NEW', title='Example X1 Blue')
    return dict(base, marketplace='UK', price={'value':'12.50','currency':'GBP'}, shipping_quote={'value':'2.00','currency':'GBP'}), dict(base, marketplace='IE')

def test_demo():
    r=demo(); assert r['match_status']=='STRUCTURED_MATCH_CANDIDATE'; assert r['illustrative_subtotal_eur']=='17.40'
    assert not any(r[k] for k in ('identity_verified','landed_cost_verified','demand_verified','purchase_recommendation','browse_requests','database_writes','browse_collection_authorized','post_activation_authorized'))

@pytest.mark.parametrize('key,value', [('brand','Other'),('model','X2'),('variant','Red'),('pack_count',1),('condition','USED'),('gtin','036000291452')])
def test_conflict(records,key,value):
    a,b=records; b[key]=value; assert compare_fixture(a,b)['match_status']=='REJECT_CONFLICT'

@pytest.mark.parametrize('key', ['gtin','brand','model','variant','pack_count','condition'])
def test_missing(records,key):
    a,b=records; b.pop(key); assert compare_fixture(a,b)['match_status']=='REVIEW_REQUIRED'

@pytest.mark.parametrize('value',['1234567890123','00000000','1234567890129','12345678901234',123])
def test_bad_gtin(value):
    with pytest.raises(ValueError): gtin(value)

def test_equivalent_gtin():
    assert gtin('036000291452')==gtin('0036000291452')

def test_missing_shipping(records):
    a,b=records; a.pop('shipping_quote'); assert compare_fixture(a,b,gbp_to_eur='1.2')['illustrative_subtotal_eur'] is None

def test_free_shipping(records):
    a,b=records; a['shipping_quote']['value']='0'; assert compare_fixture(a,b,gbp_to_eur='1.2')['illustrative_subtotal_eur']=='15.00'

def test_no_fx(records):
    assert compare_fixture(*records)['illustrative_subtotal_eur'] is None

def test_bad_currency(records):
    a,b=records; a['price']['currency']='EUR'; assert compare_fixture(a,b)['asking_price_plus_shipping'] is None

def test_title_not_enough(records):
    a,b=records; b.pop('gtin'); assert compare_fixture(a,b)['title_exact_match']; assert compare_fixture(a,b)['match_status']=='REVIEW_REQUIRED'

def test_non_new(records):
    a,b=records; a['condition']=b['condition']='USED'; assert compare_fixture(a,b)['match_status']=='REJECT_CONFLICT'

def test_no_personal_data(records):
    a,b=records; a['seller']='private@example.com'; assert 'private@example.com' not in str(compare_fixture(a,b))

def test_bool_pack(records):
    a,b=records; a['pack_count']=True; assert compare_fixture(a,b)['match_status']=='REVIEW_REQUIRED'

def test_eur(records):
    a,b=records; a['marketplace']='IE'; a['price']['currency']=a['shipping_quote']['currency']='EUR'; assert compare_fixture(a,b)['illustrative_subtotal_eur']=='14.50'
