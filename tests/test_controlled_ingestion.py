import pytest

@pytest.fixture(autouse=True)
def synthetic_feed_policy(monkeypatch):
    monkeypatch.setenv('AUTHORIZED_FEED_HOST','example.org')
    monkeypatch.setenv('AUTHORIZED_FEED_PERMISSION_REF','PERM-1')

import csv
import io
import pytest
from controlled_collection import COLUMNS
from controlled_ingestion import prepare_feed, ingest_approved_feed


def sample(**changes):
    d = dict(asin='B008S8RJKK', marketplace='UK', observed_at_utc='2026-11-12T12:00:00+00:00',
        selling_price_eur='20', supplier_cost_eur='10', referral_pct='15', fulfilment_eur='2',
        inbound_eur='0.5', other_eur='0.5', returns_pct='3', source_note='Authorized commercial feed',
        source_url='https://example.org/dp/B008S8RJKK', authorization_reference='PERM-1')
    d.update(changes)
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerow(d)
    return out.getvalue().encode()


def test_prepares_and_hashes():
    a = prepare_feed(sample())
    assert a['count'] == 1
    assert len(a['sha256']) == 64
    assert a['rows'][0][0]['asin'] == 'B008S8RJKK'


def test_rejects_invalid_rows():
    with pytest.raises(ValueError):
        prepare_feed(sample(source_url='http://insecure.test'))


def test_rejects_unapproved():
    with pytest.raises(ValueError, match='approval'):
        ingest_approved_feed(sample(), 'abc', '')


def test_rejects_changed_payload_without_database():
    with pytest.raises(ValueError, match='differs'):
        ingest_approved_feed(sample(), '0'*64, 'I APPROVE THIS CSV INGESTION')


def test_rejects_empty_feed():
    out = io.StringIO()
    csv.writer(out).writerow(COLUMNS)
    with pytest.raises(ValueError):
        prepare_feed(out.getvalue())
