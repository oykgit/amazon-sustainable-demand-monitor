import unittest
from datetime import datetime,timezone
from automated_research_report import summarize

class SummaryTests(unittest.TestCase):
    def test_read_only_scenario_warning(self):
        rows=[{'asin':'B0D46JP795','marketplace':'UK','observed_at_utc':'2026-11-19T10:00:00+00:00',
               'selling_price_eur':20,'estimated_profit_eur':4.4,'estimated_roi_pct':55}]
        out=summarize(rows,[],[],checked_at=datetime(2026,11,19,tzinfo=timezone.utc))
        self.assertEqual(out['products_count'],1)
        self.assertEqual(out['products'][0]['scenario_profit_eur'],4.4)
        self.assertFalse(out['products'][0]['buy_recommendation'])
        self.assertFalse(out['verified_demand'])
        self.assertEqual(out['database_writes'],0)
    def test_no_fake_data(self):
        out=summarize([],[],[])
        self.assertEqual(out['products'],[])
