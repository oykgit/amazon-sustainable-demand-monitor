"""Stage 2B free-data commercial evidence gate. No Amazon calls or orders."""
import argparse
import json
from datetime import datetime, timezone

def assess(research):
    products=[]
    for row in research.get('products',[]):
        warnings=list(row.get('evidence_warnings',[]))
        warnings += ['12-month Amazon sales/demand unverified', 'Live Amazon fees and eligibility unverified', 'Supplier availability and costs unverified']
        products.append({'asin':row.get('asin'),'marketplace':row.get('marketplace'), 'name':row.get('name'), 'scenario_profit_eur':row.get('scenario_profit_eur'), 'scenario_roi_pct':row.get('scenario_roi_pct'), 'research_priority':row.get('research_priority'), 'evidence_gaps':sorted(set(warnings)), 'buy_recommendation':False})
    products.sort(key=lambda p:(p['scenario_profit_eur'] is None, -(p['scenario_profit_eur'] or 0),p['asin'] or ''))
    return {'mode':'STAGE_2B_FREE_DATA_READ_ONLY','generated_at_utc':datetime.now(timezone.utc).isoformat(), 'source':'Stored Neon observations only', 'products_assessed':len(products), 'verified_commercial_opportunities':0, 'automatic_live_amazon_data':False, 'keepa_calls':0,'database_writes':0,'purchases_enabled':False,'products':products}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='commercial_intelligence_report.json');args=parser.parse_args()
    from automated_research_report import run
    report=assess(run())
    with open(args.output,'w',encoding='utf8') as f:json.dump(report,f,indent=2)
    print('Assessed',report['products_assessed'],'stored products; 0 verified buy opportunities')
if __name__=='__main__':main()
