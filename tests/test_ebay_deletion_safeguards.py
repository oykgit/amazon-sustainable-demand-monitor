import unittest
from ebay_deletion_safeguards import assess_schema, read_schema_metadata


class SchemaTests(unittest.TestCase):
    def test_known_product_tables_do_not_grant_processing(self):
        result = assess_schema({'asin_identity_observations': {'asin', 'source'}, 'catalogue_identity_observations': {'barcode'}})
        self.assertFalse(result.ready_for_processing)
        self.assertEqual(result.unknown_tables, ())

    def test_unreviewed_table_flagged(self):
        result = assess_schema({'ebay_listings': {'price'}})
        self.assertEqual(result.unknown_tables, ('ebay_listings',))

    def test_user_id_column_flagged(self):
        result = assess_schema({'ebay_listings': {'ebay_user_id', 'price'}})
        self.assertIn('ebay_listings.ebay_user_id', result.potential_identifier_columns)

    def test_future_seller_column_flagged(self):
        result = assess_schema({'asin_identity_observations': {'ebay_seller_reference'}})
        self.assertEqual(len(result.potential_identifier_columns), 1)

    def test_bad_schema_rejected(self):
        with self.assertRaises(ValueError):
            assess_schema({'table': 'columns'})

    def test_read_only_metadata_query(self):
        calls = []
        class Cursor:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def execute(self, sql): calls.append(sql)
            def fetchall(self): return [('asin_identity_observations', 'asin')]
        class Conn:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def cursor(self): return Cursor()
        result = read_schema_metadata(lambda: Conn())
        self.assertFalse(result.ready_for_processing)
        self.assertEqual(len(calls), 1)
        self.assertIn('information_schema.columns', calls[0])
        self.assertNotIn('DELETE ', calls[0])

if __name__ == '__main__': unittest.main()
