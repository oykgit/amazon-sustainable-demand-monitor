import json
import unittest
from brevo_reporting import configuration_status, send_report
ENV = {"BREVO_API_KEY": "test-key", "BREVO_SENDER_EMAIL": "sender@example.com", "REPORT_RECIPIENT_EMAIL": "recipient@example.com"}
class FakeResponse:
    def __enter__(self): return self
    def __exit__(self, *args): return False
    status = 201
    def read(self, size=-1): return b'{"messageId":"test-123"}'
class BrevoTests(unittest.TestCase):
    def test_missing(self):
        self.assertFalse(all(configuration_status({}).values()))
        with self.assertRaises(ValueError): send_report('subject','body',env={})
    def test_request(self):
        def fake_open(request, timeout):
            self.assertEqual(timeout,15)
            self.assertEqual(request.get_method(),'POST')
            self.assertEqual(request.headers['Api-key'],'test-key')
            data=json.loads(request.data)
            self.assertEqual(data['to'][0]['email'],ENV['REPORT_RECIPIENT_EMAIL'])
            return FakeResponse()
        self.assertEqual(send_report('Test','Hello',env=ENV,opener=fake_open)['message_id'],'test-123')
    def test_empty_body(self):
        with self.assertRaises(ValueError): send_report('Test','',env=ENV)

    def test_unconfirmed_responses(self):
        for status, body in [(200,b'{"messageId":"x"}'),(201,b'{}'),(201,b'{"messageId":true}'),(201,b'{"messageId":" "}')]:
            with self.subTest(status=status,body=body):
                class Response(FakeResponse):
                    def read(self,size=-1): return body
                Response.status=status
                with self.assertRaises(RuntimeError):
                    send_report('Test','Hello',env=ENV,opener=lambda *a,**k:Response())
