from database_verification import sample_record, is_test_record, verify_database


def test_sample_is_unambiguously_synthetic():
    row = sample_record()
    assert is_test_record(row)
    assert 'NOT A REAL PRODUCT' in row['name']
    assert row['amazon_sales_known'] is False
    assert row['amazon_price_known'] is False
    assert row['amazon_eligibility_known'] is False


def test_verify_write_read_and_duplicate():
    records = {}
    def save(rows):
        added = 0
        for row in rows:
            key = (row['source'], row['barcode'], row['observed_at_utc'])
            if key not in records:
                records[key] = row
                added += 1
        return added
    def load():
        return list(records.values())
    assert verify_database(save=save, load=load)['verified']
    assert verify_database(save=save, load=load)['first_inserted'] == 0


def test_missing_read_fails():
    import pytest
    with pytest.raises(RuntimeError, match='not retrieved'):
        verify_database(save=lambda rows: 1, load=lambda: [])


def test_duplicate_failure_detected():
    import pytest
    with pytest.raises(RuntimeError, match='Duplicate protection'):
        verify_database(save=lambda rows: 1, load=lambda: [sample_record()])
