from __future__ import unicode_literals
from django.test import SimpleTestCase
from django.http import HttpResponse

from asgiref.inmemory import ChannelLayer
from channels.handler import AsgiHandler
from channels.message import Message


class FakeAsgiHandler(AsgiHandler):
    """
    Handler subclass that just returns a premade response rather than
    go into the view subsystem.
    """

    chunk_size = 30

    def __init__(self, response):
        assert isinstance(response, HttpResponse)
        self._response = response
        super(FakeAsgiHandler, self).__init__()

    def get_response(self, request):
        return self._response


class HandlerTests(SimpleTestCase):
    """
    Tests that the handler works correctly and round-trips things into a
    correct response.
    """

    def setUp(self):
        """
        Make an in memory channel layer for testing
        """
        self.channel_layer = ChannelLayer()
        self.make_message = lambda m, c: Message(m, c, self.channel_layer)

    def test_basic(self):
        """
        Tests a simple request
        """
        # Make stub request and desired response
        message = self.make_message({
            "reply_channel": "test",
            "http_version": "1.1",
            "method": "GET",
            "path": b"/test/",
        }, "test")
        response = HttpResponse(b"Hi there!", content_type="text/plain")
        # Run the handler
        handler = FakeAsgiHandler(response)
        reply_messages = list(handler(message))
        # Make sure we got the right number of messages
        self.assertEqual(len(reply_messages), 1)
        reply_message = reply_messages[0]
        # Make sure the message looks correct
        self.assertEqual(reply_message["content"], b"Hi there!")
        self.assertEqual(reply_message["status"], 200)
        self.assertEqual(reply_message["status_text"], b"OK")
        self.assertEqual(reply_message.get("more_content", False), False)
        self.assertEqual(
            reply_message["headers"],
            [("Content-Type", b"text/plain")],
        )

    def test_large(self):
        """
        Tests a large response (will need chunking)
        """
        # Make stub request and desired response
        message = self.make_message({
            "reply_channel": "test",
            "http_version": "1.1",
            "method": "GET",
            "path": b"/test/",
        }, "test")
        response = HttpResponse(b"Thefirstthirtybytesisrighthereandhereistherest")
        # Run the handler
        handler = FakeAsgiHandler(response)
        reply_messages = list(handler(message))
        # Make sure we got the right number of messages
        self.assertEqual(len(reply_messages), 2)
        # Make sure the messages look correct
        self.assertEqual(reply_messages[0]["content"], b"Thefirstthirtybytesisrighthere")
        self.assertEqual(reply_messages[0]["status"], 200)
        self.assertEqual(reply_messages[0]["more_content"], True)
        self.assertEqual(reply_messages[1]["content"], b"andhereistherest")
        self.assertEqual(reply_messages[1].get("more_content", False), False)

    def test_chunk_bytes(self):
        """
        Makes sure chunk_bytes works correctly
        """
        # Empty string should still return one chunk
        result = list(FakeAsgiHandler.chunk_bytes(b""))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], b"")
        self.assertEqual(result[0][1], True)
        # Below chunk size
        result = list(FakeAsgiHandler.chunk_bytes(b"12345678901234567890123456789"))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], b"12345678901234567890123456789")
        self.assertEqual(result[0][1], True)
        # Exactly chunk size
        result = list(FakeAsgiHandler.chunk_bytes(b"123456789012345678901234567890"))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], b"123456789012345678901234567890")
        self.assertEqual(result[0][1], True)
        # Just above chunk size
        result = list(FakeAsgiHandler.chunk_bytes(b"123456789012345678901234567890a"))
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0][0], b"123456789012345678901234567890")
        self.assertEqual(result[0][1], False)
        self.assertEqual(result[1][0], b"a")
        self.assertEqual(result[1][1], True)
