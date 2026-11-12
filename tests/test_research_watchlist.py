from datetime import date
import pytest
from research_watchlist import validate_entry,watchlist_status

def test_validate():
    entry=validate_entry('b008s8rjkk','UK',interval=7)
    assert entry['asin']=='B008S8RJKK'
    with pytest.raises(ValueError): validate_entry('bad','UK')
    with pytest.raises(ValueError): validate_entry('B008S8RJKK','UK',interval=0)
    with pytest.raises(ValueError): validate_entry('B008S8RJKK','UK',source_reference='x'*501)

def test_status_no_observation():
    entry=validate_entry('B008S8RJKK','UK')
    row=watchlist_status([entry],[],today=date(2026,11,12))[0]
    assert row['Review status']=='Due'
    assert row['History days']==0
    assert row['Traceable source']=='Missing'

def test_status_milestones():
    entry=validate_entry('B008S8RJKK','UK',interval=7,source_reference='receipt')
    snapshots=[{'asin':'B008S8RJKK','marketplace':'UK','observed_at_utc':d} for d in
        ['2025-11-01T12:00:00+00:00','2026-11-01T12:00:00+00:00']]
    row=watchlist_status([entry],snapshots,today=date(2026,11,12))[0]
    assert row['365-day coverage']=='Reached'
    assert row['Review status']=='Due'
    assert row['Traceable source']=='Provided'

def test_no_cross_marketplace():
    entry=validate_entry('B008S8RJKK','IE')
    rows=[{'asin':'B008S8RJKK','marketplace':'UK','observed_at_utc':'2026-11-01T00:00:00Z'}]
    assert watchlist_status([entry],rows)[0]['Observation days']==0
