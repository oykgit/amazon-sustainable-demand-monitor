from dataclasses import replace
from datetime import datetime, timezone, timedelta
import pytest
from restoration_guard import *

T=datetime(2026,1,1,tzinfo=timezone.utc)
D='a'*64

def evidence():
    return dict(restore_id='synthetic-1', restored_to=T, restored_at=T+timedelta(hours=2), checked_at=T+timedelta(hours=3), manifest=ExternalManifest('synthetic-1',T,T+timedelta(hours=3),(Obligation(D,T+timedelta(hours=1)),)), reconciliations=(Reconciliation(D,T+timedelta(hours=2),0),), inventory_verified=True,external_stores_verified=True,ingestion_suspended=True)

def test_consistent_never_authorizes():
    result=assess_restore(**evidence())
    assert result['evidence_consistent'] and result['obligations_reconciled']==1
    assert not result['production_resume_authorized'] and not result['http_acknowledgment_authorized']
    assert D not in str(result)

@pytest.mark.parametrize('field,value',[('inventory_verified',False),('external_stores_verified',False),('ingestion_suspended',False),('inventory_verified',1),('restore_id','other'),('reconciliations',()),('restored_at',T-timedelta(hours=1)),('checked_at',T.replace(tzinfo=None))])
def test_fail_closed(field,value):
    e=evidence(); e[field]=value
    with pytest.raises(RestorationError): assess_restore(**e)

@pytest.mark.parametrize('changes',[{'remaining_records':1},{'remaining_records':False},{'verified_at':T},{'fingerprint':'b'*64}])
def test_bad_reconciliation(changes):
    e=evidence(); e['reconciliations']=(replace(e['reconciliations'][0],**changes),)
    with pytest.raises(RestorationError): assess_restore(**e)

@pytest.mark.parametrize('changes',[{'covered_from':T+timedelta(seconds=1)},{'covered_until':T},{'restore_id':'other'},{'obligations':(Obligation(D,T),Obligation(D,T))}])
def test_bad_manifest(changes):
    e=evidence(); e['manifest']=replace(e['manifest'],**changes)
    with pytest.raises(RestorationError): assess_restore(**e)

def test_duplicate_reconciliation():
    e=evidence(); e['reconciliations']*=2
    with pytest.raises(RestorationError): assess_restore(**e)

def test_empty_manifest_not_authorization():
    e=evidence(); e['manifest']=replace(e['manifest'],obligations=()); e['reconciliations']=()
    assert not assess_restore(**e)['production_resume_authorized']
