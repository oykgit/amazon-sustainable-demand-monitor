"""Phase 2M: non-destructive integration preflight. Never enables live POST.

Uses actual Phase 2D/I/H/L code and simulated connection/key dependencies.
This is an offline gate, NOT a live eBay or Neon certification.
"""
from dataclasses import dataclass
import importlib.util
import json
from pathlib import Path

REQUIRED = ('ebay_webhook.py','ebay_signature.py','ebay_public_keys.py',
            'ebay_notification_ledger.py','ebay_phase2h.py','ebay_phase2i.py',
            'ebay_phase2k.py','ebay_phase2l.py')
BLOCKERS = (
    'Independent inventory of every eBay account-data store, logs, backups and exports',
    'Operator-approved identity mapping and erasure policy, including no-data path if applicable',
    'Verified real eBay notification payload, signature format and public-key retrieval',
    'Live Neon transactional tests using disposable test records and verified rollback',
    'Live HTTP retry and acknowledgment behavior tested without premature 2xx',
    'Always-on HTTPS hosting with delivery monitoring',
    'Private production credentials and eBay keyset approval',
)


def inspect_repository(root):
    root = Path(root)
    files = {name: (root / name).is_file() for name in REQUIRED}
    syntax = {}
    for name, exists in files.items():
        if not exists:
            syntax[name] = False
            continue
        try:
            compile((root / name).read_bytes(), str(root / name), 'exec')
            syntax[name] = True
        except (OSError, SyntaxError, UnicodeError):
            syntax[name] = False
    webhook = (root / 'ebay_webhook.py')
    source = webhook.read_text(encoding='utf-8') if webhook.is_file() else ''
    # Structural guard only, not a proof of runtime behavior.
    default_disabled = "'post_enabled': False" in source and "notification_processing_not_enabled" in source
    return {
        'phase': '2M', 'kind': 'offline_integration_preflight',
        'required_files': files, 'python_syntax': syntax,
        'post_disabled_static_guard': default_disabled,
        'offline_preflight_passed': all(files.values()) and all(syntax.values()) and default_disabled,
        'live_ebay_tested': False, 'live_neon_tested': False,
        'production_ready': False, 'blocking_evidence': list(BLOCKERS),
    }


if __name__ == '__main__':
    print(json.dumps(inspect_repository(Path(__file__).resolve().parent), indent=2))
