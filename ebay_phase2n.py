"""Phase 2N: conservative production evidence gate. No network or database writes."""
import json
from pathlib import Path

GATES = {
    'storage_inventory': 'All database tables, logs, exports, backups and other storage reviewed',
    'identity_erasure': 'Account matching and deletion/no-data policy independently approved',
    'ebay_signature': 'Actual eBay notification and signature verified with official public key',
    'neon_transactions': 'Disposable-record Neon commit/rollback/idempotency tests evidenced',
    'http_delivery': 'Real webhook POST response/retry behavior tested end-to-end',
    'hosting': 'Always-on HTTPS hosting and monitoring operational',
    'ebay_approval': 'Production credentials secured and keyset approved by eBay',
    'browse_api': 'Browse API application-token search verified without conflating listings with sales',
}

# An operator may supply an evidence file containing gate objects with independently
# verifiable references. This tool NEVER automatically marks a gate as passed.
def evaluate(evidence):
    if not isinstance(evidence, dict):
        raise ValueError('evidence must be an object')
    unknown = set(evidence) - set(GATES)
    if unknown:
        raise ValueError('unknown gate: ' + ', '.join(sorted(unknown)))
    status = {}
    for key, description in GATES.items():
        item = evidence.get(key)
        accepted = (isinstance(item, dict) and item.get('approved') is True
                    and isinstance(item.get('reference'), str)
                    and len(item['reference'].strip()) >= 12)
        status[key] = {'description': description, 'evidence_recorded': accepted}
    return {'phase': '2N', 'kind': 'operator_evidence_register',
            'evidence_complete': all(v['evidence_recorded'] for v in status.values()),
            'production_ready': False,
            'note': 'Evidence completeness is not certification or authorization to enable POST.',
            'gates': status}

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--evidence', type=Path, help='optional JSON evidence register')
    args = p.parse_args()
    evidence = json.loads(args.evidence.read_text()) if args.evidence else {}
    print(json.dumps(evaluate(evidence), indent=2))
