import tempfile
import unittest
from pathlib import Path
from ebay_phase2j_audit import audit, REQUIRED

class AuditTests(unittest.TestCase):
    def test_missing_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            result = audit(d)
            self.assertFalse(result['local_static_checks_passed'])
            self.assertFalse(result['production_ready'])
    def test_expected_static_layout(self):
        with tempfile.TemporaryDirectory() as d:
            for name in REQUIRED:
                (Path(d)/name).write_text('x = 1\n')
            (Path(d)/'ebay_webhook.py').write_text("def challenge_response(): pass\ndef do_POST(): pass\n# os.getenv('EBAY_PHASE2D_AUTH_TEST', '') != '1'\n# 'notification_processing_not_enabled'\n")
            result = audit(d)
            self.assertTrue(result['local_static_checks_passed'])
            self.assertFalse(result['production_ready'])
    def test_bad_python_fails(self):
        with tempfile.TemporaryDirectory() as d:
            for name in REQUIRED:
                (Path(d)/name).write_text('x = 1\n')
            (Path(d)/'ebay_phase2i.py').write_text('def broken(:\n')
            self.assertFalse(audit(d)['checks']['syntax:ebay_phase2i.py'])
    def test_no_external_access(self):
        import inspect, ebay_phase2j_audit
        src = inspect.getsource(ebay_phase2j_audit)
        self.assertNotIn('requests.get(', src)
        self.assertNotIn('psycopg.connect(', src)

if __name__ == '__main__': unittest.main()
