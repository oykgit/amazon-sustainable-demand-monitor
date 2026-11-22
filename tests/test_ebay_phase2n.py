import unittest
from ebay_phase2n import evaluate, GATES

class Phase2NTests(unittest.TestCase):
    def test_empty_evidence_fails_closed(self):
        report = evaluate({})
        self.assertFalse(report['evidence_complete'])
        self.assertFalse(report['production_ready'])
    def test_unknown_evidence_rejected(self):
        with self.assertRaises(ValueError): evaluate({'fake': {'approved': True}})
    def test_truthy_string_is_not_approval(self):
        report = evaluate({'hosting': {'approved': 'true', 'reference': 'example long reference'}})
        self.assertFalse(report['gates']['hosting']['evidence_recorded'])
    def test_no_reference_is_not_approval(self):
        report = evaluate({'hosting': {'approved': True}})
        self.assertFalse(report['gates']['hosting']['evidence_recorded'])
    def test_all_evidence_never_enables_production(self):
        evidence = {k: {'approved': True, 'reference': 'independent audit ref 123'} for k in GATES}
        report = evaluate(evidence)
        self.assertTrue(report['evidence_complete'])
        self.assertFalse(report['production_ready'])
    def test_non_dict_rejected(self):
        with self.assertRaises(ValueError): evaluate([])

if __name__ == '__main__': unittest.main()
