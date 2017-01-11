from __future__ import unicode_literals

import os
from datetime import datetime
from itertools import islice

from django.http import FileResponse, HttpResponse, HttpResponseRedirect, JsonResponse, StreamingHttpResponse
from six import BytesIO

from channels import Channel
from channels.handler import AsgiHandler
from channels.tests import ChannelTestCase


class FakeAsgiHandler(AsgiHandler):
    """
    Handler subclass that just returns a premade response rather than
    go into the view subsystem.
    """

    chunk_size = 30

    def __init__(self, response):
        assert isinstance(response, (HttpResponse, StreamingHttpResponse))
        self._response = response
        super(FakeAsgiHandler, self).__init__()

    def get_response(self, request):
        return self._response


class HandlerTests(ChannelTestCase):
    """
    Tests that the handler works correctly and round-trips things into a
    correct response.
    """

    def test_basic(self):
        """
        Tests a simple request
        """
        # Make stub request and desired response
        Channel("test").send({
            "reply_channel": "test",
            "http_version": "1.1",
            "method": "GET",
            "path": b"/test/",
        })
        response = HttpResponse(b"Hi there!", content_type="text/plain")
        # Run the handler
        handler = FakeAsgiHandler(response)
        reply_messages = list(
            handler(self.get_next_message("test", require=True)))
        # Make sure we got the right number of messages
        self.assertEqual(len(reply_messages), 1)
        reply_message = reply_messages[0]
        # Make sure the message looks correct
        self.assertEqual(reply_message["content"], b"Hi there!")
        self.assertEqual(reply_message["status"], 200)
        self.assertEqual(reply_message.get("more_content", False), False)
        self.assertEqual(
            reply_message["headers"],
            [
                (b"Content-Type", b"text/plain"),
            ],
        )

    def test_cookies(self):
        Channel("test").send({
            "reply_channel": "test",
            "http_version": "1.1",
            "method": "GET",
            "path": b"/test/",
        })
        response = HttpResponse(b"Hi there!", content_type="text/plain")
        response.set_signed_cookie('foo', '1', expires=datetime.now())
        # Run the handler
        handler = FakeAsgiHandler(response)
        reply_messages = list(
            handler(self.get_next_message("test", require=True)))
        # Make sure we got the right number of messages
        self.assertEqual(len(reply_messages), 1)
        reply_message = reply_messages[0]
        # Make sure the message looks correct
        self.assertEqual(reply_message["content"], b"Hi there!")
        self.assertEqual(reply_message["status"], 200)
        self.assertEqual(reply_message.get("more_content", False), False)
        self.assertEqual(reply_message["headers"][0], (b'Content-Type', b'text/plain'))
        self.assertIn('foo=', reply_message["headers"][1][1].decode())

    def test_headers(self):
        Channel("test").send({
            "reply_channel": "test",
            "http_version": "1.1",
            "method": "GET",
            "path": b"/test/",
        })
        response = HttpResponse(b"Hi there!", content_type="text/plain")
        response['foo'] = 1
        response['bar'] = 1
        del response['bar']
        del response['nonexistant_key']
        handler = FakeAsgiHandler(response)
        reply_messages = list(
            handler(self.get_next_message("test", require=True)))
        # Make sure we got the right number of messages
        self.assertEqual(len(reply_messages), 1)
        reply_message = reply_messages[0]
        # Make sure the message looks correct
        self.assertEqual(reply_message["content"], b"Hi there!")
        header_dict = dict(reply_messages[0]['headers'])
        self.assertEqual(header_dict[b'foo'].decode(), '1')
        self.assertNotIn('bar', header_dict)

    def test_large(self):
        """
        Tests a large response (will need chunking)
        """
        # Make stub request and desired response
        Channel("test").send({
            "reply_channel": "test",
            "http_version": "1.1",
            "method": "GET",
            "path": b"/test/",
        })
        response = HttpResponse(
            b"Thefirstthirtybytesisrighthereandhereistherest")
        # Run the handler
        handler = FakeAsgiHandler(response)
        reply_messages = list(
            handler(self.get_next_message("test", require=True)))
        # Make sure we got the right number of messages
        self.assertEqual(len(reply_messages), 2)
        # Make sure the messages look correct
        self.assertEqual(reply_messages[0][
                         "content"], b"Thefirstthirtybytesisrighthere")
        self.assertEqual(reply_messages[0]["status"], 200)
        self.assertEqual(reply_messages[0]["more_content"], True)
        self.assertEqual(reply_messages[1]["content"], b"andhereistherest")
        self.assertEqual(reply_messages[1].get("more_content", False), False)

    def test_empty(self):
        """
        Tests an empty response
        """
        # Make stub request and desired response
        Channel("test").send({
            "reply_channel": "test",
            "http_version": "1.1",
            "method": "GET",
            "path": b"/test/",
        })
        response = HttpResponse(b"", status=304)
        # Run the handler
        handler = FakeAsgiHandler(response)
        reply_messages = list(
            handler(self.get_next_message("test", require=True))
        )
        # Make sure we got the right number of messages
        self.assertEqual(len(reply_messages), 1)
        # Make sure the messages look correct
        self.assertEqual(reply_messages[0].get("content", b""), b"")
        self.assertEqual(reply_messages[0]["status"], 304)
        self.assertEqual(reply_messages[0]["more_content"], False)

    def test_empty_streaming(self):
        """
        Tests an empty streaming response
        """
        # Make stub request and desired response
        Channel("test").send({
            "reply_channel": "test",
            "http_version": "1.1",
            "method": "GET",
            "path": b"/test/",
        })
        response = StreamingHttpResponse([], status=304)
        # Run the handler
        handler = FakeAsgiHandler(response)
        reply_messages = list(
            handler(self.get_next_message("test", require=True))
        )
        # Make sure we got the right number of messages
        self.assertEqual(len(reply_messages), 1)
        # Make sure the messages look correct
        self.assertEqual(reply_messages[0].get("content", b""), b"")
        self.assertEqual(reply_messages[0]["status"], 304)
        self.assertEqual(reply_messages[0]["more_content"], False)

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
        result = list(FakeAsgiHandler.chunk_bytes(
            b"12345678901234567890123456789"))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], b"12345678901234567890123456789")
        self.assertEqual(result[0][1], True)
        # Exactly chunk size
        result = list(FakeAsgiHandler.chunk_bytes(
            b"123456789012345678901234567890"))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], b"123456789012345678901234567890")
        self.assertEqual(result[0][1], True)
        # Just above chunk size
        result = list(FakeAsgiHandler.chunk_bytes(
            b"123456789012345678901234567890a"))
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0][0], b"123456789012345678901234567890")
        self.assertEqual(result[0][1], False)
        self.assertEqual(result[1][0], b"a")
        self.assertEqual(result[1][1], True)

    def test_iterator(self):
        Channel("test").send({
            "reply_channel": "test",
            "http_version": "1.1",
            "method": "GET",
            "path": b"/test/",
        })
        response = HttpResponse(range(10))
        handler = FakeAsgiHandler(response)
        reply_messages = list(
            handler(self.get_next_message("test", require=True)))
        self.assertEqual(len(reply_messages), 1)
        self.assertEqual(reply_messages[0]["content"], b"0123456789")

    def test_streaming_data(self):
        Channel("test").send({
            "reply_channel": "test",
            "http_version": "1.1",
            "method": "GET",
            "path": b"/test/",
        })
        response = StreamingHttpResponse('Line: %s' % i for i in range(10))
        handler = FakeAsgiHandler(response)
        reply_messages = list(
            handler(self.get_next_message("test", require=True)))
        self.assertEqual(len(reply_messages), 11)
        self.assertEqual(reply_messages[0]["content"], b"Line: 0")
        self.assertEqual(reply_messages[9]["content"], b"Line: 9")

    def test_real_file_response(self):
        Channel("test").send({
            "reply_channel": "test",
            "http_version": "1.1",
            "method": "GET",
            "path": b"/test/",
        })
        current_dir = os.path.realpath(os.path.join(
            os.getcwd(), os.path.dirname(__file__)))
        response = FileResponse(
            open(os.path.join(current_dir, 'a_file'), 'rb'))
        handler = FakeAsgiHandler(response)
        reply_messages = list(
            handler(self.get_next_message("test", require=True)))
        self.assertEqual(len(reply_messages), 2)
        self.assertEqual(response.getvalue(), b'')

    def test_bytes_file_response(self):
        Channel("test").send({
            "reply_channel": "test",
            "http_version": "1.1",
            "method": "GET",
            "path": b"/test/",
        })
        response = FileResponse(BytesIO(b'sadfdasfsdfsadf'))
        handler = FakeAsgiHandler(response)
        reply_messages = list(
            handler(self.get_next_message("test", require=True)))
        self.assertEqual(len(reply_messages), 2)

    def test_string_file_response(self):
        Channel("test").send({
            "reply_channel": "test",
            "http_version": "1.1",
            "method": "GET",
            "path": b"/test/",
        })
        response = FileResponse('abcd')
        handler = FakeAsgiHandler(response)
        reply_messages = list(
            handler(self.get_next_message("test", require=True)))
        self.assertEqual(len(reply_messages), 5)

    def test_non_streaming_file_response(self):
        Channel("test").send({
            "reply_channel": "test",
            "http_version": "1.1",
            "method": "GET",
            "path": b"/test/",
        })
        response = FileResponse(BytesIO(b'sadfdasfsdfsadf'))
        # This is to test the exception handling. This would only happening if
        # the StreamingHttpResponse was incorrectly subclassed.
        response.streaming = False

        handler = FakeAsgiHandler(response)
        with self.assertRaises(AttributeError):
            list(handler(self.get_next_message("test", require=True)))

    def test_unclosable_filelike_object(self):
        Channel("test").send({
            "reply_channel": "test",
            "http_version": "1.1",
            "method": "GET",
            "path": b"/test/",
        })

        # This is a readable object that cannot be closed.
        class Unclosable:

            def read(self, n=-1):
                # Nothing to see here
                return b""

        response = FileResponse(Unclosable())
        handler = FakeAsgiHandler(response)
        reply_messages = list(islice(handler(self.get_next_message("test", require=True)), 5))
        self.assertEqual(len(reply_messages), 1)
        response.close()

    def test_json_response(self):
        Channel("test").send({
            "reply_channel": "test",
            "http_version": "1.1",
            "method": "GET",
            "path": b"/test/",
        })
        response = JsonResponse({'foo': (1, 2)})
        handler = FakeAsgiHandler(response)
        reply_messages = list(handler(self.get_next_message("test", require=True)))
        self.assertEqual(len(reply_messages), 1)
        self.assertEqual(reply_messages[0]['content'], b'{"foo": [1, 2]}')

    def test_redirect(self):
        for redirect_to in ['/', '..', 'https://example.com']:
            Channel("test").send({
                "reply_channel": "test",
                "http_version": "1.1",
                "method": "GET",
                "path": b"/test/",
            })
            response = HttpResponseRedirect(redirect_to)
            handler = FakeAsgiHandler(response)
            reply_messages = list(handler(self.get_next_message("test", require=True)))
            self.assertEqual(reply_messages[0]['status'], 302)
            header_dict = dict(reply_messages[0]['headers'])
            self.assertEqual(header_dict[b'Location'].decode(), redirect_to)
