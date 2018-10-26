from concurrent.futures import TimeoutError
from urllib.parse import unquote

import pytest
from django.conf.urls import url

from channels.consumer import AsyncConsumer
from channels.generic.websocket import WebsocketConsumer
from channels.routing import URLRouter
from channels.testing import HttpCommunicator, WebsocketCommunicator


class SimpleHttpApp(AsyncConsumer):
    """
    Barebones HTTP ASGI app for testing.
    """

    async def http_request(self, event):
        assert self.scope["path"] == "/test/"
        assert self.scope["method"] == "GET"
        assert self.scope["query_string"] == b"foo=bar"
        await self.send({"type": "http.response.start", "status": 200, "headers": []})
        await self.send({"type": "http.response.body", "body": b"test response"})


@pytest.mark.asyncio
async def test_http_communicator():
    """
    Tests that the HTTP communicator class works at a basic level.
    """
    communicator = HttpCommunicator(SimpleHttpApp, "GET", "/test/?foo=bar")
    response = await communicator.get_response()
    assert response["body"] == b"test response"
    assert response["status"] == 200


class SimpleWebsocketApp(WebsocketConsumer):
    """
    Barebones WebSocket ASGI app for testing.
    """

    def connect(self):
        assert self.scope["path"] == "/testws/"
        self.accept()

    def receive(self, text_data=None, bytes_data=None):
        self.send(text_data=text_data, bytes_data=bytes_data)


class ErrorWebsocketApp(WebsocketConsumer):
    """
    Barebones WebSocket ASGI app for error testing.
    """

    def receive(self, text_data=None, bytes_data=None):
        pass


class KwargsWebSocketApp(WebsocketConsumer):
    """
    WebSocket ASGI app used for testing the kwargs arguments in the url_route.
    """

    def connect(self):
        self.accept()
        self.send(text_data=self.scope["url_route"]["kwargs"]["message"])


@pytest.mark.asyncio
async def test_websocket_communicator():
    """
    Tests that the WebSocket communicator class works at a basic level.
    """
    communicator = WebsocketCommunicator(SimpleWebsocketApp, "/testws/")
    # Test connection
    connected, subprotocol = await communicator.connect()
    assert connected
    assert subprotocol is None
    # Test sending text
    await communicator.send_to(text_data="hello")
    response = await communicator.receive_from()
    assert response == "hello"
    # Test sending bytes
    await communicator.send_to(bytes_data=b"w\0\0\0")
    response = await communicator.receive_from()
    assert response == b"w\0\0\0"
    # Test sending JSON
    await communicator.send_json_to({"hello": "world"})
    response = await communicator.receive_json_from()
    assert response == {"hello": "world"}
    # Close out
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_websocket_application():
    """
    Tests that the WebSocket communicator class works with the
    URLRoute application.
    """
    application = URLRouter([url(r"^testws/(?P<message>\w+)/$", KwargsWebSocketApp)])
    communicator = WebsocketCommunicator(application, "/testws/test/")
    connected, subprotocol = await communicator.connect()
    # Test connection
    assert connected
    assert subprotocol is None
    message = await communicator.receive_from()
    assert message == "test"
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_timeout_disconnect():
    """
    Tests that disconnect() still works after a timeout.
    """
    communicator = WebsocketCommunicator(ErrorWebsocketApp, "/testws/")
    # Test connection
    connected, subprotocol = await communicator.connect()
    assert connected
    assert subprotocol is None
    # Test sending text (will error internally)
    await communicator.send_to(text_data="hello")
    with pytest.raises(TimeoutError):
        await communicator.receive_from()
    # Close out
    await communicator.disconnect()


class ConnectionScopeValidator(WebsocketConsumer):
    """
    Tests ASGI specification for the connection scope.
    """

    def connect(self):
        assert self.scope["type"] == "websocket"
        # check if path is a unicode string
        assert isinstance(self.scope["path"], str)
        # check if path has percent escapes decoded
        assert self.scope["path"] == unquote(self.scope["path"])
        # check if query_string is a bytes sequence
        assert isinstance(self.scope["query_string"], bytes)
        self.accept()


paths = [
    "user:pass@example.com:8080/p/a/t/h?query=string#hash",
    "wss://user:pass@example.com:8080/p/a/t/h?query=string#hash",
    "ws://www.example.com/%E9%A6%96%E9%A1%B5/index.php?foo=%E9%A6%96%E9%A1%B5&spam=eggs",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("path", paths)
async def test_connection_scope(path):
    """
    Tests ASGI specification for the the connection scope.
    """
    communicator = WebsocketCommunicator(ConnectionScopeValidator, path)
    connected, _ = await communicator.connect()
    assert connected
    await communicator.disconnect()
