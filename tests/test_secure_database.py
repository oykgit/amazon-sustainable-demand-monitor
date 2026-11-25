import unittest
from unittest.mock import MagicMock
from secure_database import database_transaction, connection_parameters, DatabaseAccessError

URL='postgresql://reader:synthetic@ep-test.neon.tech/research'
ENV={'DATABASE_READER_URL':URL, 'DATABASE_INGESTION_URL':URL.replace('reader:', 'writer:'), 'DATABASE_ADMIN_URL':URL.replace('reader:', 'admin:')}

class SecureDatabaseTests(unittest.TestCase):
    def test_tls(self):
        p=connection_parameters('reader',ENV)
        self.assertEqual(p['sslmode'],'verify-full')
        self.assertEqual(p['sslrootcert'],'system')
    def test_no_fallback(self):
        with self.assertRaises(DatabaseAccessError): connection_parameters('reader',{'DATABASE_URL':URL})
    def test_invalid_role(self):
        with self.assertRaises(DatabaseAccessError): connection_parameters('other',ENV)
    def test_unsafe_urls(self):
        for url in [URL+'?sslmode=disable',URL+'#x',URL.replace('neon.tech','example.org'),URL.replace('postgresql','http'),URL.replace('/research',':1234/research'),URL.replace('reader:synthetic','reader')]:
            with self.subTest(url=url), self.assertRaises(DatabaseAccessError): connection_parameters('reader',{'DATABASE_READER_URL':url})
    def test_reader(self):
        c=MagicMock(); connect=MagicMock(return_value=c)
        with database_transaction('reader',environ=ENV,connector=connect) as actual: self.assertIs(actual,c)
        c.cursor.return_value.__enter__.return_value.execute.assert_any_call('SET TRANSACTION READ ONLY')
        c.commit.assert_not_called(); c.rollback.assert_called_once(); c.close.assert_called_once()
    def test_writer(self):
        for role,user in [('ingestion','writer'),('administrator','admin')]:
            c=MagicMock(); connect=MagicMock(return_value=c)
            with database_transaction(role,environ=ENV,connector=connect): pass
            self.assertEqual(connect.call_args.kwargs['user'],user)
            c.commit.assert_called_once(); c.close.assert_called_once()
    def test_failure(self):
        c=MagicMock()
        with self.assertRaises(DatabaseAccessError) as e:
            with database_transaction('ingestion',environ=ENV,connector=lambda **kw:c): raise ValueError('secret')
        self.assertNotIn('secret',str(e.exception)); c.rollback.assert_called_once(); c.close.assert_called_once(); c.commit.assert_not_called()
    def test_commit_failure(self):
        c=MagicMock(); c.commit.side_effect=RuntimeError('secret')
        with self.assertRaises(DatabaseAccessError):
            with database_transaction('ingestion',environ=ENV,connector=lambda **kw:c): pass
        c.rollback.assert_called_once(); c.close.assert_called_once()
    def test_rollback_failure(self):
        c=MagicMock(); c.rollback.side_effect=RuntimeError('secret')
        with self.assertRaises(DatabaseAccessError):
            with database_transaction('ingestion',environ=ENV,connector=lambda **kw:c): raise ValueError('bad')
        c.close.assert_called_once()
    def test_connection_failure(self):
        connect=MagicMock(side_effect=RuntimeError('secret'))
        with self.assertRaises(DatabaseAccessError) as e:
            with database_transaction('reader',environ=ENV,connector=connect): pass
        self.assertNotIn('secret',str(e.exception))
    def test_setup_failure(self):
        c=MagicMock(); c.cursor.return_value.__enter__.return_value.execute.side_effect=RuntimeError('bad')
        with self.assertRaises(DatabaseAccessError):
            with database_transaction('reader',environ=ENV,connector=lambda **kw:c): self.fail('must not yield')
        c.rollback.assert_called_once(); c.close.assert_called_once()
    def test_close_failure(self):
        c=MagicMock(); c.close.side_effect=RuntimeError('secret')
        with self.assertRaises(DatabaseAccessError):
            with database_transaction('reader',environ=ENV,connector=lambda **kw:c): pass
