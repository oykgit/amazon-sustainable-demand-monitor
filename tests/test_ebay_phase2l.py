import unittest
from ebay_phase2l import AccountStore, ErasurePolicy, ErasurePolicyError, make_erasure_callback

STORE = AccountStore('public','ebay_user_cache','ebay_user_id','userId')
def policy(stores=(STORE,), **kw):
    flags=dict(inventory_reviewed=True,external_storage_reviewed=True,
               exact_identity_mapping_reviewed=True,no_other_account_stores=True)
    flags.update(kw)
    return ErasurePolicy(stores, **flags)
class Cursor:
    def __init__(self, schema_ok=True, count=2):
        self.schema_ok=schema_ok; self.rowcount=count; self.queries=[]
    def execute(self,sql,params): self.queries.append((sql,params))
    def fetchone(self): return (1,) if self.schema_ok else None
EVENT={'notification':{'data':{'userId':'abc-123'}}}
class Phase2LTests(unittest.TestCase):
    def test_refuses_unapproved_inventory(self):
        with self.assertRaises(ErasurePolicyError): make_erasure_callback(policy(inventory_reviewed=False))
    def test_refuses_empty_policy(self):
        with self.assertRaises(ErasurePolicyError): make_erasure_callback(policy(stores=()))
    def test_refuses_sql_injection_identifiers(self):
        with self.assertRaises(ErasurePolicyError): make_erasure_callback(policy(stores=(AccountStore('public','x;DROP','id','userId'),)))
    def test_refuses_internal_ledger(self):
        with self.assertRaises(ErasurePolicyError): make_erasure_callback(policy(stores=(AccountStore('public','ebay_notification_ledger','notification_fingerprint','userId'),)))
    def test_exact_match_parameterized_delete(self):
        cur=Cursor(); result=make_erasure_callback(policy())(cur,EVENT)
        self.assertEqual(result,2)
        self.assertIn('DELETE FROM "public"."ebay_user_cache"',cur.queries[-1][0])
        self.assertEqual(cur.queries[-1][1],('abc-123',))
    def test_missing_identifier_blocks_all_delete(self):
        cur=Cursor()
        with self.assertRaises(ErasurePolicyError): make_erasure_callback(policy())(cur,{'notification':{'data':{}}})
        self.assertFalse(any('DELETE' in q for q,_ in cur.queries))
    def test_schema_drift_blocks_all_delete(self):
        cur=Cursor(schema_ok=False)
        with self.assertRaises(ErasurePolicyError): make_erasure_callback(policy())(cur,EVENT)
        self.assertFalse(any('DELETE' in q for q,_ in cur.queries))
    def test_multiple_stores_prevalidated(self):
        second=AccountStore('public','ebay_account_notes','ebay_username','username')
        cur=Cursor()
        with self.assertRaises(ErasurePolicyError):
            make_erasure_callback(policy(stores=(STORE,second)))(cur,EVENT)
        self.assertFalse(any('DELETE' in q for q,_ in cur.queries))
    def test_rejects_unconfirmed_rowcount(self):
        cur=Cursor(count=-1)
        with self.assertRaises(ErasurePolicyError): make_erasure_callback(policy())(cur,EVENT)
if __name__=='__main__': unittest.main()
