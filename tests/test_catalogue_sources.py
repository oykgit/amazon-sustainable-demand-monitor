import io
import json
from datetime import datetime, timezone
import pandas as pd
import pytest
from catalogue_sources import lookup_upcitemdb, lookup_product, observation, merge_observations, FIELDS

class FakeResponse:
    def __init__(self, payload): self.payload=payload
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def read(self,n): return json.dumps(self.payload).encode()

def fake(payload):
    def opener(req,timeout):
        assert timeout==12
        assert 'api.upcitemdb.com' in req.full_url
        return FakeResponse(payload)
    return opener

def test_exact_match():
    r=lookup_upcitemdb('012345678905',opener=fake({'items':[{'ean':'012345678905','title':'Test','brand':'Maker'}]}))
    assert r['found'] and r['name']=='Test' and not r['amazon_sales_known']

def test_reject_unrelated_match():
    assert not lookup_upcitemdb('012345678905',opener=fake({'items':[{'ean':'999999999999','title':'Wrong'}]}))['found']

def test_invalid_barcodes():
    for barcode in ['123','12abc567890','123456789012345','']:
        with pytest.raises(ValueError): lookup_upcitemdb(barcode,opener=fake({}))

def test_bad_response():
    with pytest.raises(ValueError): lookup_upcitemdb('012345678905',opener=fake({'items':{}}))

def test_unknown_source():
    with pytest.raises(ValueError): lookup_product('012345678905','unknown')

def test_observation_and_dedupe():
    r=lookup_upcitemdb('012345678905',opener=fake({'items':[{'upc':'012345678905','title':'Test'}]}))
    row=observation(r,datetime(2026,11,11,tzinfo=timezone.utc))
    assert list(row)==FIELDS
    merged=merge_observations(pd.DataFrame(columns=FIELDS),row)
    merged=merge_observations(merged,row)
    assert len(merged)==1 and merged.iloc[0]['source']=='UPCitemdb'

def test_missing_not_observed():
    with pytest.raises(ValueError): observation({'found':False})

def test_invalid_merge_columns():
    with pytest.raises(ValueError): merge_observations(pd.DataFrame({'bad':[1]}),{})
