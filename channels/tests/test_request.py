from __future__ import unicode_literals
from django.utils import six

from channels import Channel
from channels.tests import ChannelTestCase
from channels.handler import AsgiRequest
from channels.exceptions import RequestTimeout, RequestAborted


class RequestTests(ChannelTestCase):
    """
    Tests that ASGI request handling correctly decodes HTTP requests.
    """

    def test_basic(self):
        """
        Tests that the handler can decode the most basic request message,
        with all optional fields omitted.
        """
        Channel("test").send({
            "reply_channel": "test-reply",
            "http_version": "1.1",
            "method": "GET",
            "path": b"/test/",
        })
        request = AsgiRequest(self.get_next_message("test"))
        self.assertEqual(request.path, "/test/")
        self.assertEqual(request.method, "GET")
        self.assertFalse(request.body)
        self.assertNotIn("HTTP_HOST", request.META)
        self.assertNotIn("REMOTE_ADDR", request.META)
        self.assertNotIn("REMOTE_HOST", request.META)
        self.assertNotIn("REMOTE_PORT", request.META)
        self.assertNotIn("SERVER_NAME", request.META)
        self.assertNotIn("SERVER_PORT", request.META)
        self.assertFalse(request.GET)
        self.assertFalse(request.POST)
        self.assertFalse(request.COOKIES)

    def test_extended(self):
        """
        Tests a more fully-featured GET request
        """
        Channel("test").send({
            "reply_channel": "test",
            "http_version": "1.1",
            "method": "GET",
            "path": b"/test2/",
            "query_string": b"x=1&y=foo%20bar+baz",
            "headers": {
                "host": b"example.com",
                "cookie": b"test-time=1448995585123; test-value=yeah",
            },
            "client": ["10.0.0.1", 1234],
            "server": ["10.0.0.2", 80],
        })
        request = AsgiRequest(self.get_next_message("test"))
        self.assertEqual(request.path, "/test2/")
        self.assertEqual(request.method, "GET")
        self.assertFalse(request.body)
        self.assertEqual(request.META["HTTP_HOST"], "example.com")
        self.assertEqual(request.META["REMOTE_ADDR"], "10.0.0.1")
        self.assertEqual(request.META["REMOTE_HOST"], "10.0.0.1")
        self.assertEqual(request.META["REMOTE_PORT"], 1234)
        self.assertEqual(request.META["SERVER_NAME"], "10.0.0.2")
        self.assertEqual(request.META["SERVER_PORT"], 80)
        self.assertEqual(request.GET["x"], "1")
        self.assertEqual(request.GET["y"], "foo bar baz")
        self.assertEqual(request.COOKIES["test-time"], "1448995585123")
        self.assertEqual(request.COOKIES["test-value"], "yeah")
        self.assertFalse(request.POST)

    def test_post_single(self):
        """
        Tests a POST body contained within a single message.
        """
        Channel("test").send({
            "reply_channel": "test",
            "http_version": "1.1",
            "method": "POST",
            "path": b"/test2/",
            "query_string": b"django=great",
            "body": b"ponies=are+awesome",
            "headers": {
                "host": b"example.com",
                "content-type": b"application/x-www-form-urlencoded",
                "content-length": b"18",
            },
        })
        request = AsgiRequest(self.get_next_message("test"))
        self.assertEqual(request.path, "/test2/")
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.body, b"ponies=are+awesome")
        self.assertEqual(request.META["HTTP_HOST"], "example.com")
        self.assertEqual(request.META["CONTENT_TYPE"], "application/x-www-form-urlencoded")
        self.assertEqual(request.GET["django"], "great")
        self.assertEqual(request.POST["ponies"], "are awesome")
        with self.assertRaises(KeyError):
            request.POST["django"]
        with self.assertRaises(KeyError):
            request.GET["ponies"]

    def test_post_multiple(self):
        """
        Tests a POST body across multiple messages (first part in 'body').
        """
        Channel("test").send({
            "reply_channel": "test",
            "http_version": "1.1",
            "method": "POST",
            "path": b"/test/",
            "body": b"there_a",
            "body_channel": "test-input",
            "headers": {
                "host": b"example.com",
                "content-type": b"application/x-www-form-urlencoded",
                "content-length": b"21",
            },
        })
        Channel("test-input").send({
            "content": b"re=fou",
            "more_content": True,
        })
        Channel("test-input").send({
            "content": b"r+lights",
        })
        request = AsgiRequest(self.get_next_message("test"))
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.body, b"there_are=four+lights")
        self.assertEqual(request.META["CONTENT_TYPE"], "application/x-www-form-urlencoded")
        self.assertEqual(request.POST["there_are"], "four lights")

    def test_post_files(self):
        """
        Tests POSTing files using multipart form data and multiple messages,
        with no body in the initial message.
        """
        body = (
            b'--BOUNDARY\r\n' +
            b'Content-Disposition: form-data; name="title"\r\n\r\n' +
            b'My First Book\r\n' +
            b'--BOUNDARY\r\n' +
            b'Content-Disposition: form-data; name="pdf"; filename="book.pdf"\r\n\r\n' +
            b'FAKEPDFBYTESGOHERE' +
            b'--BOUNDARY--'
        )
        Channel("test").send({
            "reply_channel": "test",
            "http_version": "1.1",
            "method": "POST",
            "path": b"/test/",
            "body_channel": "test-input",
            "headers": {
                "content-type": b"multipart/form-data; boundary=BOUNDARY",
                "content-length": six.text_type(len(body)).encode("ascii"),
            },
        })
        Channel("test-input").send({
            "content": body[:20],
            "more_content": True,
        })
        Channel("test-input").send({
            "content": body[20:],
        })
        request = AsgiRequest(self.get_next_message("test"))
        self.assertEqual(request.method, "POST")
        self.assertEqual(len(request.body), len(body))
        self.assertTrue(request.META["CONTENT_TYPE"].startswith("multipart/form-data"))
        self.assertFalse(request._post_parse_error)
        self.assertEqual(request.POST["title"], "My First Book")
        self.assertEqual(request.FILES["pdf"].read(), b"FAKEPDFBYTESGOHERE")

    def test_stream(self):
        """
        Tests the body stream is emulated correctly.
        """
        Channel("test").send({
            "reply_channel": "test",
            "http_version": "1.1",
            "method": "PUT",
            "path": b"/",
            "body": b"onetwothree",
            "headers": {
                "host": b"example.com",
                "content-length": b"11",
            },
        })
        request = AsgiRequest(self.get_next_message("test", require=True))
        self.assertEqual(request.method, "PUT")
        self.assertEqual(request.read(3), b"one")
        self.assertEqual(request.read(), b"twothree")

    def test_request_timeout(self):
        """
        Tests that the code correctly gives up after the request body read timeout.
        """
        Channel("test").send({
            "reply_channel": "test",
            "http_version": "1.1",
            "method": "POST",
            "path": b"/test/",
            "body": b"there_a",
            "body_channel": "test-input",
            "headers": {
                "host": b"example.com",
                "content-type": b"application/x-www-form-urlencoded",
                "content-length": b"21",
            },
        })
        # Say there's more content, but never provide it! Muahahaha!
        Channel("test-input").send({
            "content": b"re=fou",
            "more_content": True,
        })

        class VeryImpatientRequest(AsgiRequest):
            body_receive_timeout = 0

        with self.assertRaises(RequestTimeout):
            VeryImpatientRequest(self.get_next_message("test"))

    def test_request_abort(self):
        """
        Tests that the code aborts when a request-body close is sent.
        """
        Channel("test").send({
            "reply_channel": "test",
            "http_version": "1.1",
            "method": "POST",
            "path": b"/test/",
            "body": b"there_a",
            "body_channel": "test-input",
            "headers": {
                "host": b"example.com",
                "content-type": b"application/x-www-form-urlencoded",
                "content-length": b"21",
            },
        })
        Channel("test-input").send({
            "closed": True,
        })
        with self.assertRaises(RequestAborted):
            AsgiRequest(self.get_next_message("test"))
