import unittest

from django import http
from django.contrib.messages.middleware import MessageMiddleware


class MiddlewareTest(unittest.TestCase):

    def setUp(self):
        self.middleware = MessageMiddleware()

    def test_response_without_messages(self):
        """
        Makes sure that the response middleware is tolerant of messages not
        existing on request.
        """
        request = http.HttpRequest()
        response = http.HttpResponse()
        self.middleware.process_response(request, response)

    def test_repr(self):
        expected = '<MessageMiddleware MESSAGE_STORAGE="django.contrib.messages.storage.fallback.FallbackStorage">'
        self.assertEqual(repr(self.middleware), expected)
