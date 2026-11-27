"""Offline regression tests for privacy-safe webhook diagnostics."""
import io
import logging
import os
from unittest.mock import patch
from test_ebay_phase2q_webhook import local_server, request, PATH
import ebay_webhook


def test_diagnostic_health_never_claims_processing_enabled():
    with patch.dict(os.environ, {'EBAY_PHASE2D_AUTH_TEST':'1', 'EBAY_CLIENT_ID':'synthetic-client', 'EBAY_CLIENT_SECRET':'synthetic-secret'}):
        with local_server() as port:
            status, health = request(port, 'GET', '/health')
    assert status == 200
    assert health['post_enabled'] is False
    assert health['signature_diagnostic_enabled'] is True
    assert health['oauth_credentials_configured'] is True
    assert 'synthetic-secret' not in str(health)
    assert 'synthetic-client' not in str(health)


def test_post_diagnostic_logs_only_outcome_and_never_acknowledges():
    with patch.dict(os.environ, {'EBAY_PHASE2D_AUTH_TEST':'1'}):
        with patch.object(ebay_webhook, 'authenticate_notification', return_value={'notification':{'data':{'username':'private-fixture'}}}):
            with local_server() as port:
                with __import__('unittest').TestCase().assertLogs('ebay_webhook', level='WARNING') as logs:
                    status, response = request(port, 'POST', PATH+'?private-query', body=b'{"username":"private-fixture"}', headers={'X-EBAY-SIGNATURE':'private-signature'})
    assert status == 503
    assert response['error'] == 'verified_but_processing_not_enabled'
    assert 'ebay_notification_http_status=503 outcome=verified_but_processing_not_enabled' in '\n'.join(logs.output)
    assert 'private-' not in '\n'.join(logs.output)


def test_default_http_logging_does_not_expose_raw_request():
    handler = object.__new__(ebay_webhook.Handler)
    with patch('sys.stderr', new_callable=io.StringIO) as stderr:
        handler.log_message('%s', 'private-query')
        assert stderr.getvalue() == ''
