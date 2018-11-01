import unittest

from django.contrib.messages.middleware import MessageMiddleware
from django.http import HttpRequest, HttpResponse


class MiddlewareTests(unittest.TestCase):

    def setUp(self):
        self.middleware = MessageMiddleware()

    def test_response_without_messages(self):
        """
        MessageMiddleware is tolerant of messages not existing on request.
        """
        request = HttpRequest()
        response = HttpResponse()
        self.middleware.process_response(request, response)
