"""Low level HTTP server."""

import asyncio
from typing import Any, Awaitable, Callable, Dict, List, Optional  # noqa

from .abc import AbstractStreamWriter
from .http_parser import RawRequestMessage
from .streams import StreamReader
from .web_protocol import RequestHandler, _RequestFactory, _RequestHandler
from .web_request import BaseRequest

__all__ = ("Server",)


class Server:
    def __init__(
        self,
        handler: _RequestHandler,
        *,
        request_factory: Optional[_RequestFactory] = None,
        handler_cancellation: bool = False,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        **kwargs: Any,
    ) -> None:
        self._loop = loop or asyncio.get_running_loop()
        self._connections: Dict[RequestHandler, asyncio.Transport] = {}
        self._kwargs = kwargs
        # requests_count is the number of requests being processed by the server
        # for the lifetime of the server.
        self.requests_count = 0
        self.request_handler = handler
        self.request_factory = request_factory or self._make_request
        self.handler_cancellation = handler_cancellation

    @property
    def connections(self) -> List[RequestHandler]:
        return list(self._connections.keys())

    def connection_made(
        self, handler: RequestHandler, transport: asyncio.Transport
    ) -> None:
        self._connections[handler] = transport

    def connection_lost(
        self, handler: RequestHandler, exc: Optional[BaseException] = None
    ) -> None:
        if handler in self._connections:
            if handler._task_handler:
                handler._task_handler.add_done_callback(
                    lambda f: self._connections.pop(handler, None)
                )
            else:
                del self._connections[handler]

    def _make_request(
        self,
        message: RawRequestMessage,
        payload: StreamReader,
        protocol: RequestHandler,
        writer: AbstractStreamWriter,
        task: "asyncio.Task[None]",
    ) -> BaseRequest:
        return BaseRequest(message, payload, protocol, writer, task, self._loop)

    def pre_shutdown(self) -> None:
        for conn in self._connections:
            conn.close()

    async def shutdown(self, timeout: Optional[float] = None) -> None:
        coros = (conn.shutdown(timeout) for conn in self._connections)
        await asyncio.gather(*coros)
        self._connections.clear()

    def __call__(self) -> RequestHandler:
        try:
            return RequestHandler(self, loop=self._loop, **self._kwargs)
        except TypeError:
            # Failsafe creation: remove all custom handler_args
            kwargs = {
                k: v
                for k, v in self._kwargs.items()
                if k in ["debug", "access_log_class"]
            }
            return RequestHandler(self, loop=self._loop, **kwargs)
