from __future__ import unicode_literals

import gzip
import io

from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django.test import SimpleTestCase
from django.test.client import conditional_content_removal


# based on Python 3.3's gzip.compress
def gzip_compress(data):
    buf = io.BytesIO()
    f = gzip.GzipFile(fileobj=buf, mode='wb', compresslevel=0)
    try:
        f.write(data)
    finally:
        f.close()
    return buf.getvalue()


class ConditionalContentTests(SimpleTestCase):

    def test_conditional_content_removal(self):
        """
        Content is removed from regular and streaming responses with a
        status_code of 100-199, 204, 304, or a method of "HEAD".
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

        # Issue #20472
        abc = gzip_compress(b'abc')
        res = HttpResponse(abc, status=304)
        res['Content-Encoding'] = 'gzip'
        conditional_content_removal(req, res)
        self.assertEqual(res.content, b'')

        res = StreamingHttpResponse([abc], status=304)
        res['Content-Encoding'] = 'gzip'
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
