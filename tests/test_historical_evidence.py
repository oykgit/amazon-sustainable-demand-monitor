import unittest
from historical_evidence import analyse

def row(date="2026-11-01", value="21.5", kind="PRICE_EUR"):
    return {"asin":"B008S8RJKK","market":"UK","observed_date":date,"source_provider":"operator",
            "source_reference":"example-not-authenticated","evidence_type":kind,"value":value}

class Tests(unittest.TestCase):
    def test_empty(self):
        r=analyse([], as_of="2026-11-18")
        self.assertEqual(r["groups"], [])
        self.assertEqual(r["database_writes"],0)
    def test_sparse(self):
        r=analyse([row()], as_of="2026-11-18")
        self.assertEqual(r["groups"][0]["coverage_gate"],"INSUFFICIENT")
        self.assertFalse(r["historical_demand_verified"])
    def test_future_rejected(self):
        with self.assertRaises(ValueError): analyse([row("2027-01-01")], as_of="2026-11-18")
    def test_bad_source(self):
        r=row(); r["source_reference"]=""
        with self.assertRaises(ValueError): analyse([r], as_of="2026-11-18")
    def test_invalid_rank(self):
        with self.assertRaises(ValueError): analyse([row(kind="SALES_RANK",value="1.5")], as_of="2026-11-18")
    def test_negative(self):
        with self.assertRaises(ValueError): analyse([row(value="-1")], as_of="2026-11-18")
    def test_no_automatic_sales_claim(self):
        rows=[row(f"2026-{m:02d}-01") for m in range(1,12)]
        result=analyse(rows,as_of="2026-11-18")
        self.assertFalse(result["groups"][0]["sustained_demand_verified"])

if __name__ == "__main__": unittest.main()
