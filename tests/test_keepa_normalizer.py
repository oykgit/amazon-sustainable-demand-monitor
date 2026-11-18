import unittest
from keepa_normalizer import normalize

class KeepaNormalizationTests(unittest.TestCase):
    def test_price_and_rank(self):
        r=normalize({'asin':'B008S8RJKK','csv':[[5000000,1299,5001440,-1],[5000000,1599],None,[5000000,12345]]},'B008S8RJKK')
        self.assertEqual(r['count'],3)
        self.assertEqual(r['omitted']['unavailable_or_out_of_stock'],1)
        self.assertEqual(r['observations'][0]['value'],12.99)
        self.assertFalse(r['historical_demand_verified'])
    def test_odd_array_rejected(self):
        with self.assertRaises(ValueError): normalize({'csv':[[10,500,20]]},'B008S8RJKK')
    def test_asin_mismatch(self):
        with self.assertRaises(ValueError): normalize({'asin':'B000000000','csv':[]},'B008S8RJKK')
    def test_missing_csv(self):
        with self.assertRaises(ValueError): normalize({},'B008S8RJKK')
    def test_invalid_fx(self):
        with self.assertRaises(ValueError): normalize({'csv':[]},'B008S8RJKK',fx_gbp_to_eur=-2)
    def test_fx_operator_estimate(self):
        r=normalize({'csv':[[5000000,1000]]},'B008S8RJKK',fx_gbp_to_eur=1.2)
        self.assertEqual(r['observations'][0]['price_eur_operator_estimate'],12)
    def test_no_ireland_domain(self):
        with self.assertRaises(ValueError): normalize({'csv':[]},'B008S8RJKK','IE')
    def test_future_time_not_emitted(self):
        r=normalize({'csv':[[100000000,1000]]},'B008S8RJKK')
        self.assertEqual(r['count'],0)
    def test_bad_value(self):
        with self.assertRaises(ValueError): normalize({'csv':[[5000000,'hello']]},'B008S8RJKK')
if __name__=='__main__': unittest.main()
