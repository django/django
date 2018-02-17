import pytest
from django.test import override_settings

from channels.generic.websocket import (
    AsyncJsonWebsocketConsumer, AsyncWebsocketConsumer, JsonWebsocketConsumer, WebsocketConsumer,
)
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator


@pytest.mark.asyncio
async def test_websocket_consumer():
    """
    Tests that WebsocketConsumer is implemented correctly.
    """
    results = {}

    class TestConsumer(WebsocketConsumer):
        def connect(self):
            results["connected"] = True
            self.accept()

        def receive(self, text_data=None, bytes_data=None):
            results["received"] = (text_data, bytes_data)
            self.send(text_data=text_data, bytes_data=bytes_data)

        def disconnect(self, code):
            results["disconnected"] = code

    # Test a normal connection
    communicator = WebsocketCommunicator(TestConsumer, "/testws/")
    connected, _ = await communicator.connect()
    assert connected
    assert "connected" in results
    # Test sending text
    await communicator.send_to(text_data="hello")
    response = await communicator.receive_from()
    assert response == "hello"
    assert results["received"] == ("hello", None)
    # Test sending bytes
    await communicator.send_to(bytes_data=b"w\0\0\0")
    response = await communicator.receive_from()
    assert response == b"w\0\0\0"
    assert results["received"] == (None, b"w\0\0\0")
    # Close out
    await communicator.disconnect()
    assert "disconnected" in results


@pytest.mark.asyncio
async def test_websocket_consumer_groups():
    """
    Tests that WebsocketConsumer adds and removes channels from groups.
    """
    results = {}

    class TestConsumer(WebsocketConsumer):
        groups = ["chat"]

        def receive(self, text_data=None, bytes_data=None):
            results["received"] = (text_data, bytes_data)
            self.send(text_data=text_data, bytes_data=bytes_data)

    channel_layers_setting = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }
    with override_settings(CHANNEL_LAYERS=channel_layers_setting):
        communicator = WebsocketCommunicator(TestConsumer, "/testws/")
        await communicator.connect()

        channel_layer = get_channel_layer()
        # Test that the websocket channel was added to the group on connect
        message = {"type": "websocket.receive", "text": "hello"}
        await channel_layer.group_send("chat", message)
        response = await communicator.receive_from()
        assert response == "hello"
        assert results["received"] == ("hello", None)
        # Test that the websocket channel was discarded from the group on disconnect
        await communicator.disconnect()
        assert channel_layer.groups == {}


@pytest.mark.asyncio
async def test_async_websocket_consumer():
    """
    Tests that AsyncWebsocketConsumer is implemented correctly.
    """
    results = {}

    class TestConsumer(AsyncWebsocketConsumer):
        async def connect(self):
            results["connected"] = True
            await self.accept()

        async def receive(self, text_data=None, bytes_data=None):
            results["received"] = (text_data, bytes_data)
            await self.send(text_data=text_data, bytes_data=bytes_data)

        async def disconnect(self, code):
            results["disconnected"] = code

    # Test a normal connection
    communicator = WebsocketCommunicator(TestConsumer, "/testws/")
    connected, _ = await communicator.connect()
    assert connected
    assert "connected" in results
    # Test sending text
    await communicator.send_to(text_data="hello")
    response = await communicator.receive_from()
    assert response == "hello"
    assert results["received"] == ("hello", None)
    # Test sending bytes
    await communicator.send_to(bytes_data=b"w\0\0\0")
    response = await communicator.receive_from()
    assert response == b"w\0\0\0"
    assert results["received"] == (None, b"w\0\0\0")
    # Close out
    await communicator.disconnect()
    assert "disconnected" in results


@pytest.mark.asyncio
async def test_async_websocket_consumer_groups():
    """
    Tests that AsyncWebsocketConsumer adds and removes channels from groups.
    """
    results = {}

    class TestConsumer(AsyncWebsocketConsumer):
        groups = ["chat"]

        async def receive(self, text_data=None, bytes_data=None):
            results["received"] = (text_data, bytes_data)
            await self.send(text_data=text_data, bytes_data=bytes_data)

    channel_layers_setting = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }
    with override_settings(CHANNEL_LAYERS=channel_layers_setting):
        communicator = WebsocketCommunicator(TestConsumer, "/testws/")
        await communicator.connect()

        channel_layer = get_channel_layer()
        # Test that the websocket channel was added to the group on connect
        message = {"type": "websocket.receive", "text": "hello"}
        await channel_layer.group_send("chat", message)
        response = await communicator.receive_from()
        assert response == "hello"
        assert results["received"] == ("hello", None)

        # Test that the websocket channel was discarded from the group on disconnect
        await communicator.disconnect()
        assert channel_layer.groups == {}


@pytest.mark.asyncio
async def test_json_websocket_consumer():
    """
    Tests that JsonWebsocketConsumer is implemented correctly.
    """
    results = {}

    class TestConsumer(JsonWebsocketConsumer):
        def connect(self):
            self.accept()

        def receive_json(self, data=None):
            results["received"] = data
            self.send_json(data)

    # Open a connection
    communicator = WebsocketCommunicator(TestConsumer, "/testws/")
    connected, _ = await communicator.connect()
    assert connected
    # Test sending
    await communicator.send_json_to({"hello": "world"})
    response = await communicator.receive_json_from()
    assert response == {"hello": "world"}
    assert results["received"] == {"hello": "world"}
    # Test sending bytes breaks it
    await communicator.send_to(bytes_data=b"w\0\0\0")
    with pytest.raises(ValueError):
        await communicator.wait()


@pytest.mark.asyncio
async def test_async_json_websocket_consumer():
    """
    Tests that AsyncJsonWebsocketConsumer is implemented correctly.
    """
    results = {}

    class TestConsumer(AsyncJsonWebsocketConsumer):
        async def connect(self):
            await self.accept()

        async def receive_json(self, data=None):
            results["received"] = data
            await self.send_json(data)

    # Open a connection
    communicator = WebsocketCommunicator(TestConsumer, "/testws/")
    connected, _ = await communicator.connect()
    assert connected
    # Test sending
    await communicator.send_json_to({"hello": "world"})
    response = await communicator.receive_json_from()
    assert response == {"hello": "world"}
    assert results["received"] == {"hello": "world"}
    # Test sending bytes breaks it
    await communicator.send_to(bytes_data=b"w\0\0\0")
    with pytest.raises(ValueError):
        await communicator.wait()
