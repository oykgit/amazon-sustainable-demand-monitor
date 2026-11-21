# eBay Webhook Phase 2B: Offline signature verification

Adds an isolated, offline ECDSA/SHA-256 verifier for the raw eBay JSON notification bytes. It validates the Base64-encoded JSON signature envelope and verifies the DER-encoded ECDSA signature with a supplied **trusted** PEM public key.

## Files
- `ebay_signature.py` (new)
- `tests/test_ebay_signature.py` (new)
- `PHASE2B_README.md` (new)

## Install
Add these files at the repository root and test folder respectively. Do not replace `ebay_webhook.py`. The live POST endpoint remains disabled and the existing GET challenge is unchanged.

Run tests: `python -m unittest discover -s tests -p 'test_ebay_signature.py' -v`

Test dependency: `cryptography>=42,<47`. This package is **not yet imported by the live webhook**; do not change the existing Render Build or Start Commands for this phase.

## Not production-ready
- No eBay OAuth client-credentials token acquisition or authenticated `getPublicKey` request yet.
- No trusted public-key cache or key-ID binding yet.
- No integration into the HTTP POST handler.
- No durable notification receipt, replay protection, or verified data-erasure procedure.
- No verified live eBay sample notification.
- Free Render service may sleep and miss prompt delivery requirements.

Do not register this webhook in eBay yet. Never paste client secrets or verification tokens into GitHub or chat.
