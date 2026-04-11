"""WebSocket client for asyncio."""

import asyncio
import sys
from types import TracebackType
from typing import Any, Optional, Type, cast

import attr

from ._websocket.reader import WebSocketDataQueue
from .client_exceptions import ClientError, ServerTimeoutError, WSMessageTypeError
from .client_reqrep import ClientResponse
from .helpers import calculate_timeout_when, set_result
from .http import (
    WS_CLOSED_MESSAGE,
    WS_CLOSING_MESSAGE,
    WebSocketError,
    WSCloseCode,
    WSMessage,
    WSMsgType,
)
from .http_websocket import _INTERNAL_RECEIVE_TYPES, WebSocketWriter
from .streams import EofStream
from .typedefs import (
    DEFAULT_JSON_DECODER,
    DEFAULT_JSON_ENCODER,
    JSONDecoder,
    JSONEncoder,
)

if sys.version_info >= (3, 11):
    import asyncio as async_timeout
else:
    import async_timeout


@attr.s(frozen=True, slots=True)
class ClientWSTimeout:
    ws_receive = attr.ib(type=Optional[float], default=None)
    ws_close = attr.ib(type=Optional[float], default=None)


DEFAULT_WS_CLIENT_TIMEOUT = ClientWSTimeout(ws_receive=None, ws_close=10.0)


class ClientWebSocketResponse:
    def __init__(
        self,
        reader: WebSocketDataQueue,
        writer: WebSocketWriter,
        protocol: Optional[str],
        response: ClientResponse,
        timeout: ClientWSTimeout,
        autoclose: bool,
        autoping: bool,
        loop: asyncio.AbstractEventLoop,
        *,
        heartbeat: Optional[float] = None,
        compress: int = 0,
        client_notakeover: bool = False,
    ) -> None:
        self._response = response
        self._conn = response.connection

        self._writer = writer
        self._reader = reader
        self._protocol = protocol
        self._closed = False
        self._closing = False
        self._close_code: Optional[int] = None
        self._timeout = timeout
        self._autoclose = autoclose
        self._autoping = autoping
        self._heartbeat = heartbeat
        self._heartbeat_cb: Optional[asyncio.TimerHandle] = None
        self._heartbeat_when: float = 0.0
        if heartbeat is not None:
            self._pong_heartbeat = heartbeat / 2.0
        self._pong_response_cb: Optional[asyncio.TimerHandle] = None
        self._loop = loop
        self._waiting: bool = False
        self._close_wait: Optional[asyncio.Future[None]] = None
        self._exception: Optional[BaseException] = None
        self._compress = compress
        self._client_notakeover = client_notakeover
        self._ping_task: Optional[asyncio.Task[None]] = None

        self._reset_heartbeat()

    def _cancel_heartbeat(self) -> None:
        self._cancel_pong_response_cb()
        if self._heartbeat_cb is not None:
            self._heartbeat_cb.cancel()
            self._heartbeat_cb = None
        if self._ping_task is not None:
            self._ping_task.cancel()
            self._ping_task = None

    def _cancel_pong_response_cb(self) -> None:
        if self._pong_response_cb is not None:
            self._pong_response_cb.cancel()
            self._pong_response_cb = None

    def _reset_heartbeat(self) -> None:
        if self._heartbeat is None:
            return
        self._cancel_pong_response_cb()
        loop = self._loop
        assert loop is not None
        conn = self._conn
        timeout_ceil_threshold = (
            conn._connector._timeout_ceil_threshold if conn is not None else 5
        )
        now = loop.time()
        when = calculate_timeout_when(now, self._heartbeat, timeout_ceil_threshold)
        self._heartbeat_when = when
        if self._heartbeat_cb is None:
            # We do not cancel the previous heartbeat_cb here because
            # it generates a significant amount of TimerHandle churn
            # which causes asyncio to rebuild the heap frequently.
            # Instead _send_heartbeat() will reschedule the next
            # heartbeat if it fires too early.
            self._heartbeat_cb = loop.call_at(when, self._send_heartbeat)

    def _send_heartbeat(self) -> None:
        self._heartbeat_cb = None
        loop = self._loop
        now = loop.time()
        if now < self._heartbeat_when:
            # Heartbeat fired too early, reschedule
            self._heartbeat_cb = loop.call_at(
                self._heartbeat_when, self._send_heartbeat
            )
            return

        conn = self._conn
        timeout_ceil_threshold = (
            conn._connector._timeout_ceil_threshold if conn is not None else 5
        )
        when = calculate_timeout_when(now, self._pong_heartbeat, timeout_ceil_threshold)
        self._cancel_pong_response_cb()
        self._pong_response_cb = loop.call_at(when, self._pong_not_received)

        coro = self._writer.send_frame(b"", WSMsgType.PING)
        if sys.version_info >= (3, 12):
            # Optimization for Python 3.12, try to send the ping
            # immediately to avoid having to schedule
            # the task on the event loop.
            ping_task = asyncio.Task(coro, loop=loop, eager_start=True)
        else:
            ping_task = loop.create_task(coro)

        if not ping_task.done():
            self._ping_task = ping_task
            ping_task.add_done_callback(self._ping_task_done)
        else:
            self._ping_task_done(ping_task)

    def _ping_task_done(self, task: "asyncio.Task[None]") -> None:
        """Callback for when the ping task completes."""
        if not task.cancelled() and (exc := task.exception()):
            self._handle_ping_pong_exception(exc)
        self._ping_task = None

    def _pong_not_received(self) -> None:
        self._handle_ping_pong_exception(
            ServerTimeoutError(f"No PONG received after {self._pong_heartbeat} seconds")
        )

    def _handle_ping_pong_exception(self, exc: BaseException) -> None:
        """Handle exceptions raised during ping/pong processing."""
        if self._closed:
            return
        self._set_closed()
        self._close_code = WSCloseCode.ABNORMAL_CLOSURE
        self._exception = exc
        self._response.close()
        if self._waiting and not self._closing:
            self._reader.feed_data(WSMessage(WSMsgType.ERROR, exc, None), 0)

    def _set_closed(self) -> None:
        """Set the connection to closed.

        Cancel any heartbeat timers and set the closed flag.
        """
        self._closed = True
        self._cancel_heartbeat()

    def _set_closing(self) -> None:
        """Set the connection to closing.

        Cancel any heartbeat timers and set the closing flag.
        """
        self._closing = True
        self._cancel_heartbeat()

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def close_code(self) -> Optional[int]:
        return self._close_code

    @property
    def protocol(self) -> Optional[str]:
        return self._protocol

    @property
    def compress(self) -> int:
        return self._compress

    @property
    def client_notakeover(self) -> bool:
        return self._client_notakeover

    def get_extra_info(self, name: str, default: Any = None) -> Any:
        """extra info from connection transport"""
        conn = self._response.connection
        if conn is None:
            return default
        transport = conn.transport
        if transport is None:
            return default
        return transport.get_extra_info(name, default)

    def exception(self) -> Optional[BaseException]:
        return self._exception

    async def ping(self, message: bytes = b"") -> None:
        await self._writer.send_frame(message, WSMsgType.PING)

    async def pong(self, message: bytes = b"") -> None:
        await self._writer.send_frame(message, WSMsgType.PONG)

    async def send_frame(
        self, message: bytes, opcode: WSMsgType, compress: Optional[int] = None
    ) -> None:
        """Send a frame over the websocket."""
        await self._writer.send_frame(message, opcode, compress)

    async def send_str(self, data: str, compress: Optional[int] = None) -> None:
        if not isinstance(data, str):
            raise TypeError("data argument must be str (%r)" % type(data))
        await self._writer.send_frame(
            data.encode("utf-8"), WSMsgType.TEXT, compress=compress
        )

    async def send_bytes(self, data: bytes, compress: Optional[int] = None) -> None:
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("data argument must be byte-ish (%r)" % type(data))
        await self._writer.send_frame(data, WSMsgType.BINARY, compress=compress)

    async def send_json(
        self,
        data: Any,
        compress: Optional[int] = None,
        *,
        dumps: JSONEncoder = DEFAULT_JSON_ENCODER,
    ) -> None:
        await self.send_str(dumps(data), compress=compress)

    async def close(self, *, code: int = WSCloseCode.OK, message: bytes = b"") -> bool:
        # we need to break `receive()` cycle first,
        # `close()` may be called from different task
        if self._waiting and not self._closing:
            assert self._loop is not None
            self._close_wait = self._loop.create_future()
            self._set_closing()
            self._reader.feed_data(WS_CLOSING_MESSAGE, 0)
            await self._close_wait

        if self._closed:
            return False

        self._set_closed()
        try:
            await self._writer.close(code, message)
        except asyncio.CancelledError:
            self._close_code = WSCloseCode.ABNORMAL_CLOSURE
            self._response.close()
            raise
        except Exception as exc:
            self._close_code = WSCloseCode.ABNORMAL_CLOSURE
            self._exception = exc
            self._response.close()
            return True

        if self._close_code:
            self._response.close()
            return True

        while True:
            try:
                async with async_timeout.timeout(self._timeout.ws_close):
                    msg = await self._reader.read()
            except asyncio.CancelledError:
                self._close_code = WSCloseCode.ABNORMAL_CLOSURE
                self._response.close()
                raise
            except Exception as exc:
                self._close_code = WSCloseCode.ABNORMAL_CLOSURE
                self._exception = exc
                self._response.close()
                return True

            if msg.type is WSMsgType.CLOSE:
                self._close_code = msg.data
                self._response.close()
                return True

    async def receive(self, timeout: Optional[float] = None) -> WSMessage:
        receive_timeout = timeout or self._timeout.ws_receive

        while True:
            if self._waiting:
                raise RuntimeError("Concurrent call to receive() is not allowed")

            if self._closed:
                return WS_CLOSED_MESSAGE
            elif self._closing:
                await self.close()
                return WS_CLOSED_MESSAGE

            try:
                self._waiting = True
                try:
                    if receive_timeout:
                        # Entering the context manager and creating
                        # Timeout() object can take almost 50% of the
                        # run time in this loop so we avoid it if
                        # there is no read timeout.
                        async with async_timeout.timeout(receive_timeout):
                            msg = await self._reader.read()
                    else:
                        msg = await self._reader.read()
                    self._reset_heartbeat()
                finally:
                    self._waiting = False
                    if self._close_wait:
                        set_result(self._close_wait, None)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                self._close_code = WSCloseCode.ABNORMAL_CLOSURE
                raise
            except EofStream:
                self._close_code = WSCloseCode.OK
                await self.close()
                return WSMessage(WSMsgType.CLOSED, None, None)
            except ClientError:
                # Likely ServerDisconnectedError when connection is lost
                self._set_closed()
                self._close_code = WSCloseCode.ABNORMAL_CLOSURE
                return WS_CLOSED_MESSAGE
            except WebSocketError as exc:
                self._close_code = exc.code
                await self.close(code=exc.code)
                return WSMessage(WSMsgType.ERROR, exc, None)
            except Exception as exc:
                self._exception = exc
                self._set_closing()
                self._close_code = WSCloseCode.ABNORMAL_CLOSURE
                await self.close()
                return WSMessage(WSMsgType.ERROR, exc, None)

            if msg.type not in _INTERNAL_RECEIVE_TYPES:
                # If its not a close/closing/ping/pong message
                # we can return it immediately
                return msg

            if msg.type is WSMsgType.CLOSE:
                self._set_closing()
                self._close_code = msg.data
                if not self._closed and self._autoclose:
                    await self.close()
            elif msg.type is WSMsgType.CLOSING:
                self._set_closing()
            elif msg.type is WSMsgType.PING and self._autoping:
                await self.pong(msg.data)
                continue
            elif msg.type is WSMsgType.PONG and self._autoping:
                continue

            return msg

    async def receive_str(self, *, timeout: Optional[float] = None) -> str:
        msg = await self.receive(timeout)
        if msg.type is not WSMsgType.TEXT:
            raise WSMessageTypeError(
                f"Received message {msg.type}:{msg.data!r} is not WSMsgType.TEXT"
            )
        return cast(str, msg.data)

    async def receive_bytes(self, *, timeout: Optional[float] = None) -> bytes:
        msg = await self.receive(timeout)
        if msg.type is not WSMsgType.BINARY:
            raise WSMessageTypeError(
                f"Received message {msg.type}:{msg.data!r} is not WSMsgType.BINARY"
            )
        return cast(bytes, msg.data)

    async def receive_json(
        self,
        *,
        loads: JSONDecoder = DEFAULT_JSON_DECODER,
        timeout: Optional[float] = None,
    ) -> Any:
        data = await self.receive_str(timeout=timeout)
        return loads(data)

    def __aiter__(self) -> "ClientWebSocketResponse":
        return self

    async def __anext__(self) -> WSMessage:
        msg = await self.receive()
        if msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
            raise StopAsyncIteration
        return msg

    async def __aenter__(self) -> "ClientWebSocketResponse":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.close()
