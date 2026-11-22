"""Phase 2E: fail-closed, read-only eBay deletion impact assessment.

No DDL, DML, logging of identifiers, or acknowledgment is performed here.
This module deliberately cannot authorize webhook POST success.
"""
from dataclasses import dataclass
from typing import Callable

# Explicitly audited tables from the uploaded repository, NOT an assertion
# about the live Neon database (which may contain additional tables).
REVIEWED_TABLES = frozenset({
    'catalogue_identity_observations', 'asin_identity_observations',
})

# Do not treat a product's source URL, brand, title or ASIN as an eBay user ID.
# Additional tables or future eBay-specific user identifiers require review.
USER_IDENTIFIER_COLUMNS = frozenset({
    'ebay_user_id', 'ebay_username', 'ebay_eias_token',
    'seller_user_id', 'seller_username', 'buyer_user_id',
})


@dataclass(frozen=True)
class ImpactAssessment:
    ready_for_processing: bool
    unknown_tables: tuple
    potential_identifier_columns: tuple
    reason: str


def assess_schema(table_columns: dict[str, set[str]]) -> ImpactAssessment:
    """Conservatively classify a snapshot of DB table/column metadata.

    A clean snapshot is NOT sufficient to acknowledge notifications: actual
    erasure handling, transaction durability and live eBay testing are missing.
    """
    if not isinstance(table_columns, dict):
        raise ValueError('schema snapshot must be a dict')
    unknown = []
    identifiers = []
    for table, columns in table_columns.items():
        if not isinstance(table, str) or not isinstance(columns, (set, frozenset, list, tuple)):
            raise ValueError('invalid schema snapshot')
        if table not in REVIEWED_TABLES:
            unknown.append(table)
        for column in columns:
            if not isinstance(column, str):
                raise ValueError('invalid column')
            if column.lower() in USER_IDENTIFIER_COLUMNS or ('ebay' in column.lower() and ('user' in column.lower() or 'seller' in column.lower())):
                identifiers.append(f'{table}.{column}')
    return ImpactAssessment(
        ready_for_processing=False,
        unknown_tables=tuple(sorted(unknown)),
        potential_identifier_columns=tuple(sorted(identifiers)),
        reason='manual_schema_review_and_durable_erasure_not_yet_implemented',
    )


def read_schema_metadata(connection_factory: Callable):
    """Read only public table metadata from Neon. No rows or personal data."""
    with connection_factory() as conn:
        with conn.cursor() as cur:
            cur.execute('''SELECT table_name, column_name FROM information_schema.columns
                           WHERE table_schema = 'public' ORDER BY table_name, ordinal_position''')
            snapshot = {}
            for table, column in cur.fetchall():
                snapshot.setdefault(table, set()).add(column)
    return assess_schema(snapshot)
