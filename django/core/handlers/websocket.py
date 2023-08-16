import asyncio
import functools
import json
import typing as t

from asgiref.sync import sync_to_async

from django import http
from django.core.exceptions import RequestAborted
from django.core.signals import got_request_exception
from django.utils.log import request_logger


class HttpResponseUpgrade(http.HttpResponse):
    status_code = 101
    handler = None
    sub_protocol = None

    def __init__(self, handler, *args, sub_protocol: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.handler = handler
        self.sub_protocol = sub_protocol


class HttpResponseWSClose(http.HttpResponse):
    status_code = 403
    close_code = None

    def __init__(self, *args, close_code: int = 1000, **kwargs):
        super().__init__(*args, **kwargs)
        self.close_code = close_code


class WSProtoException(Exception):
    pass


class WebSocket:
    def __init__(self, request, receive, send):
        self.request = request
        self._receive = receive
        self._send = send
        self._accepted = False
        self.closed = False

    async def accept(self, response: HttpResponseUpgrade):
        if self._accepted:
            raise WSProtoException("Websocket can be accepted only once")
        # By ASGI spec we should receive 'websocket.connect' first. But some
        # server send it after 'accept'. Communication is async, so just send
        # our part of handshake first - it covers both cases.
        response_headers = []
        for header, value in response.items():
            if isinstance(header, str):
                header = header.encode("ascii")
            if isinstance(value, str):
                value = value.encode("latin1")
            response_headers.append((bytes(header).lower(), bytes(value)))
        await self._send(
            {
                "type": "websocket.accept",
                "subprotocol": response.sub_protocol,
                "headers": response_headers,
            }
        )
        self._accepted = True

    async def close(self, code: int = 1000, reason: str = ""):
        if not self.closed:
            await self._send(
                {"type": "websocket.close", "code": code, "reason": reason}
            )
            self.closed = True

    async def send(self, message: t.Mapping):
        if not self._accepted:
            raise WSProtoException("Websocket needs to be accepted before send")
        if self.closed:
            raise WSProtoException("WebSocket is closed")
        await self._send(message)

    async def receive(self) -> t.Mapping:
        if not self._accepted:
            raise WSProtoException("Websocket needs to be accepted before receive data")
        if self.closed:
            raise WSProtoException("WebSocket is closed")

        message = await self._receive()
        if message["type"] == "websocket.disconnect":
            self.closed = True
            raise RequestAborted()
        if message["type"] != "websocket.receive":
            raise WSProtoException(
                "Wrong websocket receive message type: %s" % message["type"]
            )
        return message

    async def receive_json(self):
        message = await self.receive()
        if "text" in message:
            return json.loads(message["text"])
        return json.loads(message["bytes"].decode())

    async def receive_text(self) -> str:
        message = await self.receive()
        if "text" in message:
            return message["text"]
        return message["bytes"].decode()

    async def receive_bytes(self) -> bytes:
        message = await self.receive()
        if "text" in message:
            return message["text"].encode()
        return message["bytes"]

    async def send_json(self, data, **dumps_kwargs):
        await self.send(
            {"type": "websocket.send", "text": json.dumps(data, **dumps_kwargs)}
        )

    async def send_text(self, text: str):
        if not isinstance(text, str):
            raise WSProtoException("Only text can be send, not %s" % text)
        await self.send({"type": "websocket.send", "text": text})

    async def send_bytes(self, text: bytes):
        if not isinstance(text, bytes):
            raise WSProtoException("Only bytes can be send, not %s" % text)
        await self.send({"type": "websocket.send", "bytes": text})

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_val:
                if isinstance(exc_val, (asyncio.CancelledError, RequestAborted)):
                    return False
                await got_request_exception.asend(sender=None, request=self.request)
                await sync_to_async(request_logger.error, thread_sensitive=False)(
                    "%s: %s",
                    str(exc_val),
                    self.request.path,
                    extra={
                        "status_code": 500,
                        "request": self.request,
                    },
                    exc_info=exc_val,
                )
                if isinstance(exc_val, Exception):
                    return True
        finally:
            await self.close()


def websocket_view(func):
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        async def websocket_handler(ws: WebSocket):
            return await func(request, ws, *args, **kwargs)

        return HttpResponseUpgrade(handler=websocket_handler)

    return wrapper
