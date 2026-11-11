import unittest
import pandas as pd
from collector import validate,merge

class CollectorTests(unittest.TestCase):
    def test_rejects_missing_columns(self):
        with self.assertRaises(ValueError): validate(pd.DataFrame({'market':['UK']}),'rank')
    def test_merge_replaces_matching_observation(self):
        base={'market':'UK','asin':'B123','product':'Product','observed_at':'2026-10-10','best_seller_rank':100,'category':'Home','source_url':'https://example.com'}
        newer={**base,'best_seller_rank':80}
        out=merge(pd.DataFrame([base]),pd.DataFrame([newer]),'rank')
        self.assertEqual(len(out),1)
        self.assertEqual(int(out.iloc[0].best_seller_rank),80)
    def test_rejects_future_dates(self):
        row={'market':'IE','asin':'B123','product':'Product','observed_at':'2099-01-01','best_seller_rank':100,'category':'Home','source_url':'https://example.com'}
        with self.assertRaises(ValueError): validate(pd.DataFrame([row]),'rank')
if __name__=='__main__': unittest.main()
