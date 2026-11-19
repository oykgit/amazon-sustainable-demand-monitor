import unittest
from unittest.mock import patch, MagicMock
from neon_readiness import read_interest_summary

class NeonReadinessTests(unittest.TestCase):
    @patch('neon_readiness._connection')
    def test_existing_data(self, connect):
        cur = MagicMock()
        cur.fetchone.return_value = ('search_interest_observations',)
        cur.fetchall.return_value = [('IE','drawer organiser',12,6.6)]
        connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = cur
        data = read_interest_summary('postgresql://fake/test')
        self.assertEqual(data['rows'],12)
        self.assertEqual(data['keywords'],1)
        self.assertEqual(data['series'][0]['mean_interest'],6.6)
        self.assertTrue(all(q.args[0].lstrip().upper().startswith('SELECT') for q in cur.execute.call_args_list))
    @patch('neon_readiness._connection')
    def test_table_missing(self, connect):
        cur = MagicMock()
        cur.fetchone.return_value = (None,)
        connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = cur
        self.assertEqual(read_interest_summary('postgresql://fake/test')['rows'],0)
