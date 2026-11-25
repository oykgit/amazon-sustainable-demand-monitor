"""Stage 2B free-data commercial evidence gate. No Amazon calls or orders."""
import argparse
import json
from datetime import datetime, timezone

from reporting_guard import bounded, projected, require

GAPS=('12-month Amazon sales/demand unverified','Live Amazon fees and eligibility unverified','Supplier availability and costs unverified','Scenario values are not verified commercial returns')

def assess(research):
    products=[]
    seen=set()
    require(isinstance(research,dict))
    for row in bounded(research.get('products')):
        product=projected(row)
        k=(product['asin'],product['marketplace'])
        require(k not in seen); seen.add(k)
        product['evidence_gaps']=list(GAPS)
        products.append(product)
    products.sort(key=lambda p:(p['scenario_profit_eur'] is None,-(p['scenario_profit_eur'] or 0),p['asin'],p['marketplace']))
    return {'mode':'STAGE_2B_FREE_DATA_READ_ONLY','generated_at_utc':datetime.now(timezone.utc).isoformat(), 'source':'Stored Neon observations only', 'products_assessed':len(products), 'verified_commercial_opportunities':0, 'automatic_live_amazon_data':False, 'keepa_calls':0,'database_writes':0,'purchases_enabled':False,'products':products}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='commercial_intelligence_report.json');args=parser.parse_args()
    from automated_research_report import run
    report=assess(run())
    with open(args.output,'w',encoding='utf8') as f:json.dump(report,f,indent=2,allow_nan=False)
    print('Assessed',report['products_assessed'],'stored products; 0 verified buy opportunities')
if __name__=='__main__':main()
