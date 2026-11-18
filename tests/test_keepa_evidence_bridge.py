import unittest
from keepa_evidence_bridge import assess_keepa_payload

class BridgeTests(unittest.TestCase):
    def payload(self):
        return {'asin':'B008S8RJKK','csv':[[8000000,1500], [8000000,1600], None, [8000000,3000]]}
    def test_rank_without_fx(self):
        r=assess_keepa_payload(self.payload(),'B008S8RJKK',as_of='2026-11-18')
        self.assertEqual(len(r['groups']),1)
        self.assertEqual(r['groups'][0]['evidence_type'],'SALES_RANK')
        self.assertEqual(r['normalization']['skipped']['gbp_without_fx'],1)
    def test_fx_adds_price(self):
        r=assess_keepa_payload(self.payload(),'B008S8RJKK',fx_gbp_to_eur=1.2,as_of='2026-11-18')
        self.assertEqual(len(r['groups']),2)
        self.assertEqual(r['normalization']['skipped']['alternative_price_series'],1)
    def test_read_only(self):
        r=assess_keepa_payload(self.payload(),'B008S8RJKK')
        self.assertEqual(r['network_requests'],0)
        self.assertEqual(r['database_writes'],0)
        self.assertFalse(r['purchases_enabled'])
        self.assertFalse(r['historical_demand_verified'])
    def test_bad_asin(self):
        with self.assertRaises(ValueError):assess_keepa_payload(self.payload(),'BAD')
    def test_bad_fx(self):
        with self.assertRaises(ValueError):assess_keepa_payload(self.payload(),'B008S8RJKK',fx_gbp_to_eur=-1)
    def test_empty(self):
        r=assess_keepa_payload({'asin':'B008S8RJKK','csv':[]},'B008S8RJKK')
        self.assertEqual(r['groups'],[])
    def test_sha_stable(self):
        a=assess_keepa_payload(self.payload(),'B008S8RJKK')
        b=assess_keepa_payload(self.payload(),'B008S8RJKK')
        self.assertEqual(a['normalization']['payload_sha256'],b['normalization']['payload_sha256'])
if __name__=='__main__': unittest.main()
