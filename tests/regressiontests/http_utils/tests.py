from __future__ import unicode_literals
from django.http import HttpRequest, HttpResponse, HttpStreamingResponse, utils
from django.test import TestCase

class HttpUtilTests(TestCase):
    def test_conditional_content_removal(self):
        """
        Tests that content is removed from regular and streaming responses with
        a status_code of 100-199, 204, 304 or a method of "HEAD".
        """
        req = HttpRequest()

        for status_code in (100, 150, 199, 204, 304):
            # regular response.
            res = HttpResponse('abc')
            self.assertEqual(res.content, b'abc')
            res.status_code = status_code
            utils.conditional_content_removal(req, res)
            self.assertEqual(res.content, b'')

            # streaming response.
            res = HttpResponse(['abc'])
            self.assertEqual(b''.join(res), b'abc')
            res = HttpResponse(['abc'])
            res.status_code = status_code
            utils.conditional_content_removal(req, res)
            self.assertEqual(b''.join(res), b'')

        # do nothing for other status codes.
        res = HttpResponse('abc')
        self.assertEqual(res.content, b'abc')
        res.status_code = 200
        utils.conditional_content_removal(req, res)
        self.assertEqual(res.content, b'abc')

        # HEAD reqeusts.
        req.method = 'HEAD'

        # regular response.
        res = HttpResponse('abc')
        self.assertEqual(res.content, b'abc')
        utils.conditional_content_removal(req, res)
        self.assertEqual(res.content, b'')

        # streaming response.
        res = HttpResponse(['abc'])
        self.assertEqual(b''.join(res), b'abc')
        res = HttpResponse(['abc'])
        utils.conditional_content_removal(req, res)
        self.assertEqual(b''.join(res), b'')
