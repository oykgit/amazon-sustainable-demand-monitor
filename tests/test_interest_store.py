import unittest
import pandas as pd
from interest_store import validate_interest

class InterestValidationTests(unittest.TestCase):
    def example(self):
        return pd.DataFrame([{'market':'IE','keyword':'drawer organiser','month':'2026-10','search_interest':0,'source':'Google Trends manual export'}])
    def test_valid(self):
        self.assertEqual(len(validate_interest(self.example())),1)
    def test_missing_source(self):
        d=self.example();d.loc[0,'source']=''
        with self.assertRaises(ValueError):validate_interest(d)
    def test_bad_market(self):
        d=self.example();d.loc[0,'market']='US'
        with self.assertRaises(ValueError):validate_interest(d)
    def test_out_of_range(self):
        d=self.example();d.loc[0,'search_interest']=101
        with self.assertRaises(ValueError):validate_interest(d)
    def test_duplicate_month(self):
        d=pd.concat([self.example(),self.example()],ignore_index=True)
        with self.assertRaises(ValueError):validate_interest(d)
    def test_future(self):
        d=self.example();d.loc[0,'month']='2099-01'
        with self.assertRaises(ValueError):validate_interest(d)
    def test_bad_month(self):
        d=self.example();d.loc[0,'month']='2026-13'
        with self.assertRaises(ValueError):validate_interest(d)
if __name__=='__main__':unittest.main()
