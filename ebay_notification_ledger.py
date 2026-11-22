"""Phase 2F durable eBay notification ledger (staging only).

Stores no eBay user identifiers, raw payloads, or notification bodies.
No webhook acknowledgements or erasure actions are enabled by this module.
"""
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
    """Record an already authenticated notification, idempotently.

    Caller MUST cryptographically verify signature before invoking this.
    Requires preinstalled SQL schema. Commits on success, rolls back on error.
    Returns True if newly recorded, False if duplicate.
    """
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
        connection.rollback()
        raise LedgerError('could not durably record notification') from exc


def read_notification_status(connection, notification_id):
    """Read only, for internal testing; does not authorize a 2xx response."""
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
