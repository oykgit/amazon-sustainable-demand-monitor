"""Read-only production inventory and optional token probe; never authorizes activation."""
import argparse
import json
from secure_database import database_transaction
from ebay_public_keys import EbayPublicKeyClient

# pg_catalog exposes metadata even for tables inaccessible to the reader.
SQL = """
SELECT n.nspname, c.relname, c.relkind, a.attname,
       pg_catalog.format_type(a.atttypid,a.atttypmod),
       pg_catalog.has_table_privilege(current_user,c.oid,'SELECT'),
       pg_catalog.has_table_privilege(current_user,c.oid,'DELETE')
FROM pg_catalog.pg_class c
JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
LEFT JOIN pg_catalog.pg_attribute a ON a.attrelid=c.oid
 AND a.attnum>0 AND NOT a.attisdropped
WHERE c.relkind IN ('r','p','v','m','f')
 AND n.nspname NOT IN ('pg_catalog','information_schema')
 AND n.nspname NOT LIKE 'pg_toast%%' AND n.nspname NOT LIKE 'pg_temp_%%'
ORDER BY n.nspname,c.relname,a.attnum
"""

def inventory(transaction=database_transaction):
    with transaction('reader') as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_user, current_setting('transaction_read_only')")
            if cur.fetchone() != ('monitor_reader','on'):
                raise ValueError('reader guard failed')
            cur.execute(SQL)
            rows=cur.fetchall()
    if not rows or len(rows)>10000:
        raise ValueError('inventory empty or too large')
    tables={}
    for schema,name,kind,column,datatype,select,delete in rows:
        key=(schema,name)
        entry=tables.setdefault(key,dict(schema=schema,table=name,kind=kind,
            reader_select=select,reader_delete=delete,columns=[]))
        if delete is not False:
            raise ValueError('unexpected reader delete permission')
        if column is not None:
            entry['columns'].append(dict(name=column,type=datatype))
    return list(tables.values())

def run(*, db=False, oauth=False, inventory_fn=inventory, client_factory=EbayPublicKeyClient):
    result={'phase':'3.0A','inventory_status':'NOT_RUN','oauth_status':'NOT_RUN',
            'production_ready':False,'post_activation_authorized':False,
            'browse_collection_authorized':False,'database_writes':0,
            'storage_inventory_approved':False,'restoration_enforcement_verified':False,
            'live_signature_verified':False}
    if db:
        try:
            result['relations']=inventory_fn()
            result['inventory_status']='METADATA_COLLECTED_REVIEW_REQUIRED'
        except Exception:
            result['inventory_status']='FAIL_OR_UNCONFIRMED'
    if oauth:
        try:
            # Existing client requests a token only; no marketplace data or token output.
            token=client_factory()._access_token()
            if not isinstance(token,str) or not token:
                raise ValueError('no token')
            result['oauth_status']='PASS_TOKEN_ISSUED'
        except Exception:
            result['oauth_status']='FAIL_OR_UNCONFIRMED'
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--db',action='store_true');p.add_argument('--oauth',action='store_true');a=p.parse_args()
    result=run(db=a.db,oauth=a.oauth)
    print(json.dumps(result,indent=2))
    raise SystemExit(int(any(result[k]=='FAIL_OR_UNCONFIRMED' for k in ('inventory_status','oauth_status'))))
