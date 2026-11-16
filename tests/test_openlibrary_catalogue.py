import unittest
from openlibrary_catalogue import normalize_isbn, preview

class OpenLibraryTests(unittest.TestCase):
    def test_isbn13(self): self.assertEqual(normalize_isbn('978-0-14-032872-1'),'9780140328721')
    def test_isbn10(self): self.assertEqual(normalize_isbn('0-306-40615-2'),'0306406152')
    def test_invalid_checksum(self):
        with self.assertRaises(ValueError): normalize_isbn('9780140328722')
    def test_injection_rejected(self):
        with self.assertRaises(ValueError): normalize_isbn('9780140328721/../../admin')
    def test_preview(self):
        report=preview('9780140328721',fetcher=lambda _:b'{"title":"Matilda","publish_date":"1988","publishers":["Publisher"]}')
        self.assertEqual(report['title'],'Matilda')
        self.assertEqual(report['database_writes'],0)
        self.assertFalse(report['amazon_sales_verified'])
        self.assertEqual(report['network_requests'],1)
    def test_bad_json(self):
        with self.assertRaises(ValueError): preview('9780140328721',fetcher=lambda _:b'not json')
    def test_no_title(self):
        with self.assertRaises(ValueError): preview('9780140328721',fetcher=lambda _:b'{}')
    def test_size_cap(self):
        with self.assertRaises(ValueError): preview('9780140328721',fetcher=lambda _:b' '*256001)

if __name__=='__main__': unittest.main()
