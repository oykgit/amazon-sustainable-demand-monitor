import unittest
from unittest.mock import patch
from dashboard_commercial import display_rows, load_dashboard

class DashboardCommercialTests(unittest.TestCase):
    def test_display_rows_never_recommends_purchase(self):
        report={'products':[{'asin':'B123','marketplace':'UK','name':'Example','scenario_profit_eur':4.4,'scenario_roi_pct':55,'research_priority':'REVIEW SCENARIO','evidence_gaps':['Demand unknown'],'buy_recommendation':True}]}
        row=display_rows(report)[0]
        self.assertEqual(row['Estimated profit (EUR)'],4.4)
        self.assertFalse(row['Verified buy recommendation'])
        self.assertIn('Demand unknown',row['Evidence gaps'])
    @patch('dashboard_commercial.assess')
    @patch('dashboard_commercial.run')
    def test_load_uses_existing_assessment(self, run, assess):
        run.return_value={'products':[]}
        assess.return_value={'products_assessed':0}
        self.assertEqual(load_dashboard(),{'products_assessed':0})
        assess.assert_called_once_with(run.return_value)
