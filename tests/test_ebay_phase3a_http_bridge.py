from contextlib import contextmanager
import threading
from unittest.mock import patch
import pytest
from ebay_phase3a_staging_http import make_staging_server
from test_ebay_phase2q_webhook import request, PATH
from ebay_signature import SignatureError
from ebay_public_keys import EbayKeyError

@contextmanager
def staging(**kwargs):
    server = make_staging_server(**kwargs)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def options():
    return dict(connection=object(), erase=lambda *args: 0, key_client=object(), inventory_approved=True)


def test_policy_required():
    args = options(); args['inventory_approved'] = False
    with pytest.raises(ValueError):
        make_staging_server(**args)

@pytest.mark.parametrize('outcome,status', [
    ({'state':'completed','http_acknowledgment_authorized':False},200),
    ({'state':'received','http_acknowledgment_authorized':False},503),
    ({'state':'completed','http_acknowledgment_authorized':True},503),
    (None,503), (SignatureError('private'),412), (EbayKeyError('private'),503),
    (RuntimeError('private'),503)])
def test_http_result_gate(outcome,status):
    args = options()
    config = {'side_effect': outcome} if isinstance(outcome, Exception) else {'return_value': outcome}
    with patch('ebay_phase3a_staging_http.process_notification_offline', **config) as process:
        with staging(**args) as port:
            code, data = request(port,'POST',PATH,body=b'{}',headers={'X-EBAY-SIGNATURE':'fixture'})
        assert code == status
        assert 'private' not in str(data)
        process.assert_called_once_with('fixture',b'{}',args['connection'],args['erase'],storage_inventory_approved=True,key_client=args['key_client'])
        if code == 200:
            assert data['production_acknowledgment_authorized'] is False


def test_wrong_path_does_not_process():
    with patch('ebay_phase3a_staging_http.process_notification_offline') as process:
        with staging(**options()) as port:
            assert request(port,'POST','/wrong',body=b'{}')[0] == 404
        process.assert_not_called()
