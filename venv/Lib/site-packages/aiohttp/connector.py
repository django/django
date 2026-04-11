import asyncio
import functools
import random
import socket
import sys
import traceback
import warnings
from collections import OrderedDict, defaultdict, deque
from contextlib import suppress
from http import HTTPStatus
from itertools import chain, cycle, islice
from time import monotonic
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    DefaultDict,
    Deque,
    Dict,
    Iterator,
    List,
    Literal,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
    cast,
)

import aiohappyeyeballs
from aiohappyeyeballs import AddrInfoType, SocketFactoryType

from . import hdrs, helpers
from .abc import AbstractResolver, ResolveResult
from .client_exceptions import (
    ClientConnectionError,
    ClientConnectorCertificateError,
    ClientConnectorDNSError,
    ClientConnectorError,
    ClientConnectorSSLError,
    ClientHttpProxyError,
    ClientProxyConnectionError,
    ServerFingerprintMismatch,
    UnixClientConnectorError,
    cert_errors,
    ssl_errors,
)
from .client_proto import ResponseHandler
from .client_reqrep import ClientRequest, Fingerprint, _merge_ssl_params
from .helpers import (
    _SENTINEL,
    ceil_timeout,
    is_ip_address,
    noop,
    sentinel,
    set_exception,
    set_result,
)
from .log import client_logger
from .resolver import DefaultResolver

if sys.version_info >= (3, 12):
    from collections.abc import Buffer
else:
    Buffer = Union[bytes, bytearray, "memoryview[int]", "memoryview[bytes]"]

if TYPE_CHECKING:
    import ssl

    SSLContext = ssl.SSLContext
else:
    try:
        import ssl

        SSLContext = ssl.SSLContext
    except ImportError:  # pragma: no cover
        ssl = None  # type: ignore[assignment]
        SSLContext = object  # type: ignore[misc,assignment]

EMPTY_SCHEMA_SET = frozenset({""})
HTTP_SCHEMA_SET = frozenset({"http", "https"})
WS_SCHEMA_SET = frozenset({"ws", "wss"})

HTTP_AND_EMPTY_SCHEMA_SET = HTTP_SCHEMA_SET | EMPTY_SCHEMA_SET
HIGH_LEVEL_SCHEMA_SET = HTTP_AND_EMPTY_SCHEMA_SET | WS_SCHEMA_SET

NEEDS_CLEANUP_CLOSED = (3, 13, 0) <= sys.version_info < (
    3,
    13,
    1,
) or sys.version_info < (3, 12, 7)
# Cleanup closed is no longer needed after https://github.com/python/cpython/pull/118960
# which first appeared in Python 3.12.7 and 3.13.1


__all__ = (
    "BaseConnector",
    "TCPConnector",
    "UnixConnector",
    "NamedPipeConnector",
    "AddrInfoType",
    "SocketFactoryType",
)


if TYPE_CHECKING:
    from .client import ClientTimeout
    from .client_reqrep import ConnectionKey
    from .tracing import Trace


class _DeprecationWaiter:
    __slots__ = ("_awaitable", "_awaited")

    def __init__(self, awaitable: Awaitable[Any]) -> None:
        self._awaitable = awaitable
        self._awaited = False

    def __await__(self) -> Any:
        self._awaited = True
        return self._awaitable.__await__()

    def __del__(self) -> None:
        if not self._awaited:
            warnings.warn(
                "Connector.close() is a coroutine, "
                "please use await connector.close()",
                DeprecationWarning,
            )


async def _wait_for_close(waiters: List[Awaitable[object]]) -> None:
    """Wait for all waiters to finish closing."""
    results = await asyncio.gather(*waiters, return_exceptions=True)
    for res in results:
        if isinstance(res, Exception):
            client_logger.debug("Error while closing connector: %r", res)


class Connection:

    _source_traceback = None

    def __init__(
        self,
        connector: "BaseConnector",
        key: "ConnectionKey",
        protocol: ResponseHandler,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._key = key
        self._connector = connector
        self._loop = loop
        self._protocol: Optional[ResponseHandler] = protocol
        self._callbacks: List[Callable[[], None]] = []

        if loop.get_debug():
            self._source_traceback = traceback.extract_stack(sys._getframe(1))

    def __repr__(self) -> str:
        return f"Connection<{self._key}>"

    def __del__(self, _warnings: Any = warnings) -> None:
        if self._protocol is not None:
            kwargs = {"source": self}
            _warnings.warn(f"Unclosed connection {self!r}", ResourceWarning, **kwargs)
            if self._loop.is_closed():
                return

            self._connector._release(self._key, self._protocol, should_close=True)

            context = {"client_connection": self, "message": "Unclosed connection"}
            if self._source_traceback is not None:
                context["source_traceback"] = self._source_traceback
            self._loop.call_exception_handler(context)

    def __bool__(self) -> Literal[True]:
        """Force subclasses to not be falsy, to make checks simpler."""
        return True

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        warnings.warn(
            "connector.loop property is deprecated", DeprecationWarning, stacklevel=2
        )
        return self._loop

    @property
    def transport(self) -> Optional[asyncio.Transport]:
        if self._protocol is None:
            return None
        return self._protocol.transport

    @property
    def protocol(self) -> Optional[ResponseHandler]:
        return self._protocol

    def add_callback(self, callback: Callable[[], None]) -> None:
        if callback is not None:
            self._callbacks.append(callback)

    def _notify_release(self) -> None:
        callbacks, self._callbacks = self._callbacks[:], []

        for cb in callbacks:
            with suppress(Exception):
                cb()

    def close(self) -> None:
        self._notify_release()

        if self._protocol is not None:
            self._connector._release(self._key, self._protocol, should_close=True)
            self._protocol = None

    def release(self) -> None:
        self._notify_release()

        if self._protocol is not None:
            self._connector._release(self._key, self._protocol)
            self._protocol = None

    @property
    def closed(self) -> bool:
        return self._protocol is None or not self._protocol.is_connected()


class _ConnectTunnelConnection(Connection):
    """Special connection wrapper for CONNECT tunnels that must never be pooled.

    This connection wraps the proxy connection that will be upgraded with TLS.
    It must never be released to the pool because:
    1. Its 'closed' future will never complete, causing session.close() to hang
    2. It represents an intermediate state, not a reusable connection
    3. The real connection (with TLS) will be created separately
    """

    def release(self) -> None:
        """Do nothing - don't pool or close the connection.

        These connections are an intermediate state during the CONNECT tunnel
        setup and will be cleaned up naturally after the TLS upgrade. If they
        were to be pooled, they would never be properly closed, causing
        session.close() to wait forever for their 'closed' future.
        """


class _TransportPlaceholder:
    """placeholder for BaseConnector.connect function"""

    __slots__ = ("closed", "transport")

    def __init__(self, closed_future: asyncio.Future[Optional[Exception]]) -> None:
        """Initialize a placeholder for a transport."""
        self.closed = closed_future
        self.transport = None

    def close(self) -> None:
        """Close the placeholder."""

    def abort(self) -> None:
        """Abort the placeholder (does nothing)."""


class BaseConnector:
    """Base connector class.

    keepalive_timeout - (optional) Keep-alive timeout.
    force_close - Set to True to force close and do reconnect
        after each request (and between redirects).
    limit - The total number of simultaneous connections.
    limit_per_host - Number of simultaneous connections to one host.
    enable_cleanup_closed - Enables clean-up closed ssl transports.
                            Disabled by default.
    timeout_ceil_threshold - Trigger ceiling of timeout values when
                             it's above timeout_ceil_threshold.
    loop - Optional event loop.
    """

    _closed = True  # prevent AttributeError in __del__ if ctor was failed
    _source_traceback = None

    # abort transport after 2 seconds (cleanup broken connections)
    _cleanup_closed_period = 2.0

    allowed_protocol_schema_set = HIGH_LEVEL_SCHEMA_SET

    def __init__(
        self,
        *,
        keepalive_timeout: Union[object, None, float] = sentinel,
        force_close: bool = False,
        limit: int = 100,
        limit_per_host: int = 0,
        enable_cleanup_closed: bool = False,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        timeout_ceil_threshold: float = 5,
    ) -> None:

        if force_close:
            if keepalive_timeout is not None and keepalive_timeout is not sentinel:
                raise ValueError(
                    "keepalive_timeout cannot be set if force_close is True"
                )
        else:
            if keepalive_timeout is sentinel:
                keepalive_timeout = 15.0

        loop = loop or asyncio.get_running_loop()
        self._timeout_ceil_threshold = timeout_ceil_threshold

        self._closed = False
        if loop.get_debug():
            self._source_traceback = traceback.extract_stack(sys._getframe(1))

        # Connection pool of reusable connections.
        # We use a deque to store connections because it has O(1) popleft()
        # and O(1) append() operations to implement a FIFO queue.
        self._conns: DefaultDict[
            ConnectionKey, Deque[Tuple[ResponseHandler, float]]
        ] = defaultdict(deque)
        self._limit = limit
        self._limit_per_host = limit_per_host
        self._acquired: Set[ResponseHandler] = set()
        self._acquired_per_host: DefaultDict[ConnectionKey, Set[ResponseHandler]] = (
            defaultdict(set)
        )
        self._keepalive_timeout = cast(float, keepalive_timeout)
        self._force_close = force_close

        # {host_key: FIFO list of waiters}
        # The FIFO is implemented with an OrderedDict with None keys because
        # python does not have an ordered set.
        self._waiters: DefaultDict[
            ConnectionKey, OrderedDict[asyncio.Future[None], None]
        ] = defaultdict(OrderedDict)

        self._loop = loop
        self._factory = functools.partial(ResponseHandler, loop=loop)

        # start keep-alive connection cleanup task
        self._cleanup_handle: Optional[asyncio.TimerHandle] = None

        # start cleanup closed transports task
        self._cleanup_closed_handle: Optional[asyncio.TimerHandle] = None

        if enable_cleanup_closed and not NEEDS_CLEANUP_CLOSED:
            warnings.warn(
                "enable_cleanup_closed ignored because "
                "https://github.com/python/cpython/pull/118960 is fixed "
                f"in Python version {sys.version_info}",
                DeprecationWarning,
                stacklevel=2,
            )
            enable_cleanup_closed = False

        self._cleanup_closed_disabled = not enable_cleanup_closed
        self._cleanup_closed_transports: List[Optional[asyncio.Transport]] = []
        self._placeholder_future: asyncio.Future[Optional[Exception]] = (
            loop.create_future()
        )
        self._placeholder_future.set_result(None)
        self._cleanup_closed()

    def __del__(self, _warnings: Any = warnings) -> None:
        if self._closed:
            return
        if not self._conns:
            return

        conns = [repr(c) for c in self._conns.values()]

        self._close()

        kwargs = {"source": self}
        _warnings.warn(f"Unclosed connector {self!r}", ResourceWarning, **kwargs)
        context = {
            "connector": self,
            "connections": conns,
            "message": "Unclosed connector",
        }
        if self._source_traceback is not None:
            context["source_traceback"] = self._source_traceback
        self._loop.call_exception_handler(context)

    def __enter__(self) -> "BaseConnector":
        warnings.warn(
            '"with Connector():" is deprecated, '
            'use "async with Connector():" instead',
            DeprecationWarning,
        )
        return self

    def __exit__(self, *exc: Any) -> None:
        self._close()

    async def __aenter__(self) -> "BaseConnector":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]] = None,
        exc_value: Optional[BaseException] = None,
        exc_traceback: Optional[TracebackType] = None,
    ) -> None:
        await self.close()

    @property
    def force_close(self) -> bool:
        """Ultimately close connection on releasing if True."""
        return self._force_close

    @property
    def limit(self) -> int:
        """The total number for simultaneous connections.

        If limit is 0 the connector has no limit.
        The default limit size is 100.
        """
        return self._limit

    @property
    def limit_per_host(self) -> int:
        """The limit for simultaneous connections to the same endpoint.

        Endpoints are the same if they are have equal
        (host, port, is_ssl) triple.
        """
        return self._limit_per_host

    def _cleanup(self) -> None:
        """Cleanup unused transports."""
        if self._cleanup_handle:
            self._cleanup_handle.cancel()
            # _cleanup_handle should be unset, otherwise _release() will not
            # recreate it ever!
            self._cleanup_handle = None

        now = monotonic()
        timeout = self._keepalive_timeout

        if self._conns:
            connections = defaultdict(deque)
            deadline = now - timeout
            for key, conns in self._conns.items():
                alive: Deque[Tuple[ResponseHandler, float]] = deque()
                for proto, use_time in conns:
                    if proto.is_connected() and use_time - deadline >= 0:
                        alive.append((proto, use_time))
                        continue
                    transport = proto.transport
                    proto.close()
                    if not self._cleanup_closed_disabled and key.is_ssl:
                        self._cleanup_closed_transports.append(transport)

                if alive:
                    connections[key] = alive

            self._conns = connections

        if self._conns:
            self._cleanup_handle = helpers.weakref_handle(
                self,
                "_cleanup",
                timeout,
                self._loop,
                timeout_ceil_threshold=self._timeout_ceil_threshold,
            )

    def _cleanup_closed(self) -> None:
        """Double confirmation for transport close.

        Some broken ssl servers may leave socket open without proper close.
        """
        if self._cleanup_closed_handle:
            self._cleanup_closed_handle.cancel()

        for transport in self._cleanup_closed_transports:
            if transport is not None:
                transport.abort()

        self._cleanup_closed_transports = []

        if not self._cleanup_closed_disabled:
            self._cleanup_closed_handle = helpers.weakref_handle(
                self,
                "_cleanup_closed",
                self._cleanup_closed_period,
                self._loop,
                timeout_ceil_threshold=self._timeout_ceil_threshold,
            )

    def close(self, *, abort_ssl: bool = False) -> Awaitable[None]:
        """Close all opened transports.

        :param abort_ssl: If True, SSL connections will be aborted immediately
                         without performing the shutdown handshake. This provides
                         faster cleanup at the cost of less graceful disconnection.
        """
        if not (waiters := self._close(abort_ssl=abort_ssl)):
            # If there are no connections to close, we can return a noop
            # awaitable to avoid scheduling a task on the event loop.
            return _DeprecationWaiter(noop())
        coro = _wait_for_close(waiters)
        if sys.version_info >= (3, 12):
            # Optimization for Python 3.12, try to close connections
            # immediately to avoid having to schedule the task on the event loop.
            task = asyncio.Task(coro, loop=self._loop, eager_start=True)
        else:
            task = self._loop.create_task(coro)
        return _DeprecationWaiter(task)

    def _close(self, *, abort_ssl: bool = False) -> List[Awaitable[object]]:
        waiters: List[Awaitable[object]] = []

        if self._closed:
            return waiters

        self._closed = True

        try:
            if self._loop.is_closed():
                return waiters

            # cancel cleanup task
            if self._cleanup_handle:
                self._cleanup_handle.cancel()

            # cancel cleanup close task
            if self._cleanup_closed_handle:
                self._cleanup_closed_handle.cancel()

            for data in self._conns.values():
                for proto, _ in data:
                    if (
                        abort_ssl
                        and proto.transport
                        and proto.transport.get_extra_info("sslcontext") is not None
                    ):
                        proto.abort()
                    else:
                        proto.close()
                    if closed := proto.closed:
                        waiters.append(closed)

            for proto in self._acquired:
                if (
                    abort_ssl
                    and proto.transport
                    and proto.transport.get_extra_info("sslcontext") is not None
                ):
                    proto.abort()
                else:
                    proto.close()
                if closed := proto.closed:
                    waiters.append(closed)

            for transport in self._cleanup_closed_transports:
                if transport is not None:
                    transport.abort()

            return waiters

        finally:
            self._conns.clear()
            self._acquired.clear()
            for keyed_waiters in self._waiters.values():
                for keyed_waiter in keyed_waiters:
                    keyed_waiter.cancel()
            self._waiters.clear()
            self._cleanup_handle = None
            self._cleanup_closed_transports.clear()
            self._cleanup_closed_handle = None

    @property
    def closed(self) -> bool:
        """Is connector closed.

        A readonly property.
        """
        return self._closed

    def _available_connections(self, key: "ConnectionKey") -> int:
        """
        Return number of available connections.

        The limit, limit_per_host and the connection key are taken into account.

        If it returns less than 1 means that there are no connections
        available.
        """
        # check total available connections
        # If there are no limits, this will always return 1
        total_remain = 1

        if self._limit and (total_remain := self._limit - len(self._acquired)) <= 0:
            return total_remain

        # check limit per host
        if host_remain := self._limit_per_host:
            if acquired := self._acquired_per_host.get(key):
                host_remain -= len(acquired)
            if total_remain > host_remain:
                return host_remain

        return total_remain

    def _update_proxy_auth_header_and_build_proxy_req(
        self, req: ClientRequest
    ) -> ClientRequest:
        """Set Proxy-Authorization header for non-SSL proxy requests and builds the proxy request for SSL proxy requests."""
        url = req.proxy
        assert url is not None
        headers: Dict[str, str] = {}
        if req.proxy_headers is not None:
            headers = req.proxy_headers  # type: ignore[assignment]
        headers[hdrs.HOST] = req.headers[hdrs.HOST]
        proxy_req = ClientRequest(
            hdrs.METH_GET,
            url,
            headers=headers,
            auth=req.proxy_auth,
            loop=self._loop,
            ssl=req.ssl,
        )
        auth = proxy_req.headers.pop(hdrs.AUTHORIZATION, None)
        if auth is not None:
            if not req.is_ssl():
                req.headers[hdrs.PROXY_AUTHORIZATION] = auth
            else:
                proxy_req.headers[hdrs.PROXY_AUTHORIZATION] = auth
        return proxy_req

    async def connect(
        self, req: ClientRequest, traces: List["Trace"], timeout: "ClientTimeout"
    ) -> Connection:
        """Get from pool or create new connection."""
        key = req.connection_key
        if (conn := await self._get(key, traces)) is not None:
            # If we do not have to wait and we can get a connection from the pool
            # we can avoid the timeout ceil logic and directly return the connection
            if req.proxy:
                self._update_proxy_auth_header_and_build_proxy_req(req)
            return conn

        async with ceil_timeout(timeout.connect, timeout.ceil_threshold):
            if self._available_connections(key) <= 0:
                await self._wait_for_available_connection(key, traces)
                if (conn := await self._get(key, traces)) is not None:
                    if req.proxy:
                        self._update_proxy_auth_header_and_build_proxy_req(req)
                    return conn

            placeholder = cast(
                ResponseHandler, _TransportPlaceholder(self._placeholder_future)
            )
            self._acquired.add(placeholder)
            if self._limit_per_host:
                self._acquired_per_host[key].add(placeholder)

            try:
                # Traces are done inside the try block to ensure that the
                # that the placeholder is still cleaned up if an exception
                # is raised.
                if traces:
                    for trace in traces:
                        await trace.send_connection_create_start()
                proto = await self._create_connection(req, traces, timeout)
                if traces:
                    for trace in traces:
                        await trace.send_connection_create_end()
            except BaseException:
                self._release_acquired(key, placeholder)
                raise
            else:
                if self._closed:
                    proto.close()
                    raise ClientConnectionError("Connector is closed.")

        # The connection was successfully created, drop the placeholder
        # and add the real connection to the acquired set. There should
        # be no awaits after the proto is added to the acquired set
        # to ensure that the connection is not left in the acquired set
        # on cancellation.
        self._acquired.remove(placeholder)
        self._acquired.add(proto)
        if self._limit_per_host:
            acquired_per_host = self._acquired_per_host[key]
            acquired_per_host.remove(placeholder)
            acquired_per_host.add(proto)
        return Connection(self, key, proto, self._loop)

    async def _wait_for_available_connection(
        self, key: "ConnectionKey", traces: List["Trace"]
    ) -> None:
        """Wait for an available connection slot."""
        # We loop here because there is a race between
        # the connection limit check and the connection
        # being acquired. If the connection is acquired
        # between the check and the await statement, we
        # need to loop again to check if the connection
        # slot is still available.
        attempts = 0
        while True:
            fut: asyncio.Future[None] = self._loop.create_future()
            keyed_waiters = self._waiters[key]
            keyed_waiters[fut] = None
            if attempts:
                # If we have waited before, we need to move the waiter
                # to the front of the queue as otherwise we might get
                # starved and hit the timeout.
                keyed_waiters.move_to_end(fut, last=False)

            try:
                # Traces happen in the try block to ensure that the
                # the waiter is still cleaned up if an exception is raised.
                if traces:
                    for trace in traces:
                        await trace.send_connection_queued_start()
                await fut
                if traces:
                    for trace in traces:
                        await trace.send_connection_queued_end()
            finally:
                # pop the waiter from the queue if its still
                # there and not already removed by _release_waiter
                keyed_waiters.pop(fut, None)
                if not self._waiters.get(key, True):
                    del self._waiters[key]

            if self._available_connections(key) > 0:
                break
            attempts += 1

    async def _get(
        self, key: "ConnectionKey", traces: List["Trace"]
    ) -> Optional[Connection]:
        """Get next reusable connection for the key or None.

        The connection will be marked as acquired.
        """
        if (conns := self._conns.get(key)) is None:
            return None

        t1 = monotonic()
        while conns:
            proto, t0 = conns.popleft()
            # We will we reuse the connection if its connected and
            # the keepalive timeout has not been exceeded
            if proto.is_connected() and t1 - t0 <= self._keepalive_timeout:
                if not conns:
                    # The very last connection was reclaimed: drop the key
                    del self._conns[key]
                self._acquired.add(proto)
                if self._limit_per_host:
                    self._acquired_per_host[key].add(proto)
                if traces:
                    for trace in traces:
                        try:
                            await trace.send_connection_reuseconn()
                        except BaseException:
                            self._release_acquired(key, proto)
                            raise
                return Connection(self, key, proto, self._loop)

            # Connection cannot be reused, close it
            transport = proto.transport
            proto.close()
            # only for SSL transports
            if not self._cleanup_closed_disabled and key.is_ssl:
                self._cleanup_closed_transports.append(transport)

        # No more connections: drop the key
        del self._conns[key]
        return None

    def _release_waiter(self) -> None:
        """
        Iterates over all waiters until one to be released is found.

        The one to be released is not finished and
        belongs to a host that has available connections.
        """
        if not self._waiters:
            return

        # Having the dict keys ordered this avoids to iterate
        # at the same order at each call.
        queues = list(self._waiters)
        random.shuffle(queues)

        for key in queues:
            if self._available_connections(key) < 1:
                continue

            waiters = self._waiters[key]
            while waiters:
                waiter, _ = waiters.popitem(last=False)
                if not waiter.done():
                    waiter.set_result(None)
                    return

    def _release_acquired(self, key: "ConnectionKey", proto: ResponseHandler) -> None:
        """Release acquired connection."""
        if self._closed:
            # acquired connection is already released on connector closing
            return

        self._acquired.discard(proto)
        if self._limit_per_host and (conns := self._acquired_per_host.get(key)):
            conns.discard(proto)
            if not conns:
                del self._acquired_per_host[key]
        self._release_waiter()

    def _release(
        self,
        key: "ConnectionKey",
        protocol: ResponseHandler,
        *,
        should_close: bool = False,
    ) -> None:
        if self._closed:
            # acquired connection is already released on connector closing
            return

        self._release_acquired(key, protocol)

        if self._force_close or should_close or protocol.should_close:
            transport = protocol.transport
            protocol.close()

            if key.is_ssl and not self._cleanup_closed_disabled:
                self._cleanup_closed_transports.append(transport)
            return

        self._conns[key].append((protocol, monotonic()))

        if self._cleanup_handle is None:
            self._cleanup_handle = helpers.weakref_handle(
                self,
                "_cleanup",
                self._keepalive_timeout,
                self._loop,
                timeout_ceil_threshold=self._timeout_ceil_threshold,
            )

    async def _create_connection(
        self, req: ClientRequest, traces: List["Trace"], timeout: "ClientTimeout"
    ) -> ResponseHandler:
        raise NotImplementedError()


class _DNSCacheTable:
    def __init__(self, ttl: Optional[float] = None) -> None:
        self._addrs_rr: Dict[Tuple[str, int], Tuple[Iterator[ResolveResult], int]] = {}
        self._timestamps: Dict[Tuple[str, int], float] = {}
        self._ttl = ttl

    def __contains__(self, host: object) -> bool:
        return host in self._addrs_rr

    def add(self, key: Tuple[str, int], addrs: List[ResolveResult]) -> None:
        self._addrs_rr[key] = (cycle(addrs), len(addrs))

        if self._ttl is not None:
            self._timestamps[key] = monotonic()

    def remove(self, key: Tuple[str, int]) -> None:
        self._addrs_rr.pop(key, None)

        if self._ttl is not None:
            self._timestamps.pop(key, None)

    def clear(self) -> None:
        self._addrs_rr.clear()
        self._timestamps.clear()

    def next_addrs(self, key: Tuple[str, int]) -> List[ResolveResult]:
        loop, length = self._addrs_rr[key]
        addrs = list(islice(loop, length))
        # Consume one more element to shift internal state of `cycle`
        next(loop)
        return addrs

    def expired(self, key: Tuple[str, int]) -> bool:
        if self._ttl is None:
            return False

        return self._timestamps[key] + self._ttl < monotonic()


def _make_ssl_context(verified: bool) -> SSLContext:
    """Create SSL context.

    This method is not async-friendly and should be called from a thread
    because it will load certificates from disk and do other blocking I/O.
    """
    if ssl is None:
        # No ssl support
        return None
    if verified:
        sslcontext = ssl.create_default_context()
    else:
        sslcontext = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        sslcontext.options |= ssl.OP_NO_SSLv2
        sslcontext.options |= ssl.OP_NO_SSLv3
        sslcontext.check_hostname = False
        sslcontext.verify_mode = ssl.CERT_NONE
        sslcontext.options |= ssl.OP_NO_COMPRESSION
        sslcontext.set_default_verify_paths()
    sslcontext.set_alpn_protocols(("http/1.1",))
    return sslcontext


# The default SSLContext objects are created at import time
# since they do blocking I/O to load certificates from disk,
# and imports should always be done before the event loop starts
# or in a thread.
_SSL_CONTEXT_VERIFIED = _make_ssl_context(True)
_SSL_CONTEXT_UNVERIFIED = _make_ssl_context(False)


class TCPConnector(BaseConnector):
    """TCP connector.

    verify_ssl - Set to True to check ssl certifications.
    fingerprint - Pass the binary sha256
        digest of the expected certificate in DER format to verify
        that the certificate the server presents matches. See also
        https://en.wikipedia.org/wiki/HTTP_Public_Key_Pinning
    resolver - Enable DNS lookups and use this
        resolver
    use_dns_cache - Use memory cache for DNS lookups.
    ttl_dns_cache - Max seconds having cached a DNS entry, None forever.
    family - socket address family
    local_addr - local tuple of (host, port) to bind socket to

    keepalive_timeout - (optional) Keep-alive timeout.
    force_close - Set to True to force close and do reconnect
        after each request (and between redirects).
    limit - The total number of simultaneous connections.
    limit_per_host - Number of simultaneous connections to one host.
    enable_cleanup_closed - Enables clean-up closed ssl transports.
                            Disabled by default.
    happy_eyeballs_delay - This is the “Connection Attempt Delay”
                           as defined in RFC 8305. To disable
                           the happy eyeballs algorithm, set to None.
    interleave - “First Address Family Count” as defined in RFC 8305
    loop - Optional event loop.
    socket_factory - A SocketFactoryType function that, if supplied,
                     will be used to create sockets given an
                     AddrInfoType.
    ssl_shutdown_timeout - DEPRECATED. Will be removed in aiohttp 4.0.
                           Grace period for SSL shutdown handshake on TLS
                           connections. Default is 0 seconds (immediate abort).
                           This parameter allowed for a clean SSL shutdown by
                           notifying the remote peer of connection closure,
                           while avoiding excessive delays during connector cleanup.
                           Note: Only takes effect on Python 3.11+.
    """

    allowed_protocol_schema_set = HIGH_LEVEL_SCHEMA_SET | frozenset({"tcp"})

    def __init__(
        self,
        *,
        verify_ssl: bool = True,
        fingerprint: Optional[bytes] = None,
        use_dns_cache: bool = True,
        ttl_dns_cache: Optional[int] = 10,
        family: socket.AddressFamily = socket.AddressFamily.AF_UNSPEC,
        ssl_context: Optional[SSLContext] = None,
        ssl: Union[bool, Fingerprint, SSLContext] = True,
        local_addr: Optional[Tuple[str, int]] = None,
        resolver: Optional[AbstractResolver] = None,
        keepalive_timeout: Union[None, float, object] = sentinel,
        force_close: bool = False,
        limit: int = 100,
        limit_per_host: int = 0,
        enable_cleanup_closed: bool = False,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        timeout_ceil_threshold: float = 5,
        happy_eyeballs_delay: Optional[float] = 0.25,
        interleave: Optional[int] = None,
        socket_factory: Optional[SocketFactoryType] = None,
        ssl_shutdown_timeout: Union[_SENTINEL, None, float] = sentinel,
    ):
        super().__init__(
            keepalive_timeout=keepalive_timeout,
            force_close=force_close,
            limit=limit,
            limit_per_host=limit_per_host,
            enable_cleanup_closed=enable_cleanup_closed,
            loop=loop,
            timeout_ceil_threshold=timeout_ceil_threshold,
        )

        self._ssl = _merge_ssl_params(ssl, verify_ssl, ssl_context, fingerprint)

        self._resolver: AbstractResolver
        if resolver is None:
            self._resolver = DefaultResolver(loop=self._loop)
            self._resolver_owner = True
        else:
            self._resolver = resolver
            self._resolver_owner = False

        self._use_dns_cache = use_dns_cache
        self._cached_hosts = _DNSCacheTable(ttl=ttl_dns_cache)
        self._throttle_dns_futures: Dict[
            Tuple[str, int], Set["asyncio.Future[None]"]
        ] = {}
        self._family = family
        self._local_addr_infos = aiohappyeyeballs.addr_to_addr_infos(local_addr)
        self._happy_eyeballs_delay = happy_eyeballs_delay
        self._interleave = interleave
        self._resolve_host_tasks: Set["asyncio.Task[List[ResolveResult]]"] = set()
        self._socket_factory = socket_factory
        self._ssl_shutdown_timeout: Optional[float]
        # Handle ssl_shutdown_timeout with warning for Python < 3.11
        if ssl_shutdown_timeout is sentinel:
            self._ssl_shutdown_timeout = 0
        else:
            # Deprecation warning for ssl_shutdown_timeout parameter
            warnings.warn(
                "The ssl_shutdown_timeout parameter is deprecated and will be removed in aiohttp 4.0",
                DeprecationWarning,
                stacklevel=2,
            )
            if (
                sys.version_info < (3, 11)
                and ssl_shutdown_timeout is not None
                and ssl_shutdown_timeout != 0
            ):
                warnings.warn(
                    f"ssl_shutdown_timeout={ssl_shutdown_timeout} is ignored on Python < 3.11; "
                    "only ssl_shutdown_timeout=0 is supported. The timeout will be ignored.",
                    RuntimeWarning,
                    stacklevel=2,
                )
            self._ssl_shutdown_timeout = ssl_shutdown_timeout

    def _close(self, *, abort_ssl: bool = False) -> List[Awaitable[object]]:
        """Close all ongoing DNS calls."""
        for fut in chain.from_iterable(self._throttle_dns_futures.values()):
            fut.cancel()

        waiters = super()._close(abort_ssl=abort_ssl)

        for t in self._resolve_host_tasks:
            t.cancel()
            waiters.append(t)

        return waiters

    async def close(self, *, abort_ssl: bool = False) -> None:
        """
        Close all opened transports.

        :param abort_ssl: If True, SSL connections will be aborted immediately
                         without performing the shutdown handshake. If False (default),
                         the behavior is determined by ssl_shutdown_timeout:
                         - If ssl_shutdown_timeout=0: connections are aborted
                         - If ssl_shutdown_timeout>0: graceful shutdown is performed
        """
        if self._resolver_owner:
            await self._resolver.close()
        # Use abort_ssl param if explicitly set, otherwise use ssl_shutdown_timeout default
        await super().close(abort_ssl=abort_ssl or self._ssl_shutdown_timeout == 0)

    @property
    def family(self) -> int:
        """Socket family like AF_INET."""
        return self._family

    @property
    def use_dns_cache(self) -> bool:
        """True if local DNS caching is enabled."""
        return self._use_dns_cache

    def clear_dns_cache(
        self, host: Optional[str] = None, port: Optional[int] = None
    ) -> None:
        """Remove specified host/port or clear all dns local cache."""
        if host is not None and port is not None:
            self._cached_hosts.remove((host, port))
        elif host is not None or port is not None:
            raise ValueError("either both host and port or none of them are allowed")
        else:
            self._cached_hosts.clear()

    async def _resolve_host(
        self, host: str, port: int, traces: Optional[Sequence["Trace"]] = None
    ) -> List[ResolveResult]:
        """Resolve host and return list of addresses."""
        if is_ip_address(host):
            return [
                {
                    "hostname": host,
                    "host": host,
                    "port": port,
                    "family": self._family,
                    "proto": 0,
                    "flags": 0,
                }
            ]

        if not self._use_dns_cache:

            if traces:
                for trace in traces:
                    await trace.send_dns_resolvehost_start(host)

            res = await self._resolver.resolve(host, port, family=self._family)

            if traces:
                for trace in traces:
                    await trace.send_dns_resolvehost_end(host)

            return res

        key = (host, port)
        if key in self._cached_hosts and not self._cached_hosts.expired(key):
            # get result early, before any await (#4014)
            result = self._cached_hosts.next_addrs(key)

            if traces:
                for trace in traces:
                    await trace.send_dns_cache_hit(host)
            return result

        futures: Set["asyncio.Future[None]"]
        #
        # If multiple connectors are resolving the same host, we wait
        # for the first one to resolve and then use the result for all of them.
        # We use a throttle to ensure that we only resolve the host once
        # and then use the result for all the waiters.
        #
        if key in self._throttle_dns_futures:
            # get futures early, before any await (#4014)
            futures = self._throttle_dns_futures[key]
            future: asyncio.Future[None] = self._loop.create_future()
            futures.add(future)
            if traces:
                for trace in traces:
                    await trace.send_dns_cache_hit(host)
            try:
                await future
            finally:
                futures.discard(future)
            return self._cached_hosts.next_addrs(key)

        # update dict early, before any await (#4014)
        self._throttle_dns_futures[key] = futures = set()
        # In this case we need to create a task to ensure that we can shield
        # the task from cancellation as cancelling this lookup should not cancel
        # the underlying lookup or else the cancel event will get broadcast to
        # all the waiters across all connections.
        #
        coro = self._resolve_host_with_throttle(key, host, port, futures, traces)
        loop = asyncio.get_running_loop()
        if sys.version_info >= (3, 12):
            # Optimization for Python 3.12, try to send immediately
            resolved_host_task = asyncio.Task(coro, loop=loop, eager_start=True)
        else:
            resolved_host_task = loop.create_task(coro)

        if not resolved_host_task.done():
            self._resolve_host_tasks.add(resolved_host_task)
            resolved_host_task.add_done_callback(self._resolve_host_tasks.discard)

        try:
            return await asyncio.shield(resolved_host_task)
        except asyncio.CancelledError:

            def drop_exception(fut: "asyncio.Future[List[ResolveResult]]") -> None:
                with suppress(Exception, asyncio.CancelledError):
                    fut.result()

            resolved_host_task.add_done_callback(drop_exception)
            raise

    async def _resolve_host_with_throttle(
        self,
        key: Tuple[str, int],
        host: str,
        port: int,
        futures: Set["asyncio.Future[None]"],
        traces: Optional[Sequence["Trace"]],
    ) -> List[ResolveResult]:
        """Resolve host and set result for all waiters.

        This method must be run in a task and shielded from cancellation
        to avoid cancelling the underlying lookup.
        """
        try:
            if traces:
                for trace in traces:
                    await trace.send_dns_cache_miss(host)

                for trace in traces:
                    await trace.send_dns_resolvehost_start(host)

            addrs = await self._resolver.resolve(host, port, family=self._family)
            if traces:
                for trace in traces:
                    await trace.send_dns_resolvehost_end(host)

            self._cached_hosts.add(key, addrs)
            for fut in futures:
                set_result(fut, None)
        except BaseException as e:
            # any DNS exception is set for the waiters to raise the same exception.
            # This coro is always run in task that is shielded from cancellation so
            # we should never be propagating cancellation here.
            for fut in futures:
                set_exception(fut, e)
            raise
        finally:
            self._throttle_dns_futures.pop(key)

        return self._cached_hosts.next_addrs(key)

    async def _create_connection(
        self, req: ClientRequest, traces: List["Trace"], timeout: "ClientTimeout"
    ) -> ResponseHandler:
        """Create connection.

        Has same keyword arguments as BaseEventLoop.create_connection.
        """
        if req.proxy:
            _, proto = await self._create_proxy_connection(req, traces, timeout)
        else:
            _, proto = await self._create_direct_connection(req, traces, timeout)

        return proto

    def _get_ssl_context(self, req: ClientRequest) -> Optional[SSLContext]:
        """Logic to get the correct SSL context

        0. if req.ssl is false, return None

        1. if ssl_context is specified in req, use it
        2. if _ssl_context is specified in self, use it
        3. otherwise:
            1. if verify_ssl is not specified in req, use self.ssl_context
               (will generate a default context according to self.verify_ssl)
            2. if verify_ssl is True in req, generate a default SSL context
            3. if verify_ssl is False in req, generate a SSL context that
               won't verify
        """
        if not req.is_ssl():
            return None

        if ssl is None:  # pragma: no cover
            raise RuntimeError("SSL is not supported.")
        sslcontext = req.ssl
        if isinstance(sslcontext, ssl.SSLContext):
            return sslcontext
        if sslcontext is not True:
            # not verified or fingerprinted
            return _SSL_CONTEXT_UNVERIFIED
        sslcontext = self._ssl
        if isinstance(sslcontext, ssl.SSLContext):
            return sslcontext
        if sslcontext is not True:
            # not verified or fingerprinted
            return _SSL_CONTEXT_UNVERIFIED
        return _SSL_CONTEXT_VERIFIED

    def _get_fingerprint(self, req: ClientRequest) -> Optional["Fingerprint"]:
        ret = req.ssl
        if isinstance(ret, Fingerprint):
            return ret
        ret = self._ssl
        if isinstance(ret, Fingerprint):
            return ret
        return None

    async def _wrap_create_connection(
        self,
        *args: Any,
        addr_infos: List[AddrInfoType],
        req: ClientRequest,
        timeout: "ClientTimeout",
        client_error: Type[Exception] = ClientConnectorError,
        **kwargs: Any,
    ) -> Tuple[asyncio.Transport, ResponseHandler]:
        try:
            async with ceil_timeout(
                timeout.sock_connect, ceil_threshold=timeout.ceil_threshold
            ):
                sock = await aiohappyeyeballs.start_connection(
                    addr_infos=addr_infos,
                    local_addr_infos=self._local_addr_infos,
                    happy_eyeballs_delay=self._happy_eyeballs_delay,
                    interleave=self._interleave,
                    loop=self._loop,
                    socket_factory=self._socket_factory,
                )
                # Add ssl_shutdown_timeout for Python 3.11+ when SSL is used
                if (
                    kwargs.get("ssl")
                    and self._ssl_shutdown_timeout
                    and sys.version_info >= (3, 11)
                ):
                    kwargs["ssl_shutdown_timeout"] = self._ssl_shutdown_timeout
                return await self._loop.create_connection(*args, **kwargs, sock=sock)
        except cert_errors as exc:
            raise ClientConnectorCertificateError(req.connection_key, exc) from exc
        except ssl_errors as exc:
            raise ClientConnectorSSLError(req.connection_key, exc) from exc
        except OSError as exc:
            if exc.errno is None and isinstance(exc, asyncio.TimeoutError):
                raise
            raise client_error(req.connection_key, exc) from exc

    async def _wrap_existing_connection(
        self,
        *args: Any,
        req: ClientRequest,
        timeout: "ClientTimeout",
        client_error: Type[Exception] = ClientConnectorError,
        **kwargs: Any,
    ) -> Tuple[asyncio.Transport, ResponseHandler]:
        try:
            async with ceil_timeout(
                timeout.sock_connect, ceil_threshold=timeout.ceil_threshold
            ):
                return await self._loop.create_connection(*args, **kwargs)
        except cert_errors as exc:
            raise ClientConnectorCertificateError(req.connection_key, exc) from exc
        except ssl_errors as exc:
            raise ClientConnectorSSLError(req.connection_key, exc) from exc
        except OSError as exc:
            if exc.errno is None and isinstance(exc, asyncio.TimeoutError):
                raise
            raise client_error(req.connection_key, exc) from exc

    def _fail_on_no_start_tls(self, req: "ClientRequest") -> None:
        """Raise a :py:exc:`RuntimeError` on missing ``start_tls()``.

        It is necessary for TLS-in-TLS so that it is possible to
        send HTTPS queries through HTTPS proxies.

        This doesn't affect regular HTTP requests, though.
        """
        if not req.is_ssl():
            return

        proxy_url = req.proxy
        assert proxy_url is not None
        if proxy_url.scheme != "https":
            return

        self._check_loop_for_start_tls()

    def _check_loop_for_start_tls(self) -> None:
        try:
            self._loop.start_tls
        except AttributeError as attr_exc:
            raise RuntimeError(
                "An HTTPS request is being sent through an HTTPS proxy. "
                "This needs support for TLS in TLS but it is not implemented "
                "in your runtime for the stdlib asyncio.\n\n"
                "Please upgrade to Python 3.11 or higher. For more details, "
                "please see:\n"
                "* https://bugs.python.org/issue37179\n"
                "* https://github.com/python/cpython/pull/28073\n"
                "* https://docs.aiohttp.org/en/stable/"
                "client_advanced.html#proxy-support\n"
                "* https://github.com/aio-libs/aiohttp/discussions/6044\n",
            ) from attr_exc

    def _loop_supports_start_tls(self) -> bool:
        try:
            self._check_loop_for_start_tls()
        except RuntimeError:
            return False
        else:
            return True

    def _warn_about_tls_in_tls(
        self,
        underlying_transport: asyncio.Transport,
        req: ClientRequest,
    ) -> None:
        """Issue a warning if the requested URL has HTTPS scheme."""
        if req.request_info.url.scheme != "https":
            return

        # Check if uvloop is being used, which supports TLS in TLS,
        # otherwise assume that asyncio's native transport is being used.
        if type(underlying_transport).__module__.startswith("uvloop"):
            return

        # Support in asyncio was added in Python 3.11 (bpo-44011)
        asyncio_supports_tls_in_tls = sys.version_info >= (3, 11) or getattr(
            underlying_transport,
            "_start_tls_compatible",
            False,
        )

        if asyncio_supports_tls_in_tls:
            return

        warnings.warn(
            "An HTTPS request is being sent through an HTTPS proxy. "
            "This support for TLS in TLS is known to be disabled "
            "in the stdlib asyncio (Python <3.11). This is why you'll probably see "
            "an error in the log below.\n\n"
            "It is possible to enable it via monkeypatching. "
            "For more details, see:\n"
            "* https://bugs.python.org/issue37179\n"
            "* https://github.com/python/cpython/pull/28073\n\n"
            "You can temporarily patch this as follows:\n"
            "* https://docs.aiohttp.org/en/stable/client_advanced.html#proxy-support\n"
            "* https://github.com/aio-libs/aiohttp/discussions/6044\n",
            RuntimeWarning,
            source=self,
            # Why `4`? At least 3 of the calls in the stack originate
            # from the methods in this class.
            stacklevel=3,
        )

    async def _start_tls_connection(
        self,
        underlying_transport: asyncio.Transport,
        req: ClientRequest,
        timeout: "ClientTimeout",
        client_error: Type[Exception] = ClientConnectorError,
    ) -> Tuple[asyncio.BaseTransport, ResponseHandler]:
        """Wrap the raw TCP transport with TLS."""
        tls_proto = self._factory()  # Create a brand new proto for TLS
        sslcontext = self._get_ssl_context(req)
        if TYPE_CHECKING:
            # _start_tls_connection is unreachable in the current code path
            # if sslcontext is None.
            assert sslcontext is not None

        try:
            async with ceil_timeout(
                timeout.sock_connect, ceil_threshold=timeout.ceil_threshold
            ):
                try:
                    # ssl_shutdown_timeout is only available in Python 3.11+
                    if sys.version_info >= (3, 11) and self._ssl_shutdown_timeout:
                        tls_transport = await self._loop.start_tls(
                            underlying_transport,
                            tls_proto,
                            sslcontext,
                            server_hostname=req.server_hostname or req.host,
                            ssl_handshake_timeout=timeout.total,
                            ssl_shutdown_timeout=self._ssl_shutdown_timeout,
                        )
                    else:
                        tls_transport = await self._loop.start_tls(
                            underlying_transport,
                            tls_proto,
                            sslcontext,
                            server_hostname=req.server_hostname or req.host,
                            ssl_handshake_timeout=timeout.total,
                        )
                except BaseException:
                    # We need to close the underlying transport since
                    # `start_tls()` probably failed before it had a
                    # chance to do this:
                    if self._ssl_shutdown_timeout == 0:
                        underlying_transport.abort()
                    else:
                        underlying_transport.close()
                    raise
                if isinstance(tls_transport, asyncio.Transport):
                    fingerprint = self._get_fingerprint(req)
                    if fingerprint:
                        try:
                            fingerprint.check(tls_transport)
                        except ServerFingerprintMismatch:
                            tls_transport.close()
                            if not self._cleanup_closed_disabled:
                                self._cleanup_closed_transports.append(tls_transport)
                            raise
        except cert_errors as exc:
            raise ClientConnectorCertificateError(req.connection_key, exc) from exc
        except ssl_errors as exc:
            raise ClientConnectorSSLError(req.connection_key, exc) from exc
        except OSError as exc:
            if exc.errno is None and isinstance(exc, asyncio.TimeoutError):
                raise
            raise client_error(req.connection_key, exc) from exc
        except TypeError as type_err:
            # Example cause looks like this:
            # TypeError: transport <asyncio.sslproto._SSLProtocolTransport
            # object at 0x7f760615e460> is not supported by start_tls()

            raise ClientConnectionError(
                "Cannot initialize a TLS-in-TLS connection to host "
                f"{req.host!s}:{req.port:d} through an underlying connection "
                f"to an HTTPS proxy {req.proxy!s} ssl:{req.ssl or 'default'} "
                f"[{type_err!s}]"
            ) from type_err
        else:
            if tls_transport is None:
                msg = "Failed to start TLS (possibly caused by closing transport)"
                raise client_error(req.connection_key, OSError(msg))
            tls_proto.connection_made(
                tls_transport
            )  # Kick the state machine of the new TLS protocol

        return tls_transport, tls_proto

    def _convert_hosts_to_addr_infos(
        self, hosts: List[ResolveResult]
    ) -> List[AddrInfoType]:
        """Converts the list of hosts to a list of addr_infos.

        The list of hosts is the result of a DNS lookup. The list of
        addr_infos is the result of a call to `socket.getaddrinfo()`.
        """
        addr_infos: List[AddrInfoType] = []
        for hinfo in hosts:
            host = hinfo["host"]
            is_ipv6 = ":" in host
            family = socket.AF_INET6 if is_ipv6 else socket.AF_INET
            if self._family and self._family != family:
                continue
            addr = (host, hinfo["port"], 0, 0) if is_ipv6 else (host, hinfo["port"])
            addr_infos.append(
                (family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", addr)
            )
        return addr_infos

    async def _create_direct_connection(
        self,
        req: ClientRequest,
        traces: List["Trace"],
        timeout: "ClientTimeout",
        *,
        client_error: Type[Exception] = ClientConnectorError,
    ) -> Tuple[asyncio.Transport, ResponseHandler]:
        sslcontext = self._get_ssl_context(req)
        fingerprint = self._get_fingerprint(req)

        host = req.url.raw_host
        assert host is not None
        # Replace multiple trailing dots with a single one.
        # A trailing dot is only present for fully-qualified domain names.
        # See https://github.com/aio-libs/aiohttp/pull/7364.
        if host.endswith(".."):
            host = host.rstrip(".") + "."
        port = req.port
        assert port is not None
        try:
            # Cancelling this lookup should not cancel the underlying lookup
            #  or else the cancel event will get broadcast to all the waiters
            #  across all connections.
            hosts = await self._resolve_host(host, port, traces=traces)
        except OSError as exc:
            if exc.errno is None and isinstance(exc, asyncio.TimeoutError):
                raise
            # in case of proxy it is not ClientProxyConnectionError
            # it is problem of resolving proxy ip itself
            raise ClientConnectorDNSError(req.connection_key, exc) from exc

        last_exc: Optional[Exception] = None
        addr_infos = self._convert_hosts_to_addr_infos(hosts)
        while addr_infos:
            # Strip trailing dots, certificates contain FQDN without dots.
            # See https://github.com/aio-libs/aiohttp/issues/3636
            server_hostname = (
                (req.server_hostname or host).rstrip(".") if sslcontext else None
            )

            try:
                transp, proto = await self._wrap_create_connection(
                    self._factory,
                    timeout=timeout,
                    ssl=sslcontext,
                    addr_infos=addr_infos,
                    server_hostname=server_hostname,
                    req=req,
                    client_error=client_error,
                )
            except (ClientConnectorError, asyncio.TimeoutError) as exc:
                last_exc = exc
                aiohappyeyeballs.pop_addr_infos_interleave(addr_infos, self._interleave)
                continue

            if req.is_ssl() and fingerprint:
                try:
                    fingerprint.check(transp)
                except ServerFingerprintMismatch as exc:
                    transp.close()
                    if not self._cleanup_closed_disabled:
                        self._cleanup_closed_transports.append(transp)
                    last_exc = exc
                    # Remove the bad peer from the list of addr_infos
                    sock: socket.socket = transp.get_extra_info("socket")
                    bad_peer = sock.getpeername()
                    aiohappyeyeballs.remove_addr_infos(addr_infos, bad_peer)
                    continue

            return transp, proto
        else:
            assert last_exc is not None
            raise last_exc

    async def _create_proxy_connection(
        self, req: ClientRequest, traces: List["Trace"], timeout: "ClientTimeout"
    ) -> Tuple[asyncio.BaseTransport, ResponseHandler]:
        self._fail_on_no_start_tls(req)
        runtime_has_start_tls = self._loop_supports_start_tls()
        proxy_req = self._update_proxy_auth_header_and_build_proxy_req(req)

        # create connection to proxy server
        transport, proto = await self._create_direct_connection(
            proxy_req, [], timeout, client_error=ClientProxyConnectionError
        )

        if req.is_ssl():
            if runtime_has_start_tls:
                self._warn_about_tls_in_tls(transport, req)

            # For HTTPS requests over HTTP proxy
            # we must notify proxy to tunnel connection
            # so we send CONNECT command:
            #   CONNECT www.python.org:443 HTTP/1.1
            #   Host: www.python.org
            #
            # next we must do TLS handshake and so on
            # to do this we must wrap raw socket into secure one
            # asyncio handles this perfectly
            proxy_req.method = hdrs.METH_CONNECT
            proxy_req.url = req.url
            key = req.connection_key._replace(
                proxy=None, proxy_auth=None, proxy_headers_hash=None
            )
            conn = _ConnectTunnelConnection(self, key, proto, self._loop)
            proxy_resp = await proxy_req.send(conn)
            try:
                protocol = conn._protocol
                assert protocol is not None

                # read_until_eof=True will ensure the connection isn't closed
                # once the response is received and processed allowing
                # START_TLS to work on the connection below.
                protocol.set_response_params(
                    read_until_eof=runtime_has_start_tls,
                    timeout_ceil_threshold=self._timeout_ceil_threshold,
                )
                resp = await proxy_resp.start(conn)
            except BaseException:
                proxy_resp.close()
                conn.close()
                raise
            else:
                conn._protocol = None
                try:
                    if resp.status != 200:
                        message = resp.reason
                        if message is None:
                            message = HTTPStatus(resp.status).phrase
                        raise ClientHttpProxyError(
                            proxy_resp.request_info,
                            resp.history,
                            status=resp.status,
                            message=message,
                            headers=resp.headers,
                        )
                    if not runtime_has_start_tls:
                        rawsock = transport.get_extra_info("socket", default=None)
                        if rawsock is None:
                            raise RuntimeError(
                                "Transport does not expose socket instance"
                            )
                        # Duplicate the socket, so now we can close proxy transport
                        rawsock = rawsock.dup()
                except BaseException:
                    # It shouldn't be closed in `finally` because it's fed to
                    # `loop.start_tls()` and the docs say not to touch it after
                    # passing there.
                    transport.close()
                    raise
                finally:
                    if not runtime_has_start_tls:
                        transport.close()

                if not runtime_has_start_tls:
                    # HTTP proxy with support for upgrade to HTTPS
                    sslcontext = self._get_ssl_context(req)
                    return await self._wrap_existing_connection(
                        self._factory,
                        timeout=timeout,
                        ssl=sslcontext,
                        sock=rawsock,
                        server_hostname=req.host,
                        req=req,
                    )

                return await self._start_tls_connection(
                    # Access the old transport for the last time before it's
                    # closed and forgotten forever:
                    transport,
                    req=req,
                    timeout=timeout,
                )
            finally:
                proxy_resp.close()

        return transport, proto


class UnixConnector(BaseConnector):
    """Unix socket connector.

    path - Unix socket path.
    keepalive_timeout - (optional) Keep-alive timeout.
    force_close - Set to True to force close and do reconnect
        after each request (and between redirects).
    limit - The total number of simultaneous connections.
    limit_per_host - Number of simultaneous connections to one host.
    loop - Optional event loop.
    """

    allowed_protocol_schema_set = HIGH_LEVEL_SCHEMA_SET | frozenset({"unix"})

    def __init__(
        self,
        path: str,
        force_close: bool = False,
        keepalive_timeout: Union[object, float, None] = sentinel,
        limit: int = 100,
        limit_per_host: int = 0,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        super().__init__(
            force_close=force_close,
            keepalive_timeout=keepalive_timeout,
            limit=limit,
            limit_per_host=limit_per_host,
            loop=loop,
        )
        self._path = path

    @property
    def path(self) -> str:
        """Path to unix socket."""
        return self._path

    async def _create_connection(
        self, req: ClientRequest, traces: List["Trace"], timeout: "ClientTimeout"
    ) -> ResponseHandler:
        try:
            async with ceil_timeout(
                timeout.sock_connect, ceil_threshold=timeout.ceil_threshold
            ):
                _, proto = await self._loop.create_unix_connection(
                    self._factory, self._path
                )
        except OSError as exc:
            if exc.errno is None and isinstance(exc, asyncio.TimeoutError):
                raise
            raise UnixClientConnectorError(self.path, req.connection_key, exc) from exc

        return proto


class NamedPipeConnector(BaseConnector):
    """Named pipe connector.

    Only supported by the proactor event loop.
    See also: https://docs.python.org/3/library/asyncio-eventloop.html

    path - Windows named pipe path.
    keepalive_timeout - (optional) Keep-alive timeout.
    force_close - Set to True to force close and do reconnect
        after each request (and between redirects).
    limit - The total number of simultaneous connections.
    limit_per_host - Number of simultaneous connections to one host.
    loop - Optional event loop.
    """

    allowed_protocol_schema_set = HIGH_LEVEL_SCHEMA_SET | frozenset({"npipe"})

    def __init__(
        self,
        path: str,
        force_close: bool = False,
        keepalive_timeout: Union[object, float, None] = sentinel,
        limit: int = 100,
        limit_per_host: int = 0,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        super().__init__(
            force_close=force_close,
            keepalive_timeout=keepalive_timeout,
            limit=limit,
            limit_per_host=limit_per_host,
            loop=loop,
        )
        if not isinstance(
            self._loop,
            asyncio.ProactorEventLoop,  # type: ignore[attr-defined]
        ):
            raise RuntimeError(
                "Named Pipes only available in proactor loop under windows"
            )
        self._path = path

    @property
    def path(self) -> str:
        """Path to the named pipe."""
        return self._path

    async def _create_connection(
        self, req: ClientRequest, traces: List["Trace"], timeout: "ClientTimeout"
    ) -> ResponseHandler:
        try:
            async with ceil_timeout(
                timeout.sock_connect, ceil_threshold=timeout.ceil_threshold
            ):
                _, proto = await self._loop.create_pipe_connection(  # type: ignore[attr-defined]
                    self._factory, self._path
                )
                # the drain is required so that the connection_made is called
                # and transport is set otherwise it is not set before the
                # `assert conn.transport is not None`
                # in client.py's _request method
                await asyncio.sleep(0)
                # other option is to manually set transport like
                # `proto.transport = trans`
        except OSError as exc:
            if exc.errno is None and isinstance(exc, asyncio.TimeoutError):
                raise
            raise ClientConnectorError(req.connection_key, exc) from exc

        return cast(ResponseHandler, proto)
