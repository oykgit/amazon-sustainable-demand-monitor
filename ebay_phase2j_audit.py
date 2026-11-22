"""Phase 2J local, read-only release gate. Never connects to eBay or Neon.

Run: python ebay_phase2j_audit.py
It checks the checked-out repository, not the deployed Render revision.
"""
import importlib.util
import json
from pathlib import Path

REQUIRED = ('ebay_webhook.py','ebay_signature.py','ebay_public_keys.py',
            'ebay_notification_ledger.py','ebay_deletion_safeguards.py',
            'ebay_phase2g.py','ebay_phase2h.py','ebay_phase2i.py')

def audit(root='.'):
    root = Path(root)
    checks = {}
    for name in REQUIRED:
        checks['file:' + name] = (root / name).is_file()
    # Syntax-check only; do not import modules or trigger network activity.
    for name in REQUIRED:
        path = root / name
        if path.is_file():
            try:
                compile(path.read_bytes(), str(path), 'exec')
                checks['syntax:' + name] = True
            except (SyntaxError, ValueError, UnicodeError):
                checks['syntax:' + name] = False
    webhook = (root / 'ebay_webhook.py')
    if webhook.is_file():
        source = webhook.read_text(encoding='utf-8')
        checks['webhook:challenge_handler_present'] = 'def challenge_response(' in source
        checks['webhook:post_handler_present'] = 'def do_POST(' in source
        checks['webhook:post_disabled_by_default'] = (
            "os.getenv('EBAY_PHASE2D_AUTH_TEST', '') != '1'" in source
            and "'notification_processing_not_enabled'" in source
        )
    return {
        'phase': '2J', 'kind': 'local_static_audit',
        'checks': checks,
        'local_static_checks_passed': bool(checks) and all(checks.values()),
        'production_ready': False,
        'blocking_evidence': [
            'Approved inventory of all eBay-derived user data stores and retention paths',
            'Audited account-identifier matching and transactional erasure callback',
            'Real eBay notification payload and signature compatibility verified',
            'Live Neon rollback, duplicate, and completion tests performed',
            'Live HTTP POST integration with correct retry/acknowledgment semantics',
            'Always-on HTTPS hosting and monitored webhook delivery',
            'Production credentials configured privately and eBay keyset activated',
        ],
    }

if __name__ == '__main__':
    print(json.dumps(audit(), indent=2, sort_keys=True))
