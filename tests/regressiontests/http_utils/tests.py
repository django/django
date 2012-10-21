from __future__ import unicode_literals

from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django.http.utils import conditional_content_removal
from django.test import TestCase


class HttpUtilTests(TestCase):

    def test_conditional_content_removal(self):
        """
        Tests that content is removed from regular and streaming responses with
        a status_code of 100-199, 204, 304 or a method of "HEAD".
        """
        req = HttpRequest()

        # Do nothing for 200 responses.
        res = HttpResponse('abc')
        conditional_content_removal(req, res)
        self.assertEqual(res.content, b'abc')

        res = StreamingHttpResponse(['abc'])
        conditional_content_removal(req, res)
        self.assertEqual(b''.join(res), b'abc')

        # Strip content for some status codes.
        for status_code in (100, 150, 199, 204, 304):
            res = HttpResponse('abc', status=status_code)
            conditional_content_removal(req, res)
            self.assertEqual(res.content, b'')

            res = StreamingHttpResponse(['abc'], status=status_code)
            conditional_content_removal(req, res)
            self.assertEqual(b''.join(res), b'')

        # Strip content for HEAD requests.
        req.method = 'HEAD'

        res = HttpResponse('abc')
        conditional_content_removal(req, res)
        self.assertEqual(res.content, b'')

        res = StreamingHttpResponse(['abc'])
        conditional_content_removal(req, res)
        self.assertEqual(b''.join(res), b'')
