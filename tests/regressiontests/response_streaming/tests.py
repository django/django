import urllib, os

from django.test import TestCase
from django.conf import settings
from django.core.files import temp as tempfile

def x():
    for i in range(0, 10):
        yield unicode(i) + u'\n'

class ResponseStreamingTests(TestCase):
    def test_streaming(self):
        response = self.client.get('/streaming/stream_file/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Disposition'],
                'attachment; filename=test.csv')
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertTrue(not response._is_string)
        self.assertEqual("".join(iter(response)), "".join(x()))
        self.assertTrue(not response._is_string)

    def test_bad_streaming(self):
        response = self.client.get('/streaming/stream_file/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Disposition'],
                'attachment; filename=test.csv')
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertTrue(not response._is_string)
        self.assertEqual(response.content, "".join(x()))
        self.assertTrue(response._is_string)
