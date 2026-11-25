"""Disposable CI PostgreSQL only; no production credentials consumed."""
import os
import unittest
from unittest.mock import patch
import persistent_store as store
from secure_database import database_transaction, DatabaseAccessError

@unittest.skipUnless(os.getenv('PHASE2T3A_LOCAL_PG') == '1', 'Disposable CI database only')
class PostgresTests(unittest.TestCase):
    def test_readonly_and_permissions(self):
        import psycopg
        params = dict(host='127.0.0.1', port=5432, dbname='storage_test', user='storage_test', password='local_test_only', sslmode='disable')
        with psycopg.connect(**params) as conn:
            conn.execute('CREATE ROLE storage_reader LOGIN PASSWORD \'reader_test_only\'')
            conn.execute('CREATE ROLE storage_writer LOGIN PASSWORD \'writer_test_only\'')
            conn.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
            store._init(conn)
            conn.execute('GRANT USAGE ON SCHEMA public TO storage_reader, storage_writer')
            conn.execute('GRANT SELECT ON catalogue_identity_observations TO storage_reader, storage_writer')
            conn.execute('GRANT INSERT ON catalogue_identity_observations TO storage_writer')
        def local_params(role, environ=None):
            return dict(params, user='storage_reader' if role=='reader' else 'storage_writer', password='reader_test_only' if role=='reader' else 'writer_test_only')
        with patch('secure_database.connection_parameters', side_effect=local_params), patch.dict(os.environ, {'COMMERCIAL_STORAGE_MODE':'secure'}, clear=True):
            record={'observed_at_utc':'2000-01-01T00:00:00+00:00','barcode':'0000000000000','source':'SYNTHETIC_TEST'}
            self.assertEqual(store.save_observations([record]),1)
            self.assertEqual(store.save_observations([record]),0)
            self.assertEqual(len(store.load_observations()),1)
            with database_transaction('reader') as conn:
                self.assertEqual(conn.execute('SHOW transaction_read_only').fetchone()[0],'on')
            for role, sql in [('reader','DELETE FROM catalogue_identity_observations'),('ingestion','DELETE FROM catalogue_identity_observations'),('ingestion','CREATE TABLE forbidden (id int)')]:
                with self.assertRaises(DatabaseAccessError):
                    with database_transaction(role) as conn: conn.execute(sql)
            self.assertEqual(len(store.load_observations()),1)
