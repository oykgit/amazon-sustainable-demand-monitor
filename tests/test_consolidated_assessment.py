import unittest
from consolidated_assessment import consolidate

COMP = {'ASIN':'B008S8RJKK','Marketplace':'UK','Latest profit estimate (€)':4.4,'Latest ROI estimate (%)':55.0}
IDENT = {'asin':'B008S8RJKK','marketplace':'UK','name':'Coffee','observed_at_utc':'2026-11-12','source_url':'https://example.org'}
INTEREST = [{'market':'UK','keyword':'instant coffee','month':'2026-01','search_interest':40,'source':'test'},
            {'market':'UK','keyword':'instant coffee','month':'2026-02','search_interest':60,'source':'test'},
            {'market':'IE','keyword':'instant coffee','month':'2026-01','search_interest':90,'source':'test'}]

class ConsolidatedTests(unittest.TestCase):
    def test_no_automatic_link(self):
        r=consolidate([COMP],[IDENT],INTEREST)[0]
        self.assertEqual(r['Google Trends observed months'],0)
        self.assertEqual(r['Product identity (operator recorded)'],'Coffee')
        self.assertFalse(r['Sustained Amazon demand verified'])
    def test_explicit_market_link(self):
        r=consolidate([COMP],[IDENT],INTEREST,{('B008S8RJKK','UK'):'instant coffee'})[0]
        self.assertEqual(r['Google Trends observed months'],2)
        self.assertEqual(r['Google Trends average relative interest'],50)
        self.assertEqual(r['Latest profit estimate (€)'],4.4)
        self.assertEqual(r['Purchase recommendation'],'NOT PROVIDED')
    def test_wrong_market_is_not_linked(self):
        r=consolidate([COMP],[],INTEREST,{('B008S8RJKK','UK'):'unrelated'})[0]
        self.assertIsNone(r['Google Trends average relative interest'])
    def test_identity_latest(self):
        old=dict(IDENT,name='Old',observed_at_utc='2026-01-01')
        r=consolidate([COMP],[IDENT,old],[])[0]
        self.assertEqual(r['Product identity (operator recorded)'],'Coffee')
    def test_no_data(self):
        self.assertEqual(consolidate([],[],[]),[])

if __name__ == '__main__': unittest.main()
