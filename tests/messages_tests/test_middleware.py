import unittest

from django import http
from django.contrib.messages.middleware import MessageMiddleware


class MiddlewareTests(unittest.TestCase):

    def setUp(self):
        self.middleware = MessageMiddleware()

    def test_response_without_messages(self):
        """
        MessageMiddleware is tolerant of messages not existing on request.
        """
        request = http.HttpRequest()
        response = http.HttpResponse()
        self.middleware.process_response(request, response)
