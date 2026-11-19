"""Keepa readiness only: no paid access or API calls."""
def status():
    return {'provider':'Keepa','subscription_enabled':False,'network_enabled':False,'paid_calls':0}
def fetch_history(*args,**kwargs):
    raise RuntimeError('Keepa access disabled until explicitly authorized')
