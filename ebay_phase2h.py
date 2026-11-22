"""Phase 2H: fail-closed, transactional deletion workflow engine.

Staging only. Never call this from a live webhook until the storage inventory,
verified eBay identity mapping, and live database tests are complete.
"""
from dataclasses import dataclass
from typing import Callable


class DeletionProcessingError(RuntimeError):
    pass


@dataclass(frozen=True)
class DeletionOutcome:
    notification_fingerprint: str
    state: str
    erased_records: int
    acknowledged: bool = False


def process_verified_deletion(connection, notification_id: str,
                              inspect_and_erase: Callable, *,
                              storage_inventory_approved: bool = False) -> DeletionOutcome:
    """Process verified notification in one transaction with an approved handler.

    `inspect_and_erase(cur, notification_id)` must identify all matching user
    data across approved stores and erase it in this same transaction. Return
    nonnegative number of records erased. It must raise if any storage location
    is unreviewed or any erasure cannot be completed. No HTTP success here.

    The caller MUST have verified the eBay signature and extracted the ID from
    the authenticated payload. `storage_inventory_approved` is an explicit
    operator approval, never inferred from a zero-count query.
    """
    from ebay_notification_ledger import notification_fingerprint
    digest = notification_fingerprint(notification_id)
    if not storage_inventory_approved or not callable(inspect_and_erase):
        raise DeletionProcessingError('approved full storage inventory and erasure handler required')
    try:
        with connection.cursor() as cur:
            # Serialize competing handlers on the same notification row.
            cur.execute('''SELECT status FROM public.ebay_notification_ledger
                           WHERE notification_fingerprint = %s FOR UPDATE''', (digest,))
            row = cur.fetchone()
            if row is None:
                raise DeletionProcessingError('notification must be durably staged first')
            if row[0] == 'completed':
                connection.commit()
                return DeletionOutcome(digest, 'completed', 0)
            if row[0] not in ('received', 'failed', 'processing'):
                raise DeletionProcessingError('unknown notification state')
            cur.execute('''UPDATE public.ebay_notification_ledger
                           SET status='processing', updated_at=now()
                           WHERE notification_fingerprint=%s''', (digest,))
            erased = inspect_and_erase(cur, notification_id)
            if isinstance(erased, bool) or not isinstance(erased, int) or erased < 0:
                raise DeletionProcessingError('erasure handler returned invalid result')
            cur.execute('''UPDATE public.ebay_notification_ledger
                           SET status='completed', updated_at=now()
                           WHERE notification_fingerprint=%s''', (digest,))
        connection.commit()
        return DeletionOutcome(digest, 'completed', erased)
    except Exception as exc:
        connection.rollback()
        raise DeletionProcessingError('deletion transaction did not complete') from exc
