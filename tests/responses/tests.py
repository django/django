from django.http import HttpResponse
import unittest

class HttpResponseTests(unittest.TestCase):

    def test_status_code(self):
        resp = HttpResponse(status=418)
        self.assertEqual(resp.status_code, 418)
        self.assertEqual(resp.reason_phrase, "I'M A TEAPOT")

    def test_reason_phrase(self):
        reason = "I'm an anarchist coffee pot on crack."
        resp = HttpResponse(status=814, reason=reason)
        self.assertEqual(resp.status_code, 814)
        self.assertEqual(resp.reason_phrase, reason)
