"""Phase 2K: read-only Neon account-data inventory and fail-closed erasure policy.

No deletion is authorized by this module. The five known research tables are
product-centric, not a verified inventory of all storage systems. No-op deletion
must never be inferred from a clean SQL scan.
"""
from dataclasses import dataclass
import json
import re

KNOWN_RESEARCH_TABLES = frozenset({
    'asin_identity_observations', 'asin_price_snapshots',
    'asin_research_watchlist', 'catalogue_identity_observations',
    'search_interest_observations',
})
KNOWN_INTERNAL_TABLES = frozenset({'ebay_notification_ledger'})
SUSPICIOUS = re.compile(r'(ebay|seller|buyer|account|username|eias|user[_]?id|token|payload|notification)', re.I)


@dataclass(frozen=True)
class InventoryResult:
    table_count: int
    unknown_tables: tuple
    candidate_columns: tuple
    extra_schemas: tuple
    account_erasure_ready: bool = False
    post_activation_authorized: bool = False

    def as_dict(self):
        return {
            'table_count': self.table_count,
            'unknown_tables': list(self.unknown_tables),
            'candidate_columns': list(self.candidate_columns),
            'extra_schemas': list(self.extra_schemas),
            'account_erasure_ready': False,
            'post_activation_authorized': False,
            'required_manual_reviews': [
                'All Neon databases, branches, schemas, tables, views and backups',
                'Application logs, Render logs, exports, files and third-party services',
                'Future eBay API persistence and account-identifier mapping',
                'Verified account-data erasure callback and live transactional tests',
            ],
        }


def assess_inventory(rows, extra_schemas=()):
    """Assess (schema, table, column) metadata only, never actual personal data."""
    mapping = {}
    for schema, table, column in rows:
        if not all(isinstance(x, str) and x for x in (schema, table, column)):
            raise ValueError('invalid metadata row')
        mapping.setdefault((schema, table), set()).add(column)
    known = KNOWN_RESEARCH_TABLES | KNOWN_INTERNAL_TABLES
    unknown = tuple(sorted(f'{s}.{t}' for s, t in mapping if s != 'public' or t not in known))
    candidates = tuple(sorted(
        f'{s}.{t}.{c}' for (s, t), columns in mapping.items() for c in columns
        if SUSPICIOUS.search(c) and not (s == 'public' and t == 'ebay_notification_ledger'
                                        and c == 'notification_fingerprint')
    ))
    return InventoryResult(len(mapping), unknown, candidates, tuple(sorted(extra_schemas)))


def inspect_neon_read_only(connection):
    """Read schema metadata only; caller manages connection. Never commit/write."""
    with connection.cursor() as cur:
        cur.execute('''SELECT table_schema, table_name, column_name
                       FROM information_schema.columns
                       WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
                       ORDER BY table_schema, table_name, ordinal_position''')
        rows = cur.fetchall()
        cur.execute('''SELECT schema_name FROM information_schema.schemata
                       WHERE schema_name NOT IN ('public', 'information_schema', 'pg_catalog')
                       AND schema_name NOT LIKE 'pg_toast%'
                       AND schema_name NOT LIKE 'pg_temp%'
                       ORDER BY schema_name''')
        extra_schemas = [r[0] for r in cur.fetchall()]
    return assess_inventory(rows, extra_schemas)


def refuse_unapproved_erasure(cursor, authenticated_event):
    """Deliberate guard compatible with Phase 2I callback signature.

    Never returns zero to imply a deletion was completed. The audited handler
    must be built after full storage inventory and identity mapping are known.
    """
    raise RuntimeError('Phase 2K is inventory-only: account-data erasure is not authorized')


def render_report(result):
    return json.dumps(result.as_dict(), indent=2, sort_keys=True)
