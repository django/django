import unittest
from unittest.mock import MagicMock

import pytest

from channels.testing import HttpCommunicator
from channels.consumer import AsyncConsumer


class SimpleHttpApp(AsyncConsumer):
    """
    Barebones HTTP ASGI app for testing.
    """

    async def http_request(self, event):
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


@pytest.mark.asyncio
async def test_http_communicator():
    """
    Tests that the HTTP communicator class works at a basic level.
    """
    communicator = HttpCommunicator(SimpleHttpApp, "GET", "/test/")
    response = await communicator.get_response()
    assert response["body"] == b"test response"
    assert response["status"] == 200
