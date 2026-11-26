"""Operator-only synthetic email verification; no database or scheduled sending."""
import os
import hmac
import re
import threading
from brevo_diagnostic import diagnose
from brevo_reporting import send_report

_lock = threading.Lock()
_attempted = False

def authorized(token, env=None):
    env = os.environ if env is None else env
    expected = env.get('EMAIL_TEST_OPERATOR_TOKEN', '')
    return (isinstance(token, str) and isinstance(expected, str)
            and re.fullmatch(r'[0-9a-f]{64}', expected) is not None
            and re.fullmatch(r'[0-9a-f]{64}', token) is not None
            and hmac.compare_digest(token, expected))

def ready(result):
    return (result.get('account', {}).get('category') == 'PASS'
            and result.get('senders', {}).get('category') == 'PASS'
            and result.get('sender_status') == 'ACTIVE'
            and all(result.get('configuration', {}).get(k) is True for k in
                    ('key_present','sender_format_valid','recipient_format_valid')))

def verify(token, env=None):
    if not authorized(token, env):
        raise PermissionError('Operator access required')
    return diagnose(env)

def send_test(token, confirmation, env=None):
    global _attempted
    if not authorized(token, env) or confirmation is not True:
        raise PermissionError('Operator access and explicit confirmation required')
    with _lock:
        if _attempted:
            return {'status':'ATTEMPT_ALREADY_USED'}
        if not ready(verify(token, env)):
            return {'status':'PREFLIGHT_FAILED'}
        _attempted = True  # Never retry automatically, including ambiguous delivery.
        try:
            result = send_report('Amazon Monitor Phase 2V test',
                'Synthetic Render email verification only. No product recommendation or purchase authorization.', env=env)
            return {'status':'ACCEPTED' if result.get('accepted') is True else 'UNCONFIRMED'}
        except Exception:
            return {'status':'UNCONFIRMED'}
