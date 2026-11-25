import os
import unittest
from unittest.mock import patch, MagicMock
from contextlib import contextmanager
import persistent_store as store
import asin_store, price_history, research_watchlist, interest_store, neon_readiness
from secure_database import DatabaseAccessError

LOADERS = [store.load_observations, asin_store.load_asin_observations,
           price_history.load_snapshots, research_watchlist.load_entries,
           interest_store.load_interest]

class StorageTests(unittest.TestCase):
    def test_legacy_loaders_select_only(self):
        for load in LOADERS:
            with self.subTest(load=load.__name__), patch.dict(os.environ, {'COMMERCIAL_STORAGE_MODE':'legacy'}, clear=True), patch.object(store, '_connection') as connect:
                cur = connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
                cur.fetchall.return_value = []
                load(url='postgresql://fake/test')
                sql = [c.args[0].strip().upper() for c in cur.execute.call_args_list]
                self.assertEqual(sql[0], 'SET TRANSACTION READ ONLY')
                self.assertEqual(len(sql), 2)
                self.assertTrue(sql[1].startswith('SELECT '))

    def test_secure_loaders_route_reader(self):
        for load in LOADERS:
            with self.subTest(load=load.__name__), patch.dict(os.environ, {'COMMERCIAL_STORAGE_MODE':'secure'}, clear=True), patch.object(store, 'database_transaction') as tx, patch.object(store, '_connection') as legacy:
                cur = tx.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
                cur.fetchall.return_value = []
                load(url='ignored-legacy-url')
                tx.assert_called_once_with('reader')
                legacy.assert_not_called()
                self.assertEqual(len(cur.execute.call_args_list), 1)
                self.assertTrue(cur.execute.call_args.args[0].strip().upper().startswith('SELECT '))

    def test_secure_missing_credentials_no_fallback(self):
        with patch.dict(os.environ, {'COMMERCIAL_STORAGE_MODE':'secure','DATABASE_URL':'postgresql://fake/test'}, clear=True), patch.object(store, '_connection') as legacy:
            with self.assertRaises(DatabaseAccessError): store.load_observations()
            legacy.assert_not_called()

    def test_secure_legacy_direct_path_blocked(self):
        with patch.dict(os.environ, {'COMMERCIAL_STORAGE_MODE':'secure'}, clear=True):
            with self.assertRaises(DatabaseAccessError): store._connection('postgresql://fake/test')

    def test_invalid_mode(self):
        with patch.dict(os.environ, {'COMMERCIAL_STORAGE_MODE':'typo'}, clear=True):
            with self.assertRaises(DatabaseAccessError): store.load_observations()

    def test_secure_writers_no_schema_creation(self):
        import pandas as pd
        from datetime import datetime, timezone
        snapshot = price_history.build_snapshot('B008S8RJKK','UK',20,10,15,2,1,1,3,'Synthetic test')
        operations = [lambda: store.save_observations([]), lambda: asin_store.save_asin_observations([]),
                      lambda: price_history.save_snapshot(snapshot),
                      lambda: research_watchlist.upsert_entry({'asin':'B008S8RJKK','marketplace':'UK'}),
                      lambda: interest_store.save_interest(pd.DataFrame([{'market':'IE','keyword':'test','month':'2020-01','search_interest':50,'source':'test'}]))]
        for operation in operations:
            with self.subTest(operation=operation), patch.dict(os.environ, {'COMMERCIAL_STORAGE_MODE':'secure'}, clear=True), patch.object(store, 'database_transaction') as tx, patch.object(store, '_connection') as legacy:
                cur = tx.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
                cur.rowcount = 1
                operation()
                tx.assert_called_once_with('ingestion')
                legacy.assert_not_called()
                self.assertTrue(all(c.args[0].strip().upper().startswith('INSERT ') for c in cur.execute.call_args_list))

    def test_readiness_routes_reader(self):
        with patch.dict(os.environ, {'COMMERCIAL_STORAGE_MODE':'secure'}, clear=True), patch.object(store,'database_transaction') as tx:
            tx.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value.fetchone.return_value=(None,)
            self.assertEqual(neon_readiness.read_interest_summary()['rows'],0)
            tx.assert_called_once_with('reader')

    def test_missing_table_not_silently_empty(self):
        with patch.dict(os.environ, {'COMMERCIAL_STORAGE_MODE':'secure'}, clear=True), patch.object(store,'database_transaction') as tx:
            tx.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value.execute.side_effect=RuntimeError('missing table')
            with self.assertRaises(RuntimeError): store.load_observations()
