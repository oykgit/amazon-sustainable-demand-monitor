"""Operator-triggered, non-activating operational checks. No production writes."""
import argparse
import json
import os
from urllib.request import Request, build_opener, HTTPRedirectHandler
from secure_database import database_transaction, connection_parameters

HEALTH = 'https://amazon-monitor-ebay-webhook.onrender.com/health'
BREVO = 'https://api.brevo.com/v3/smtp/email'
TABLES = ('asin_identity_observations','asin_price_snapshots','asin_research_watchlist',
          'catalogue_identity_observations','search_interest_observations','asin_price_feed_provenance')

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Redirect refused')

def request_json(request, expected, opener=None):
    with (opener or build_opener(NoRedirect()).open)(request, timeout=20) as response:
        if response.status != expected:
            raise ValueError('Unexpected status')
        raw = response.read(65537)
        if len(raw)>65536:
            raise ValueError('Response too large')
        result=json.loads(raw)
        if not isinstance(result,dict):
            raise ValueError('Invalid response')
        return result

def health(opener=None):
    result=request_json(Request(HEALTH),200,opener)
    return result.get('status')=='phase2d_authentication_integrated' and result.get('post_enabled') is False

def email(env, opener=None):
    key,sender,recipient=(env.get(k,'').strip() for k in ('BREVO_API_KEY','BREVO_SENDER_EMAIL','REPORT_RECIPIENT_EMAIL'))
    if not key or any(x.count('@')!=1 or any(c.isspace() for c in x) for x in (sender,recipient)):
        raise ValueError('Missing configuration')
    body={'sender':{'email':sender},'to':[{'email':recipient}], 'subject':'Amazon Monitor Phase 2V test',
          'textContent':'Controlled operational test only. No product recommendation or purchase authorization.'}
    result=request_json(Request(BREVO,data=json.dumps(body).encode(),headers={'api-key':key,'Content-Type':'application/json'},method='POST'),201,opener)
    return isinstance(result.get('messageId'),str) and bool(result['messageId'].strip())

CONFLICT_COLUMNS = {
    'asin_identity_observations': ('source','asin','marketplace','observed_at_utc'),
    'asin_price_snapshots': ('asin','marketplace','observed_at_utc','source_note'),
    'catalogue_identity_observations': ('source','barcode','observed_at_utc'),
    'search_interest_observations': ('market','keyword','month'),
}
WATCHLIST = 'asin_research_watchlist'
PROVENANCE = 'asin_price_feed_provenance'

def expected_table_permissions(role, table):
    # SELECT, INSERT, DELETE, TRUNCATE, UPDATE
    if role == 'reader':
        return (table != PROVENANCE, False, False, False, False)
    return (table == WATCHLIST, True, False, False, table == WATCHLIST)

def database(env):
    params=[connection_parameters(r,env) for r in ('reader','ingestion')]
    if [p['user'] for p in params] != ['monitor_reader','monitor_ingestion'] or any(params[0][k]!=params[1][k] for k in ('host','dbname')):
        return False
    for role in ('reader','ingestion'):
        with database_transaction(role,environ=env) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_user, rolcanlogin AND NOT (rolsuper OR rolcreaterole OR rolcreatedb OR rolreplication OR rolbypassrls OR rolinherit) FROM pg_roles WHERE rolname=current_user")
                if cur.fetchone() != ('monitor_'+role, True): return False
                cur.execute("SELECT has_schema_privilege(current_user,'public','CREATE'), has_database_privilege(current_user,current_database(),'CREATE'), EXISTS (SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=current_user))")
                if cur.fetchone() != (False,False,False): return False
                for table in TABLES + ('ebay_notification_ledger','playing_with_neon'):
                    name='public.'+table
                    cur.execute("SELECT to_regclass(%s)",(name,))
                    if cur.fetchone()[0] is None: return False
                    cur.execute("SELECT has_table_privilege(current_user,%s,'SELECT'), has_table_privilege(current_user,%s,'INSERT'), has_table_privilege(current_user,%s,'DELETE'), has_table_privilege(current_user,%s,'TRUNCATE'), has_table_privilege(current_user,%s,'UPDATE')",(name,)*5)
                    expected=expected_table_permissions(role,table) if table in TABLES else (False,)*5
                    if cur.fetchone()!=expected: return False
                    cur.execute("SELECT a.attname, has_column_privilege(current_user,%s,a.attname,'SELECT'), has_column_privilege(current_user,%s,a.attname,'INSERT'), has_column_privilege(current_user,%s,a.attname,'UPDATE') FROM pg_attribute a WHERE a.attrelid=to_regclass(%s) AND a.attnum>0 AND NOT a.attisdropped",(name,)*4)
                    rows=cur.fetchall()
                    if not rows: return False
                    for column,select,insert,update in rows:
                        if (select,insert,update)!=(expected[0] or (role=='ingestion' and column in CONFLICT_COLUMNS.get(table,())),expected[1],expected[4]): return False
                    if role=='ingestion' and not set(CONFLICT_COLUMNS.get(table,())).issubset({r[0] for r in rows}): return False
                cur.execute("SELECT has_sequence_privilege(current_user,'public.asin_price_snapshots_id_seq','USAGE'), has_sequence_privilege(current_user,'public.asin_price_snapshots_id_seq','SELECT'), has_sequence_privilege(current_user,'public.asin_price_snapshots_id_seq','UPDATE')")
                if cur.fetchone()!=(role=='ingestion',False,False): return False
    return True

def run(*, hosted=False, mail=False, db=False, env=None):
    env=os.environ if env is None else env
    checks={}
    for name,enabled,fn in [('hosted_health',hosted,health),('brevo_acceptance',mail,lambda:email(env)),('database_metadata',db,lambda:database(env))]:
        try: checks[name]=('PASS' if fn() is True else 'FAIL') if enabled else 'NOT_RUN'
        except Exception: checks[name]='FAIL_OR_UNCONFIRMED'
    return {'phase':'2V','checks':checks,'email_inbox_verified':False,'restoration_enforcement_verified':False,
            'ebay_approval_verified':False,'production_ready':False,'post_activation_authorized':False,
            'production_database_writes':0}

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--hosted',action='store_true');p.add_argument('--mail',action='store_true');p.add_argument('--db',action='store_true');a=p.parse_args()
    result=run(hosted=a.hosted,mail=a.mail,db=a.db);print(json.dumps(result,indent=2))
    raise SystemExit(int(any(v.startswith('FAIL') for v in result['checks'].values())))
