"""Read-only Brevo preflight; never prints provider content or credentials."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('redirect refused')

def probe(path, key, opener):
    try:
        with opener(Request('https://api.brevo.com/v3/'+path, headers={'api-key':key,'Accept':'application/json'}), timeout=20) as response:
            status=response.status
            raw=response.read(262145)
            if status != 200 or len(raw)>262144:
                return {'http_status':status,'category':'UNEXPECTED_RESPONSE'}, None
            data=json.loads(raw)
            if not isinstance(data,dict): raise ValueError('invalid response')
            return {'http_status':200,'category':'PASS'}, data
    except HTTPError as exc:
        status=exc.code
        category={401:'AUTHENTICATION_REJECTED',403:'ACCESS_FORBIDDEN',429:'RATE_LIMIT',400:'BAD_REQUEST'}.get(status,'HTTP_ERROR')
        try:
            raw=exc.read(16385)
            if len(raw)<=16384:
                data=json.loads(raw)
                msg=data.get('message','') if isinstance(data,dict) else ''
                if status in (401,403) and isinstance(msg,str) and 'ip address' in msg.lower() and any(x in msg.lower() for x in ('unauthoriz','not authoriz','not allow','blocked','unrecognized','not recogniz')):
                    category='IP_RESTRICTION_REPORTED'
        except Exception: pass
        finally: exc.close()
        return {'http_status':status,'category':category},None
    except (URLError,TimeoutError,OSError):
        return {'http_status':None,'category':'NETWORK_OR_TLS_FAILURE'},None
    except Exception:
        return {'http_status':None,'category':'INVALID_OR_UNCONFIRMED_RESPONSE'},None

def diagnose(env=None, opener=None):
    env=os.environ if env is None else env
    key,sender,recipient=(env.get(k,'').strip() for k in ('BREVO_API_KEY','BREVO_SENDER_EMAIL','REPORT_RECIPIENT_EMAIL'))
    valid=lambda x: x.count('@')==1 and all(x.split('@')) and not any(c.isspace() for c in x)
    result={'configuration':{'key_present':bool(key),'sender_format_valid':valid(sender),'recipient_format_valid':valid(recipient)},'account':{'category':'NOT_RUN'},'senders':{'category':'NOT_RUN'},'sender_status':'NOT_RUN','email_sent':False}
    if not key or any(c.isspace() for c in key):
        result['account']['category']='MISSING_OR_INVALID_KEY_FORMAT'; return result
    opener=opener or build_opener(NoRedirect()).open
    result['account'],account=probe('account',key,opener)
    if account is None: return result
    result['senders'],data=probe('senders',key,opener)
    if data is not None:
        rows=data.get('senders')
        if isinstance(rows,list):
            matches=[r for r in rows if isinstance(r,dict) and isinstance(r.get('email'),str) and r['email'].casefold()==sender.casefold()]
            result['sender_status']='ACTIVE' if len(matches)==1 and matches[0].get('active') is True else 'NOT_CONFIRMED'
    return result

if __name__=='__main__':
    print(json.dumps(diagnose(),indent=2))
