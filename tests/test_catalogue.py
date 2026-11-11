import io
import json
import pytest
from product_catalogue import lookup_barcode

class FakeResponse:
    def __init__(self,data): self.data=json.dumps(data).encode()
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self,n): return self.data[:n]

def test_real_metadata_is_not_amazon_sales():
    def opener(req,timeout):
        assert req.full_url.startswith('https://world.openfoodfacts.org/')
        return FakeResponse({'status':1,'product':{'product_name':'Test oats','brands':'Example'}})
    result=lookup_barcode('12345678',opener)
    assert result['name']=='Test oats'
    assert result['amazon_sales_known'] is False

def test_no_product():
    assert lookup_barcode('12345678',lambda req,timeout:FakeResponse({'status':0}))['found'] is False

@pytest.mark.parametrize('barcode',['','123','abcd1234','123456789012345','12345678/../'])
def test_bad_barcode(barcode):
    with pytest.raises(ValueError): lookup_barcode(barcode)
