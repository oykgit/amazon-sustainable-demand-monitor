import unittest
import pandas as pd
from free_sources import import_rank_snapshots,rank_summary,import_search_interest

class TestFreeSources(unittest.TestCase):
    def test_rank_import_and_no_buy(self):
        from io import StringIO
        csv=StringIO('market,asin,product,observed_at,best_seller_rank,category,source_url\nUK,B1,Item,2026-01-02,25,Home,https://www.amazon.co.uk/a\n')
        d=import_rank_snapshots(csv)
        self.assertEqual(len(d),1)
        self.assertEqual(rank_summary(d).iloc[0]['decision'],'RESEARCH REQUIRED')
    def test_bad_rank_filtered(self):
        from io import StringIO
        csv=StringIO('market,asin,product,observed_at,best_seller_rank,category,source_url\nUK,B1,Item,2026-01-02,-5,Home,https://example.com\n')
        self.assertTrue(import_rank_snapshots(csv).empty)
    def test_interest_range(self):
        from io import StringIO
        csv=StringIO('market,keyword,month,search_interest,source\nIE,desk,2026-01,101,manual\nIE,desk,2026-02,75,manual\n')
        self.assertEqual(len(import_search_interest(csv)),1)
if __name__=='__main__':unittest.main()
