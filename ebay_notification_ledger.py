"""Offline durable notification ledger; no HTTP acknowledgment authorization."""
import hashlib
import re

_ID = re.compile(r'^[A-Za-z0-9._:-]{1,256}$')
_ALLOWED = {'received', 'processing', 'completed', 'failed'}


class LedgerError(RuntimeError):
    pass


def notification_fingerprint(notification_id):
    if not isinstance(notification_id, str) or not _ID.fullmatch(notification_id):
        raise ValueError('invalid notification id')
    return hashlib.sha256(notification_id.encode('utf-8')).hexdigest()


def record_verified_notification(connection, notification_id):
    """Record an already authenticated notification, idempotently."""
    digest = notification_fingerprint(notification_id)
    try:
        with connection.cursor() as cur:
            cur.execute('''INSERT INTO public.ebay_notification_ledger
                (notification_fingerprint, status)
                VALUES (%s, 'received')
                ON CONFLICT (notification_fingerprint) DO NOTHING
                RETURNING notification_fingerprint''', (digest,))
            inserted = cur.fetchone() is not None
        connection.commit()
        return inserted
    except Exception as exc:
        try:
            connection.rollback()
        except Exception:
            try:
                connection.close()
            except Exception:
                pass
            raise LedgerError('could not durably record notification; rollback failed; discard connection and reconcile durable state') from exc
        raise LedgerError('could not durably record notification') from exc


def read_notification_status(connection, notification_id):
    """Read only; does not authorize a 2xx response."""
    digest = notification_fingerprint(notification_id)
    with connection.cursor() as cur:
        cur.execute('''SELECT status FROM public.ebay_notification_ledger
                       WHERE notification_fingerprint = %s''', (digest,))
        row = cur.fetchone()
    if row is None:
        return None
    if row[0] not in _ALLOWED:
        raise LedgerError('unknown ledger status')
    return row[0]
