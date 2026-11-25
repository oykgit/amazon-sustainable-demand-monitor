from datetime import datetime,timezone,date
from unittest.mock import patch
import pytest
import automated_research_report as report
import scheduled_review as review
from commercial_intelligence import assess
from dashboard_commercial import display_rows
from reporting_guard import ReportError
NOW=datetime(2025,11,20,tzinfo=timezone.utc)
BASE=dict(asin='B0D46JP795',marketplace='UK',observed_at_utc='2025-11-19T10:00:00Z',selling_price_eur=20,supplier_cost_eur=8,referral_pct=15,fulfilment_eur=3,inbound_eur=1,other_eur=0,returns_pct=3,estimated_profit_eur=999,source_note='private@example.org')

def test_recompute_and_minimize():
    result=report.summarize([BASE],[dict(BASE,name='private@example.org')],[],NOW)
    assert result['products'][0]['scenario_profit_eur']==4.4
    assert 'private@example.org' not in str(result)
    assert not result['verified_demand']

@pytest.mark.parametrize('change',[{'asin':'bad'},{'marketplace':'XX'},{'selling_price_eur':'NaN'},{'supplier_cost_eur':-1},{'observed_at_utc':'2025-11-21T00:00:00Z'},{'observed_at_utc':'2025-11-19'}])
def test_bad_evidence(change):
    with pytest.raises(ReportError): report.summarize([dict(BASE,**change)],[],[],NOW)

def test_conflicting_latest():
    with pytest.raises(ReportError): report.summarize([BASE,dict(BASE,selling_price_eur=21)],[],[],NOW)

def test_caps():
    with pytest.raises(ReportError): report.summarize([],[],[{}]*10000,NOW)
    with pytest.raises(ReportError): review.build_report([{}]*10000,[],date(2025,11,20))

def test_projection():
    row=dict(asin=BASE['asin'],marketplace='UK',name='private@example.org',scenario_profit_eur=4.4,scenario_roi_pct=55,evidence_warnings=['private@example.org'],evidence_gaps=['private@example.org'],buy_recommendation=True)
    for output in (assess({'products':[row]}),display_rows({'products':[row]})):
        assert 'private@example.org' not in str(output)
    assert not assess({'products':[row]})['products'][0]['buy_recommendation']

def test_secure_reader_without_legacy():
    with patch.dict('os.environ',{'COMMERCIAL_STORAGE_MODE':'secure'},clear=True),patch.object(report,'load_snapshots',return_value=[]) as s,patch.object(report,'load_asin_observations',return_value=[]),patch.object(report,'load_entries',return_value=[]):
        assert report.run()['products_count']==0
        s.assert_called_once_with(url=None,limit=10000)

def test_review_future_and_private():
    entry=dict(asin=BASE['asin'],marketplace='UK',priority='High',review_interval_days=7,source_reference='private@example.org',notes='private@example.org')
    assert 'private@example.org' not in str(review.build_report([entry],[],date(2025,11,20)))
    with pytest.raises(ReportError): review.build_report([entry],[dict(BASE,observed_at_utc='2025-11-21T00:00:00Z')],date(2025,11,20))
