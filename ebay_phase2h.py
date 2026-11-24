
"""Phase 2R.8: Hardened transactional deletion workflow engine.

Offline and staging use only.

No live HTTP acknowledgments or production erasure authorization.

Preserves SQL compatibility with earlier regression tests.
"""

from dataclasses import dataclass
from typing import Callable


class DeletionProcessingError(RuntimeError):
    """Deletion processing could not safely complete."""


@dataclass(frozen=True)
class DeletionOutcome:
    notification_fingerprint: str
    state: str
    erased_records: int
    acknowledged: bool = False


def _rollback_safely(connection):
    """Attempt rollback without masking the original failure.

    A failed rollback means the connection must not be reused.
    """
    try:
        connection.rollback()
        return True

    except Exception:
        try:
            connection.close()
        except Exception:
            pass

        return False


def process_verified_deletion(
    connection,
    notification_id: str,
    inspect_and_erase: Callable,
    *,
    storage_inventory_approved: bool = False,
) -> DeletionOutcome:
    """Process an authenticated, durably staged notification.

    The caller must authenticate the notification before calling.

    The erasure handler must use the supplied transaction and
    must not commit independently.

    No result from this function authorizes HTTP acknowledgment.
    """

    from ebay_notification_ledger import notification_fingerprint

    digest = notification_fingerprint(notification_id)

    if (
        not storage_inventory_approved
        or not callable(inspect_and_erase)
    ):
        raise DeletionProcessingError(
            "approved full storage inventory "
            "and erasure handler required"
        )

    try:
        with connection.cursor() as cur:

            cur.execute(
                """
                SELECT status
                FROM public.ebay_notification_ledger
                WHERE notification_fingerprint = %s
                FOR UPDATE
                """,
                (digest,),
            )

            row = cur.fetchone()

            if row is None:
                raise DeletionProcessingError(
                    "notification must be durably staged first"
                )

            if row[0] == "completed":
                connection.commit()

                return DeletionOutcome(
                    digest,
                    "completed",
                    0,
                )

            if row[0] not in (
                "received",
                "failed",
                "processing",
            ):
                raise DeletionProcessingError(
                    "unknown notification state"
                )

            cur.execute(
                """
                UPDATE public.ebay_notification_ledger
                SET status='processing',
                    updated_at = now()
                WHERE notification_fingerprint = %s
                """,
                (digest,),
            )

            erased = inspect_and_erase(
                cur,
                notification_id,
            )

            if (
                isinstance(erased, bool)
                or not isinstance(erased, int)
                or erased < 0
            ):
                raise DeletionProcessingError(
                    "erasure handler returned invalid result"
                )

            cur.execute(
                """
                UPDATE public.ebay_notification_ledger
                SET status='completed',
                    updated_at = now()
                WHERE notification_fingerprint = %s
                """,
                (digest,),
            )

        connection.commit()

        return DeletionOutcome(
            digest,
            "completed",
            erased,
        )

    except Exception as exc:

        rollback_succeeded = _rollback_safely(
            connection
        )

        if not rollback_succeeded:
            raise DeletionProcessingError(
                "deletion transaction did not complete; "
                "rollback failed; discard connection "
                "and reconcile durable state"
            ) from exc

        raise DeletionProcessingError(
            "deletion transaction did not complete"
        ) from exc
