import unittest
import pandas as pd
from audit import inspect, inspect_stored

class AuditTests(unittest.TestCase):
    def test_empty_storage(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            overview,details=inspect_stored(d)
            self.assertEqual(len(overview),3)
            self.assertTrue((overview.status=='NOT CONFIGURED / NO DATA').all())
            self.assertEqual(details,{})
    def test_twelve_month_coverage(self):
        months=pd.period_range(end=pd.Timestamp.today().to_period('M'),periods=12)
        rows=[dict(market='UK',asin='B000123456',product='Test',month=str(m),demand_index=50,
                   sale_price=20,source_cost=5,marketplace_fee=3,shipping=2,other_cost=1,
                   competition_index=20,source='manual',verified=False) for m in months]
        result=inspect('monthly',pd.DataFrame(rows))
        self.assertTrue(result['coverage'].iloc[0].complete_12_months)
        result2=inspect('monthly',pd.DataFrame(rows[:-1]))
        self.assertFalse(result2['coverage'].iloc[0].complete_12_months)
    def test_reject_invalid(self):
        with self.assertRaises(ValueError):inspect('rank',pd.DataFrame({'market':['UK']}))
if __name__=='__main__':unittest.main()
