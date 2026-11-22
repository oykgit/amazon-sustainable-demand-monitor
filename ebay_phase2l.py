"""Phase 2L: explicit-policy account erasure callback for Phase 2I/2H.

OFFLINE ONLY. No live POST wiring. Operator must inventory ALL storage systems,
approve a mapping, and validate in Neon before passing this callback to Phase 2I.
"""
from dataclasses import dataclass
import re

IDENT = re.compile(r'^[a-z_][a-z0-9_]*$')
ACCOUNT_KEYS = ('userId', 'username', 'eiasToken')

class ErasurePolicyError(RuntimeError):
    pass

@dataclass(frozen=True)
class AccountStore:
    schema: str
    table: str
    identifier_column: str
    notification_key: str

    def validate(self):
        if any(not isinstance(v, str) or not IDENT.fullmatch(v)
               for v in (self.schema, self.table, self.identifier_column)):
            raise ErasurePolicyError('invalid SQL identifier in approved policy')
        if self.notification_key not in ACCOUNT_KEYS:
            raise ErasurePolicyError('unsupported account identifier mapping')
        if self.schema != 'public' or self.table == 'ebay_notification_ledger':
            raise ErasurePolicyError('store is not explicitly supported')

@dataclass(frozen=True)
class ErasurePolicy:
    stores: tuple
    inventory_reviewed: bool = False
    external_storage_reviewed: bool = False
    exact_identity_mapping_reviewed: bool = False
    no_other_account_stores: bool = False

    def validate(self):
        if not all((self.inventory_reviewed, self.external_storage_reviewed,
                    self.exact_identity_mapping_reviewed, self.no_other_account_stores)):
            raise ErasurePolicyError('independent storage and identity reviews required')
        if not isinstance(self.stores, tuple):
            raise ErasurePolicyError('stores must be an immutable tuple')
        if len(self.stores) != len(set(self.stores)):
            raise ErasurePolicyError('duplicate store policy')
        for store in self.stores:
            if not isinstance(store, AccountStore):
                raise ErasurePolicyError('invalid store policy')
            store.validate()


def make_erasure_callback(policy: ErasurePolicy):
    """Return callback for process_notification_offline(..., inspect_and_erase=...).

    Requires manually approved inventory. For each configured store, checks the
    expected column exists before deleting rows by an exact authenticated ID.
    All DELETEs run using Phase 2H's caller-owned transaction/cursor. A policy
    with zero stores is deliberately NOT supported: absence of account data is
    a separate audited policy decision, not a silent successful deletion.
    """
    if not isinstance(policy, ErasurePolicy):
        raise ErasurePolicyError('approved policy required')
    policy.validate()
    if not policy.stores:
        raise ErasurePolicyError('zero-store inventory needs separate audited no-data workflow')

    def erase(cursor, event):
        if not isinstance(event, dict) or not isinstance(event.get('notification'), dict):
            raise ErasurePolicyError('authenticated notification required')
        data = event['notification'].get('data')
        if not isinstance(data, dict):
            raise ErasurePolicyError('account identifiers missing')
        # Validate ALL mappings and table schemas before ANY destructive SQL.
        planned = []
        for store in policy.stores:
            value = data.get(store.notification_key)
            if not isinstance(value, str) or not value.strip():
                raise ErasurePolicyError('required authenticated identifier missing')
            cursor.execute('''SELECT 1 FROM information_schema.columns
                              WHERE table_schema=%s AND table_name=%s
                              AND column_name=%s''',
                           (store.schema, store.table, store.identifier_column))
            if cursor.fetchone() is None:
                raise ErasurePolicyError('approved account store schema changed')
            planned.append((store, value))
        erased = 0
        for store, value in planned:
            # Identifiers strictly validated and fixed by operator policy;
            # user data is always bound as a SQL parameter.
            sql = (f'DELETE FROM "{store.schema}"."{store.table}" '
                   f'WHERE "{store.identifier_column}" = %s')
            cursor.execute(sql, (value,))
            if not isinstance(cursor.rowcount, int) or cursor.rowcount < 0:
                raise ErasurePolicyError('could not confirm deletion count')
            erased += cursor.rowcount
        return erased
    return erase
