"""V1.22 commercial provider configuration diagnostics. No network or database calls."""
import os

PROVIDERS = {
    'Keepa': {'secret': 'KEEPA_API_KEY', 'host': 'api.keepa.com', 'purpose': 'Amazon historical price and rank data'},
    'DataForSEO': {'secret': 'DATAFORSEO_PASSWORD', 'identity': 'DATAFORSEO_LOGIN', 'host': 'api.dataforseo.com', 'purpose': 'Provider-specific Amazon research endpoints'},
}

def readiness(provider, environ=None):
    env = os.environ if environ is None else environ
    if provider not in PROVIDERS:
        raise ValueError('Unsupported provider')
    cfg = PROVIDERS[provider]
    credential = bool(env.get(cfg['secret'], '').strip())
    identity = bool(env.get(cfg.get('identity', ''), '').strip()) if 'identity' in cfg else True
    raw = env.get('RESEARCH_PROVIDER_MAX_DAILY_REQUESTS', '0')
    try:
        cap = int(raw)
    except (ValueError, TypeError):
        cap = 0
    cap = max(0, min(cap, 10000))
    enabled = env.get('RESEARCH_PROVIDER_NETWORK_ENABLED', '').lower() == 'true'
    # Network calls are intentionally not implemented in this release.
    return {
        'mode': 'COMMERCIAL_PROVIDER_CONFIGURATION_READ_ONLY',
        'provider': provider,
        'provider_host': cfg['host'],
        'purpose': cfg['purpose'],
        'credentials_configured': credential and identity,
        'daily_request_budget': cap,
        'network_requested_by_configuration': enabled,
        'network_requests': 0,
        'database_writes': 0,
        'purchases_enabled': False,
        'status': 'CONFIGURATION_READY_NOT_CONNECTED' if credential and identity and cap > 0 else 'CONFIGURATION_INCOMPLETE',
        'note': 'No commercial API calls are implemented in V1.22. Credentials are never displayed or transmitted. No historical data is retrieved.'
    }
