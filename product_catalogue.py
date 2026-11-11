"""Optional real product metadata from Open Food Facts; never Amazon demand/sales."""
import json
import re
from urllib.request import Request, urlopen

API='https://world.openfoodfacts.org/api/v2/product/{barcode}.json'
FIELDS='code,product_name,brands,quantity,categories_tags,image_front_small_url'

def lookup_barcode(barcode, opener=urlopen):
    barcode=str(barcode).strip()
    if not re.fullmatch(r'\d{8,14}',barcode):
        raise ValueError('Enter a valid 8–14 digit retail barcode.')
    url=API.format(barcode=barcode)+'?fields='+FIELDS
    req=Request(url,headers={'User-Agent':'AmazonSustainableDemandMonitor/1.4 (research tool; operator contact via GitHub oykgit/amazon-sustainable-demand-monitor)','Accept':'application/json'})
    with opener(req,timeout=12) as response:
        raw=response.read(500_001)
    if len(raw)>500_000: raise ValueError('Catalogue response too large.')
    data=json.loads(raw)
    if data.get('status')!=1 or not isinstance(data.get('product'),dict):
        return {'barcode':barcode,'found':False,'source':'Open Food Facts','source_url':'https://world.openfoodfacts.org/product/'+barcode}
    p=data['product']
    return {'barcode':barcode,'found':True,'name':str(p.get('product_name') or '').strip(),
            'brand':str(p.get('brands') or '').strip(),'quantity':str(p.get('quantity') or '').strip(),
            'source':'Open Food Facts','source_url':'https://world.openfoodfacts.org/product/'+barcode,
            'amazon_sales_known':False,'amazon_price_known':False,'amazon_eligibility_known':False}
