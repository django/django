import re
import unittest
from unittest.mock import MagicMock

import pytest
from django.http import HttpResponse

from asgiref.testing import ApplicationCommunicator
from channels.consumer import AsyncConsumer
from channels.http import AsgiHandler, AsgiRequest
from channels.sessions import SessionMiddlewareStack
from channels.testing import HttpCommunicator


class RequestTests(unittest.TestCase):
    """
    Tests that ASGI request handling correctly decodes HTTP requests given scope
    and body.
    """

    def test_basic(self):
        """
        Tests that the handler can decode the most basic request message,
        with all optional fields omitted.
        """
        request = AsgiRequest(
            {
                "http_version": "1.1",
                "method": "GET",
                "path": "/test/",
            },
            b"",
        )
        self.assertEqual(request.path, "/test/")
        self.assertEqual(request.method, "GET")
        self.assertFalse(request.body)
        self.assertNotIn("HTTP_HOST", request.META)
        self.assertNotIn("REMOTE_ADDR", request.META)
        self.assertNotIn("REMOTE_HOST", request.META)
        self.assertNotIn("REMOTE_PORT", request.META)
        self.assertIn("SERVER_NAME", request.META)
        self.assertIn("SERVER_PORT", request.META)
        self.assertFalse(request.GET)
        self.assertFalse(request.POST)
        self.assertFalse(request.COOKIES)

    def test_extended(self):
        """
        Tests a more fully-featured GET request
        """
        request = AsgiRequest(
            {
                "http_version": "1.1",
                "method": "GET",
                "path": "/test2/",
                "query_string": b"x=1&y=%26foo+bar%2Bbaz",
                "headers": {
                    "host": b"example.com",
                    "cookie": b"test-time=1448995585123; test-value=yeah",
                },
                "client": ["10.0.0.1", 1234],
                "server": ["10.0.0.2", 80],
            },
            b"",
        )
        self.assertEqual(request.path, "/test2/")
        self.assertEqual(request.method, "GET")
        self.assertFalse(request.body)
        self.assertEqual(request.META["HTTP_HOST"], "example.com")
        self.assertEqual(request.META["REMOTE_ADDR"], "10.0.0.1")
        self.assertEqual(request.META["REMOTE_HOST"], "10.0.0.1")
        self.assertEqual(request.META["REMOTE_PORT"], 1234)
        self.assertEqual(request.META["SERVER_NAME"], "10.0.0.2")
        self.assertEqual(request.META["SERVER_PORT"], "80")
        self.assertEqual(request.GET["x"], "1")
        self.assertEqual(request.GET["y"], "&foo bar+baz")
        self.assertEqual(request.COOKIES["test-time"], "1448995585123")
        self.assertEqual(request.COOKIES["test-value"], "yeah")
        self.assertFalse(request.POST)

    def test_post(self):
        """
        Tests a POST body.
        """
        request = AsgiRequest(
            {
                "http_version": "1.1",
                "method": "POST",
                "path": "/test2/",
                "query_string": "django=great",
                "headers": {
                    "host": b"example.com",
                    "content-type": b"application/x-www-form-urlencoded",
                    "content-length": b"18",
                },
            },
            b"djangoponies=are+awesome",
        )
        self.assertEqual(request.path, "/test2/")
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.body, b"djangoponies=are+awesome")
        self.assertEqual(request.META["HTTP_HOST"], "example.com")
        self.assertEqual(request.META["CONTENT_TYPE"], "application/x-www-form-urlencoded")
        self.assertEqual(request.GET["django"], "great")
        self.assertEqual(request.POST["djangoponies"], "are awesome")
        with self.assertRaises(KeyError):
            request.POST["django"]
        with self.assertRaises(KeyError):
            request.GET["djangoponies"]

    def test_post_files(self):
        """
        Tests POSTing files using multipart form data.
        """
        body = (
            b"--BOUNDARY\r\n" +
            b'Content-Disposition: form-data; name="title"\r\n\r\n' +
            b"My First Book\r\n" +
            b"--BOUNDARY\r\n" +
            b'Content-Disposition: form-data; name="pdf"; filename="book.pdf"\r\n\r\n' +
            b"FAKEPDFBYTESGOHERE" +
            b"--BOUNDARY--"
        )
        request = AsgiRequest(
            {
                "http_version": "1.1",
                "method": "POST",
                "path": "/test/",
                "headers": {
                    "content-type": b"multipart/form-data; boundary=BOUNDARY",
                    "content-length": str(len(body)).encode("ascii"),
                },
            },
            body,
        )
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
        request = AsgiRequest(
            {
                "http_version": "1.1",
                "method": "PUT",
                "path": "/",
                "headers": {
                    "host": b"example.com",
                    "content-length": b"11",
                },
            },
            b"onetwothree",
        )
        self.assertEqual(request.method, "PUT")
        self.assertEqual(request.read(3), b"one")
        self.assertEqual(request.read(), b"twothree")

    def test_script_name(self):

        request = AsgiRequest(
            {
                "http_version": "1.1",
                "method": "GET",
                "path": "/test/",
                "root_path": "/path/to/"
            },
            b"",
        )

        self.assertEqual(request.path, "/path/to/test/")

### Handler tests


class MockHandler(AsgiHandler):
    """
    Testing subclass of AsgiHandler that has the actual Django response part
    ripped out.
    """

    request_class = MagicMock()

    def get_response(self, request):
        return HttpResponse("fake")


@pytest.mark.asyncio
async def test_handler_basic():
    """
    Tests very basic request handling, no body.
    """
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": "/test/",
    }
    handler = ApplicationCommunicator(MockHandler, scope)
    await handler.send_input({
        "type": "http.request",
    })
    await handler.receive_output(1)  # response start
    await handler.receive_output(1)  # response body
    MockHandler.request_class.assert_called_with(scope, b"")


@pytest.mark.asyncio
async def test_handler_body_single():
    """
    Tests request handling with a single-part body
    """
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": "/test/",
    }
    handler = ApplicationCommunicator(MockHandler, scope)
    await handler.send_input({
        "type": "http.request",
        "body": b"chunk one \x01 chunk two",
    })
    await handler.receive_output(1)  # response start
    await handler.receive_output(1)  # response body
    MockHandler.request_class.assert_called_with(scope, b"chunk one \x01 chunk two")


@pytest.mark.asyncio
async def test_handler_body_multiple():
    """
    Tests request handling with a multi-part body
    """
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": "/test/",
    }
    handler = ApplicationCommunicator(MockHandler, scope)
    await handler.send_input({
        "type": "http.request",
        "body": b"chunk one",
        "more_body": True,
    })
    await handler.send_input({
        "type": "http.request",
        "body": b" \x01 ",
        "more_body": True,
    })
    await handler.send_input({
        "type": "http.request",
        "body": b"chunk two",
    })
    await handler.receive_output(1)  # response start
    await handler.receive_output(1)  # response body
    MockHandler.request_class.assert_called_with(scope, b"chunk one \x01 chunk two")


@pytest.mark.asyncio
async def test_handler_body_ignore_extra():
    """
    Tests request handling ignores anything after more_body: False
    """
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": "/test/",
    }
    handler = ApplicationCommunicator(MockHandler, scope)
    await handler.send_input({
        "type": "http.request",
        "body": b"chunk one",
        "more_body": False,
    })
    await handler.send_input({
        "type": "http.request",
        "body": b" \x01 ",
    })
    await handler.receive_output(1)  # response start
    await handler.receive_output(1)  # response body
    MockHandler.request_class.assert_called_with(scope, b"chunk one")


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_sessions():

    class SimpleHttpApp(AsyncConsumer):
        """
        Barebones HTTP ASGI app for testing.
        """

        async def http_request(self, event):
            self.scope["session"].save()
            assert self.scope["path"] == "/test/"
            assert self.scope["method"] == "GET"
            await self.send({
                "type": "http.response.start",
                "status": 200,
                "headers": [],
            })
            await self.send({
                "type": "http.response.body",
                "body": b"test response",
            })

    communicator = HttpCommunicator(SessionMiddlewareStack(SimpleHttpApp), "GET", "/test/")
    response = await communicator.get_response()
    headers = response.get("headers", [])

    assert len(headers) == 1
    name, value = headers[0]

    assert name == b"Set-Cookie"
    value = value.decode("utf-8")

    assert re.compile(r'sessionid=').search(value) is not None

    assert re.compile(r'expires=').search(value) is not None

    assert re.compile(r'HttpOnly').search(value) is not None

    assert re.compile(r'Max-Age').search(value) is not None

    assert re.compile(r'Path').search(value) is not None
