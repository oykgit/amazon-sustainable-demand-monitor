import unittest
from commercial_intelligence import assess
from keepa_provider_contract import fetch_history,status
class Tests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(assess({'products':[]})['products_assessed'],0)
    def test_profitable_scenario_not_buy_advice(self):
        p=assess({'products':[{'asin':'B0D46JP795','scenario_profit_eur':4.4,'scenario_roi_pct':55,'evidence_warnings':[]}]})['products'][0]
        self.assertFalse(p['buy_recommendation'])
        self.assertTrue(p['evidence_gaps'])
    def test_keepa_disabled(self):
        self.assertFalse(status()['network_enabled'])
        with self.assertRaises(RuntimeError):fetch_history('B0D46JP795')
