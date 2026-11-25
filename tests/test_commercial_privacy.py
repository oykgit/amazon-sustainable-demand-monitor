import unittest
from datetime import datetime, timezone
from commercial_privacy import validate_feed_row, PrivacyError, barcode, asin

class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.row = dict(asin='b008s8rjkk', marketplace='UK', observed_at_utc='2020-01-01T00:00:00Z', selling_price_eur='20', supplier_cost_eur='10', referral_pct='15', fulfilment_eur='2', inbound_eur='1', other_eur='0', returns_pct='3', source_note='Authorized commercial feed', source_url='https://example.org/dp/B008S8RJKK', authorization_reference='PERM-1')
    def check(self, **changes):
        return validate_feed_row(dict(self.row, **changes), allowed_host='example.org', approved_reference='PERM-1')
    def test_valid(self):
        self.assertEqual(self.check()['asin'],'B008S8RJKK')
    def test_unknown_fields(self):
        for key in ('userId','username','eiasToken','seller','buyer','payload','extra'):
            with self.subTest(key=key), self.assertRaisesRegex(PrivacyError,'^UNAPPROVED_SCHEMA$'):
                self.check(**{key:'synthetic-secret'})
    def test_urls(self):
        for url in ('http://example.org/dp/B008S8RJKK','https://example.org/dp/B008S8RJKK?token=x','https://u:p@example.org/dp/B008S8RJKK','https://example.org/dp/B008S8RJKK#x','https://evil.example/dp/B008S8RJKK','https://example.org/dp/B008S8RJKK%2f','https://example.org:443/dp/B008S8RJKK'):
            with self.subTest(url=url), self.assertRaises(PrivacyError): self.check(source_url=url)
    def test_text_and_permission(self):
        for changes in ({'source_note':'synthetic-secret'}, {'authorization_reference':'PERM-2'}, {'source_note':{'userId':'x'}}, {'marketplace':'US'}):
            with self.subTest(changes=changes), self.assertRaises(PrivacyError) as e: self.check(**changes)
            self.assertNotIn('synthetic-secret',str(e.exception))
    def test_numbers(self):
        for value in ('NaN','Infinity','-1','101',True,{},'x'):
            with self.subTest(value=value), self.assertRaises(PrivacyError): self.check(referral_pct=value)
    def test_dates(self):
        for value in ('2099-01-01T00:00:00Z','2020-01-01','bad'):
            with self.subTest(value=value), self.assertRaises(PrivacyError): self.check(observed_at_utc=value)
    def test_missing(self):
        del self.row['source_note']
        with self.assertRaises(PrivacyError): self.check()
    def test_identifiers(self):
        self.assertEqual(barcode('9780140328721'),'9780140328721')
        for value in ('9780140328722','123','１２３４５６７８'):
            with self.assertRaises(PrivacyError): barcode(value)
        with self.assertRaises(PrivacyError): asin('bad')
