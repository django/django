import pytest

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.security.websocket import OriginValidator
from channels.testing import WebsocketCommunicator


@pytest.mark.asyncio
async def test_origin_validator():
    """
    Tests that OriginValidator correctly allows/denies connections.
    """
    # Make our test application
    application = OriginValidator(AsyncWebsocketConsumer, ["allowed-domain.com"])
    # Test a normal connection
    communicator = WebsocketCommunicator(application, "/", headers=[(b"origin", b"http://allowed-domain.com")])
    connected, _ = await communicator.connect()
    assert connected
    await communicator.disconnect()
    # Test a bad connection
    communicator = WebsocketCommunicator(application, "/", headers=[(b"origin", b"http://bad-domain.com")])
    connected, _ = await communicator.connect()
    assert not connected
