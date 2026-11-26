"""Isolated commercial database access. No legacy credential fallback or DDL."""
import os
import certifi
from contextlib import contextmanager
from urllib.parse import urlsplit


class DatabaseAccessError(RuntimeError):
    pass


ROLE_ENV = {'reader': 'DATABASE_READER_URL', 'ingestion': 'DATABASE_INGESTION_URL',
            'administrator': 'DATABASE_ADMIN_URL'}


def connection_parameters(role, environ=None):
    env = os.environ if environ is None else environ
    if role not in ROLE_ENV:
        raise DatabaseAccessError('Unsupported database role.')
    try:
        raw = env[ROLE_ENV[role]]
        if not isinstance(raw, str) or any(ord(c) < 33 for c in raw):
            raise ValueError()
        url = urlsplit(raw)
        # No URI options: callers cannot override TLS, service, host or session settings.
        if (url.scheme not in ('postgres', 'postgresql') or not url.hostname
                or not url.username or not url.password or not url.path.strip('/')
                or url.query or url.fragment or ',' in url.netloc
                or url.port not in (None, 5432)):
            raise ValueError()
        from urllib.parse import unquote
        host = url.hostname
        if not host.endswith('.neon.tech') or not all(c.isascii() and (c.isalnum() or c in '.-') for c in host):
            raise ValueError()
        user, password, db = map(unquote, (url.username, url.password, url.path[1:]))
        if any(not x or '\x00' in x for x in (user, password, db)) or '/' in db:
            raise ValueError()
        return dict(host=host, port=5432, user=user, password=password, dbname=db,
                    sslmode='verify-full', sslrootcert=certifi.where(), channel_binding='require', connect_timeout=8,
                    application_name='amazon_monitor_' + role)
    except (KeyError, ValueError, TypeError, AttributeError):
        raise DatabaseAccessError('Missing or invalid role-specific database configuration.') from None


@contextmanager
def database_transaction(role, *, environ=None, connector=None):
    params = connection_parameters(role, environ)
    conn = None
    try:
        if connector is None:
            import psycopg
            connector = psycopg.connect
        conn = connector(**params)
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute('SET TRANSACTION READ ONLY' if role == 'reader' else 'SET TRANSACTION READ WRITE')
            cur.execute("SET LOCAL statement_timeout = '30s'")
            cur.execute("SET LOCAL lock_timeout = '5s'")
            cur.execute("SET LOCAL search_path = pg_catalog, public")
        yield conn
        if role == 'reader':
            conn.rollback()
        else:
            conn.commit()
    except BaseException as exc:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        if not isinstance(exc, Exception):
            raise
        raise DatabaseAccessError('Database operation failed; write outcome may require reconciliation.') from None
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                raise DatabaseAccessError('Database connection termination failed; reconcile outcome.') from None
