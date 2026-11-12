"""Explicit synthetic database smoke test; never represents Amazon market evidence."""
from persistent_store import save_observations, load_observations

TEST_SOURCE = 'SYSTEM_TEST_ONLY'
TEST_BARCODE = '0000000000000'
TEST_TIMESTAMP = '2000-01-01T00:00:00+00:00'


def sample_record():
    return {
        'observed_at_utc': TEST_TIMESTAMP,
        'barcode': TEST_BARCODE,
        'name': 'SYNTHETIC DATABASE TEST — NOT A REAL PRODUCT',
        'brand': 'SYSTEM TEST', 'quantity': '',
        'source': TEST_SOURCE, 'source_url': '',
        'amazon_sales_known': False, 'amazon_price_known': False,
        'amazon_eligibility_known': False,
    }


def is_test_record(record):
    return (record.get('source') == TEST_SOURCE and
            record.get('barcode') == TEST_BARCODE and
            record.get('observed_at_utc') == TEST_TIMESTAMP)


def verify_database(save=save_observations, load=load_observations):
    """Verify write, read, and idempotency. No test data enters analysis."""
    record = sample_record()
    first = save([record])
    second = save([record])
    matches = [row for row in load() if is_test_record(row)]
    if len(matches) != 1:
        raise RuntimeError('Test record was not retrieved exactly once. Database verification failed.')
    if any(str(matches[0].get(k, '')) != str(record[k]) for k in ('name','brand','source')):
        raise RuntimeError('Retrieved test record differs from the saved record.')
    if second != 0:
        raise RuntimeError('Duplicate protection failed: the same test record was inserted again.')
    return {'verified': True, 'first_inserted': first,
            'duplicate_inserted': second, 'retrieved_test_records': len(matches)}
