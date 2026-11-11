import pytest
from profitability import calculate, screen

BASE=dict(price=25,unit_cost=10,referral_pct=15,fulfilment_fee=3,inbound_shipping=1,packaging=0.5,other_cost=0.5,return_reserve_pct=2,vat_rate_pct=0,vat_included=False,vat_recoverable=False)

def test_basic_profit_and_break_even():
    r=calculate(**BASE)
    assert r['net_profit_eur']==5.75
    assert r['referral_fee_eur']==3.75
    assert r['break_even_price_eur']==18.07
    assert r['roi_on_purchase_cost_pct']==57.5

def test_vat_inclusive_scenario():
    r=calculate(**{**BASE,'price':24,'unit_cost':12,'vat_rate_pct':20,'vat_included':True,'vat_recoverable':True})
    assert r['net_sales_revenue_eur']==20
    assert r['scenario_output_vat_eur']==4
    assert r['purchase_cost_used_eur']==10
    assert r['scenario_recoverable_purchase_vat_eur']==2

def test_screen_is_not_purchase_advice():
    r=calculate(**BASE)
    assert 'NOT A BUY RECOMMENDATION' in screen(r,4,25)
    assert screen(r,20,25)=='BELOW SCENARIO THRESHOLD'

def test_unattainable_break_even():
    r=calculate(**{**BASE,'referral_pct':100})
    assert r['break_even_possible'] is False

def test_invalid_inputs():
    for bad in [float('nan'),float('inf'),-1]:
        with pytest.raises(ValueError):calculate(**{**BASE,'price':bad})
    with pytest.raises(ValueError):calculate(**{**BASE,'referral_pct':101})
