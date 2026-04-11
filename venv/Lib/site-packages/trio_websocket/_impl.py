from __future__ import annotations

import sys
from collections import OrderedDict
from contextlib import asynccontextmanager, AbstractAsyncContextManager
from functools import partial
from ipaddress import ip_address
import itertools
import logging
import random
import ssl
import struct
import urllib.parse
from typing import Any, List, NoReturn, Optional, Union, TypeVar, TYPE_CHECKING, Generic, cast
from importlib.metadata import version

import outcome
import trio
import trio.abc
from wsproto import ConnectionType, WSConnection
from wsproto.connection import ConnectionState
import wsproto.frame_protocol as wsframeproto
from wsproto.events import (
    AcceptConnection,
    BytesMessage,
    CloseConnection,
    Ping,
    Pong,
    RejectConnection,
    RejectData,
    Request,
    TextMessage,
)
import wsproto.utilities

if sys.version_info < (3, 11):  # pragma: no cover
    # pylint doesn't care about the version_info check, so need to ignore the warning
    from exceptiongroup import BaseExceptionGroup  # pylint: disable=redefined-builtin

if TYPE_CHECKING:
    from types import TracebackType
    from typing_extensions import Final
    from collections.abc import AsyncGenerator, Awaitable, Callable, Iterable, Coroutine, Sequence

_IS_TRIO_MULTI_ERROR: Final = tuple(map(int, version("trio").split(".")[:2])) < (0, 22)

if _IS_TRIO_MULTI_ERROR:
    _TRIO_EXC_GROUP_TYPE = trio.MultiError  # type: ignore[attr-defined] # pylint: disable=no-member
else:
    _TRIO_EXC_GROUP_TYPE = BaseExceptionGroup  # pylint: disable=possibly-used-before-assignment

CONN_TIMEOUT: Final = 60 # default connect & disconnect timeout, in seconds
MESSAGE_QUEUE_SIZE: Final = 1
MAX_MESSAGE_SIZE: Final = 2 ** 20 # 1 MiB
RECEIVE_BYTES: Final = 4 * 2 ** 10 # 4 KiB
logger: Final = logging.getLogger('trio-websocket')

T = TypeVar("T")
E = TypeVar("E", bound=BaseException)


class TrioWebsocketInternalError(Exception):
    """Raised as a fallback when open_websocket is unable to unwind an exceptiongroup
    into a single preferred exception. This should never happen, if it does then
    underlying assumptions about the internal code are incorrect.
    """


def _ignore_cancel(exc: E) -> E | None:
    return None if isinstance(exc, trio.Cancelled) else exc


class _preserve_current_exception:
    """A context manager which should surround an ``__exit__`` or
    ``__aexit__`` handler or the contents of a ``finally:``
    block. It ensures that any exception that was being handled
    upon entry is not masked by a `trio.Cancelled` raised within
    the body of the context manager.

    https://github.com/python-trio/trio/issues/1559
    https://gitter.im/python-trio/general?at=5faf2293d37a1a13d6a582cf
    """
    __slots__ = ("_armed",)

    def __init__(self) -> None:
        self._armed = False

    def __enter__(self) -> None:
        self._armed = sys.exc_info()[1] is not None

    def __exit__(
        self,
        ty: type[BaseException] | None,
        value: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        if value is None or not self._armed:
            return False

        if _IS_TRIO_MULTI_ERROR:  # pragma: no cover
            filtered_exception = trio.MultiError.filter(_ignore_cancel, value)  # type: ignore[attr-defined]  # pylint: disable=no-member
        elif isinstance(value, BaseExceptionGroup):  # pylint: disable=possibly-used-before-assignment
            filtered_exception = value.subgroup(lambda exc: not isinstance(exc, trio.Cancelled))
        else:
            filtered_exception = _ignore_cancel(value)
        return filtered_exception is None


@asynccontextmanager
async def open_websocket(
    host: str,
    port: int,
    resource: str,
    *,
    use_ssl: Union[bool, ssl.SSLContext],
    subprotocols: Optional[Iterable[str]] = None,
    extra_headers: Optional[list[tuple[bytes,bytes]]] = None,
    message_queue_size: int = MESSAGE_QUEUE_SIZE,
    max_message_size: int = MAX_MESSAGE_SIZE,
    receive_buffer_size: Union[None, int] = RECEIVE_BYTES,
    connect_timeout: float = CONN_TIMEOUT,
    disconnect_timeout: float = CONN_TIMEOUT
) -> AsyncGenerator[WebSocketConnection, None]:
    '''
    Open a WebSocket client connection to a host.

    This async context manager connects when entering the context manager and
    disconnects when exiting. It yields a
    :class:`WebSocketConnection` instance.

    :param str host: The host to connect to.
    :param int port: The port to connect to.
    :param str resource: The resource, i.e. URL path.
    :param Union[bool, ssl.SSLContext] use_ssl: If this is an SSL context, then
        use that context. If this is ``True`` then use default SSL context. If
        this is ``False`` then disable SSL.
    :param subprotocols: An iterable of strings representing preferred
        subprotocols.
    :param list[tuple[bytes,bytes]] extra_headers: A list of 2-tuples containing
        HTTP header key/value pairs to send with the connection request. Note
        that headers used by the WebSocket protocol (e.g.
        ``Sec-WebSocket-Accept``) will be overwritten.
    :param int message_queue_size: The maximum number of messages that will be
        buffered in the library's internal message queue.
    :param int max_message_size: The maximum message size as measured by
        ``len()``. If a message is received that is larger than this size,
        then the connection is closed with code 1009 (Message Too Big).
    :param Optional[int] receive_buffer_size: The buffer size we use to
        receive messages internally. None to let trio choose. Defaults
        to 4 KiB.
    :param float connect_timeout: The number of seconds to wait for the
        connection before timing out.
    :param float disconnect_timeout: The number of seconds to wait when closing
        the connection before timing out.
    :raises HandshakeError: for any networking error,
        client-side timeout (:exc:`ConnectionTimeout`, :exc:`DisconnectionTimeout`),
        or server rejection (:exc:`ConnectionRejected`) during handshakes.
    '''

    # This context manager tries very very hard not to raise an exceptiongroup
    # in order to be as transparent as possible for the end user.
    # In the trivial case, this means that if user code inside the cm raises
    # we make sure that it doesn't get wrapped.

    # If opening the connection fails, then we will raise that exception. User
    # code is never executed, so we will never have multiple exceptions.

    # After opening the connection, we spawn _reader_task in the background and
    # yield to user code. If only one of those raise a non-cancelled exception
    # we will raise that non-cancelled exception.
    # If we get multiple cancelled, we raise the user's cancelled.
    # If both raise exceptions, we raise the user code's exception with __context__
    # set to a group containing internal exception(s) + any user exception __context__
    # If we somehow get multiple exceptions, but no user exception, then we raise
    # TrioWebsocketInternalError.

    # If closing the connection fails, then that will be raised as the top
    # exception in the last `finally`. If we encountered exceptions in user code
    # or in reader task then they will be set as the `__context__`.


    async def _open_connection(nursery: trio.Nursery) -> WebSocketConnection:
        try:
            with trio.fail_after(connect_timeout):
                return await connect_websocket(nursery, host, port,
                    resource, use_ssl=use_ssl, subprotocols=subprotocols,
                    extra_headers=extra_headers,
                    message_queue_size=message_queue_size,
                    max_message_size=max_message_size,
                    receive_buffer_size=receive_buffer_size)
        except trio.TooSlowError:
            raise ConnectionTimeout from None
        except OSError as e:
            raise HandshakeError from e

    async def _close_connection(connection: WebSocketConnection) -> None:
        try:
            with trio.fail_after(disconnect_timeout):
                await connection.aclose()
        except trio.TooSlowError:
            raise DisconnectionTimeout from None

    def _raise(exc: BaseException) -> NoReturn:
        """This helper allows re-raising an exception without __context__ being set."""
        # cause does not need special handlng, we simply avoid using `raise .. from ..`
        __tracebackhide__ = True
        context = exc.__context__
        try:
            raise exc
        finally:
            exc.__context__ = context
            del exc, context

    connection: WebSocketConnection|None=None
    close_result: outcome.Maybe[None] | None = None
    user_error = None

    # Unwrapping exception groups has a lot of pitfalls, one of them stemming from
    # the exception we raise also being inside the group that's set as the context.
    # This leads to loss of info unless properly handled.
    # See https://github.com/python-trio/flake8-async/issues/298
    # We therefore avoid having the exceptiongroup included as either cause or context

    try:
        async with trio.open_nursery() as new_nursery:
            result = await outcome.acapture(_open_connection, new_nursery)

            if isinstance(result, outcome.Value):
                connection = result.unwrap()
                try:
                    yield connection
                except BaseException as e:
                    user_error = e
                    raise
                finally:
                    close_result = await outcome.acapture(_close_connection, connection)
    # This exception handler should only be entered if either:
    # 1. The _reader_task started in connect_websocket raises
    # 2. User code raises an exception
    # I.e. open/close_connection are not included
    except _TRIO_EXC_GROUP_TYPE as e:
        # user_error, or exception bubbling up from _reader_task
        if len(e.exceptions) == 1:
            _raise(e.exceptions[0])

        # contains at most 1 non-cancelled exceptions
        exception_to_raise: BaseException|None = None
        for sub_exc in e.exceptions:
            if not isinstance(sub_exc, trio.Cancelled):
                if exception_to_raise is not None:
                    # multiple non-cancelled
                    break
                exception_to_raise = sub_exc
        else:
            if exception_to_raise is None:
                # all exceptions are cancelled
                # we reraise the user exception and throw out internal
                if user_error is not None:
                    _raise(user_error)
                # multiple internal Cancelled is not possible afaik
                # but if so we just raise one of them
                _raise(e.exceptions[0])  # pragma: no cover
            # raise the non-cancelled exception
            _raise(exception_to_raise)

        # if we have any KeyboardInterrupt in the group, raise a new KeyboardInterrupt
        # with the group as cause & context
        for sub_exc in e.exceptions:
            if isinstance(sub_exc, KeyboardInterrupt):
                raise KeyboardInterrupt from e

        # Both user code and internal code raised non-cancelled exceptions.
        # We set the context to be an exception group containing internal exceptions
        # and, if not None, `user_error.__context__`
        if user_error is not None:
            exceptions = [subexc for subexc in e.exceptions if subexc is not user_error]
            eg_substr = ''
            # there's technically loss of info here, with __suppress_context__=True you
            # still have original __context__ available, just not printed. But we delete
            # it completely because we can't partially suppress the group
            if user_error.__context__ is not None and not user_error.__suppress_context__:
                exceptions.append(user_error.__context__)
                eg_substr = ' and the context for the user exception'
            eg_str = (
                "Both internal and user exceptions encountered. This group contains "
                "the internal exception(s)" + eg_substr + "."
            )
            user_error.__context__ = BaseExceptionGroup(eg_str, exceptions)
            user_error.__suppress_context__ = False
            _raise(user_error)

        raise TrioWebsocketInternalError(
            "The trio-websocket API is not expected to raise multiple exceptions. "
            "Please report this as a bug to "
            "https://github.com/python-trio/trio-websocket"
        ) from e  # pragma: no cover

    finally:
        if close_result is not None:
            close_result.unwrap()


    # error setting up, unwrap that exception
    if connection is None:
        result.unwrap()


async def connect_websocket(
    nursery: trio.Nursery,
    host: str,
    port: int,
    resource: str,
    *,
    use_ssl: bool | ssl.SSLContext,
    subprotocols: Iterable[str] | None = None,
    extra_headers: list[tuple[bytes, bytes]] | None = None,
    message_queue_size: int = MESSAGE_QUEUE_SIZE,
    max_message_size: int = MAX_MESSAGE_SIZE,
    receive_buffer_size: Union[None, int] = RECEIVE_BYTES,
) -> WebSocketConnection:
    '''
    Return an open WebSocket client connection to a host.

    This function is used to specify a custom nursery to run connection
    background tasks in. The caller is responsible for closing the connection.

    If you don't need a custom nursery, you should probably use
    :func:`open_websocket` instead.

    :param nursery: A Trio nursery to run background tasks in.
    :param str host: The host to connect to.
    :param int port: The port to connect to.
    :param str resource: The resource, i.e. URL path.
    :param Union[bool, ssl.SSLContext] use_ssl: If this is an SSL context, then
        use that context. If this is ``True`` then use default SSL context. If
        this is ``False`` then disable SSL.
    :param subprotocols: An iterable of strings representing preferred
        subprotocols.
    :param list[tuple[bytes,bytes]] extra_headers: A list of 2-tuples containing
        HTTP header key/value pairs to send with the connection request. Note
        that headers used by the WebSocket protocol (e.g.
        ``Sec-WebSocket-Accept``) will be overwritten.
    :param int message_queue_size: The maximum number of messages that will be
        buffered in the library's internal message queue.
    :param int max_message_size: The maximum message size as measured by
        ``len()``. If a message is received that is larger than this size,
        then the connection is closed with code 1009 (Message Too Big).
    :param Optional[int] receive_buffer_size: The buffer size we use to
        receive messages internally. None to let trio choose. Defaults
        to 4 KiB.
    :rtype: WebSocketConnection
    '''
    if use_ssl is True:
        ssl_context = ssl.create_default_context()
    elif use_ssl is False:
        ssl_context = None
    elif isinstance(use_ssl, ssl.SSLContext):
        ssl_context = use_ssl
    else:
        raise TypeError('`use_ssl` argument must be bool or ssl.SSLContext')

    logger.debug('Connecting to ws%s://%s:%d%s',
        '' if ssl_context is None else 's', host, port, resource)
    stream: trio.SSLStream[trio.SocketStream] | trio.SocketStream
    if ssl_context is None:
        stream = await trio.open_tcp_stream(host, port)
    else:
        stream = await trio.open_ssl_over_tcp_stream(host, port,
            ssl_context=ssl_context, https_compatible=True)
    if port in (80, 443):
        host_header = host
    else:
        host_header = f'{host}:{port}'
    connection = WebSocketConnection(stream,
        WSConnection(ConnectionType.CLIENT),
        host=host_header,
        path=resource,
        client_subprotocols=subprotocols, client_extra_headers=extra_headers,
        message_queue_size=message_queue_size,
        max_message_size=max_message_size,
        receive_buffer_size=receive_buffer_size)
    nursery.start_soon(connection._reader_task)
    await connection._open_handshake.wait()
    return connection


def open_websocket_url(
    url: str,
    ssl_context: ssl.SSLContext | None = None,
    *,
    subprotocols: Iterable[str] | None = None,
    extra_headers: list[tuple[bytes, bytes]] | None = None,
    message_queue_size: int = MESSAGE_QUEUE_SIZE,
    max_message_size: int = MAX_MESSAGE_SIZE,
    connect_timeout: float = CONN_TIMEOUT,
    disconnect_timeout: float = CONN_TIMEOUT,
    receive_buffer_size: Union[None, int] = RECEIVE_BYTES,
) -> AbstractAsyncContextManager[WebSocketConnection]:
    '''
    Open a WebSocket client connection to a URL.

    This async context manager connects when entering the context manager and
    disconnects when exiting. It yields a
    :class:`WebSocketConnection` instance.

    :param str url: A WebSocket URL, i.e. `ws:` or `wss:` URL scheme.
    :param ssl_context: Optional SSL context used for ``wss:`` URLs. A default
        SSL context is used for ``wss:`` if this argument is ``None``.
    :type ssl_context: ssl.SSLContext or None
    :param subprotocols: An iterable of strings representing preferred
        subprotocols.
    :param list[tuple[bytes,bytes]] extra_headers: A list of 2-tuples containing
        HTTP header key/value pairs to send with the connection request. Note
        that headers used by the WebSocket protocol (e.g.
        ``Sec-WebSocket-Accept``) will be overwritten.
    :param int message_queue_size: The maximum number of messages that will be
        buffered in the library's internal message queue.
    :param int max_message_size: The maximum message size as measured by
        ``len()``. If a message is received that is larger than this size,
        then the connection is closed with code 1009 (Message Too Big).
    :param Optional[int] receive_buffer_size: The buffer size we use to
        receive messages internally. None to let trio choose. Defaults
        to 4 KiB.
    :param float connect_timeout: The number of seconds to wait for the
        connection before timing out.
    :param float disconnect_timeout: The number of seconds to wait when closing
        the connection before timing out.
    :raises HandshakeError: for any networking error,
        client-side timeout (:exc:`ConnectionTimeout`, :exc:`DisconnectionTimeout`),
        or server rejection (:exc:`ConnectionRejected`) during handshakes.
    '''
    host, port, resource, return_ssl_context = _url_to_host(url, ssl_context)
    return open_websocket(host, port, resource, use_ssl=return_ssl_context,
        subprotocols=subprotocols, extra_headers=extra_headers,
        message_queue_size=message_queue_size,
        max_message_size=max_message_size,
        receive_buffer_size=receive_buffer_size,
        connect_timeout=connect_timeout, disconnect_timeout=disconnect_timeout)


async def connect_websocket_url(
    nursery: trio.Nursery,
    url: str,
    ssl_context: ssl.SSLContext | None = None,
    *,
    subprotocols: Iterable[str] | None = None,
    extra_headers: list[tuple[bytes, bytes]] | None = None,
    message_queue_size: int = MESSAGE_QUEUE_SIZE,
    max_message_size: int = MAX_MESSAGE_SIZE,
    receive_buffer_size: Union[None, int] = RECEIVE_BYTES,
) -> WebSocketConnection:
    '''
    Return an open WebSocket client connection to a URL.

    This function is used to specify a custom nursery to run connection
    background tasks in. The caller is responsible for closing the connection.

    If you don't need a custom nursery, you should probably use
    :func:`open_websocket_url` instead.

    :param nursery: A nursery to run background tasks in.
    :param str url: A WebSocket URL.
    :param ssl_context: Optional SSL context used for ``wss:`` URLs.
    :type ssl_context: ssl.SSLContext or None
    :param subprotocols: An iterable of strings representing preferred
        subprotocols.
    :param list[tuple[bytes,bytes]] extra_headers: A list of 2-tuples containing
        HTTP header key/value pairs to send with the connection request. Note
        that headers used by the WebSocket protocol (e.g.
        ``Sec-WebSocket-Accept``) will be overwritten.
    :param int message_queue_size: The maximum number of messages that will be
        buffered in the library's internal message queue.
    :param int max_message_size: The maximum message size as measured by
        ``len()``. If a message is received that is larger than this size,
        then the connection is closed with code 1009 (Message Too Big).
    :param Optional[int] receive_buffer_size: The buffer size we use to
        receive messages internally. None to let trio choose. Defaults
        to 4 KiB.
    :rtype: WebSocketConnection
    '''
    host, port, resource, return_ssl_context = _url_to_host(url, ssl_context)
    return await connect_websocket(nursery, host, port, resource,
        use_ssl=return_ssl_context, subprotocols=subprotocols,
        extra_headers=extra_headers, message_queue_size=message_queue_size,
        max_message_size=max_message_size,
        receive_buffer_size=receive_buffer_size)


def _url_to_host(
    url: str,
    ssl_context: ssl.SSLContext | None,
) -> tuple[str, int, str, ssl.SSLContext | bool]:
    '''
    Convert a WebSocket URL to a (host,port,resource) tuple.

    The returned ``ssl_context`` is either the same object that was passed in,
    or if ``ssl_context`` is None, then a bool indicating if a default SSL
    context needs to be created.

    :param str url: A WebSocket URL.
    :type ssl_context: ssl.SSLContext or None
    :returns: A tuple of ``(host, port, resource, ssl_context)``.
    '''
    url = str(url)  # For backward compat with isinstance(url, yarl.URL).
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ('ws', 'wss'):
        raise ValueError('WebSocket URL scheme must be "ws:" or "wss:"')
    return_ssl_context: ssl.SSLContext | bool
    if ssl_context is None:
        return_ssl_context = parts.scheme == 'wss'
    elif parts.scheme == 'ws':
        raise ValueError('SSL context must be None for ws: URL scheme')
    else:
        return_ssl_context = ssl_context
    host = parts.hostname
    if host is None:
        raise ValueError('URL host must not be None')
    if parts.port is not None:
        port = parts.port
    else:
        port = 443 if return_ssl_context else 80
    path_qs = parts.path
    # RFC 7230, Section 5.3.1:
    # If the target URI's path component is empty, the client MUST
    # send "/" as the path within the origin-form of request-target.
    if not path_qs:
        path_qs = '/'
    if '?' in url:
        path_qs += '?' + parts.query
    return host, port, path_qs, return_ssl_context


async def wrap_client_stream(
    nursery: trio.Nursery,
    stream: trio.SocketStream | trio.SSLStream[trio.SocketStream],
    host: str,
    resource: str,
    *,
    subprotocols: Iterable[str] | None = None,
    extra_headers: list[tuple[bytes, bytes]] | None = None,
    message_queue_size: int = MESSAGE_QUEUE_SIZE,
    max_message_size: int = MAX_MESSAGE_SIZE,
    receive_buffer_size: Union[None, int] = RECEIVE_BYTES,
) -> WebSocketConnection:
    '''
    Wrap an arbitrary stream in a WebSocket connection.

    This is a low-level function only needed in rare cases. In most cases, you
    should use :func:`open_websocket` or :func:`open_websocket_url`.

    :param nursery: A Trio nursery to run background tasks in.
    :param stream: A Trio stream to be wrapped.
    :type stream: trio.abc.Stream
    :param str host: A host string that will be sent in the ``Host:`` header.
    :param str resource: A resource string, i.e. the path component to be
        accessed on the server.
    :param subprotocols: An iterable of strings representing preferred
        subprotocols.
    :param list[tuple[bytes,bytes]] extra_headers: A list of 2-tuples containing
        HTTP header key/value pairs to send with the connection request. Note
        that headers used by the WebSocket protocol (e.g.
        ``Sec-WebSocket-Accept``) will be overwritten.
    :param int message_queue_size: The maximum number of messages that will be
        buffered in the library's internal message queue.
    :param int max_message_size: The maximum message size as measured by
        ``len()``. If a message is received that is larger than this size,
        then the connection is closed with code 1009 (Message Too Big).
    :param Optional[int] receive_buffer_size: The buffer size we use to
        receive messages internally. None to let trio choose. Defaults
        to 4 KiB.
    :rtype: WebSocketConnection
    '''
    connection = WebSocketConnection(stream,
        WSConnection(ConnectionType.CLIENT),
        host=host, path=resource,
        client_subprotocols=subprotocols, client_extra_headers=extra_headers,
        message_queue_size=message_queue_size,
        max_message_size=max_message_size,
        receive_buffer_size=receive_buffer_size)
    nursery.start_soon(connection._reader_task)
    await connection._open_handshake.wait()
    return connection


async def wrap_server_stream(
    nursery: trio.Nursery,
    stream: trio.abc.Stream,
    message_queue_size: int = MESSAGE_QUEUE_SIZE,
    max_message_size: int = MAX_MESSAGE_SIZE,
    receive_buffer_size: Union[None, int] = RECEIVE_BYTES,
) -> WebSocketRequest:
    '''
    Wrap an arbitrary stream in a server-side WebSocket.

    This is a low-level function only needed in rare cases. In most cases, you
    should use :func:`serve_websocket`.

    :param nursery: A nursery to run background tasks in.
    :param stream: A stream to be wrapped.
    :param int message_queue_size: The maximum number of messages that will be
        buffered in the library's internal message queue.
    :param int max_message_size: The maximum message size as measured by
        ``len()``. If a message is received that is larger than this size,
        then the connection is closed with code 1009 (Message Too Big).
    :param Optional[int] receive_buffer_size: The buffer size we use to
        receive messages internally. None to let trio choose. Defaults
        to 4 KiB.
    :type stream: trio.abc.Stream
    :rtype: WebSocketRequest
    '''
    connection = WebSocketConnection(
        stream,
        WSConnection(ConnectionType.SERVER),
        message_queue_size=message_queue_size,
        max_message_size=max_message_size,
        receive_buffer_size=receive_buffer_size)
    nursery.start_soon(connection._reader_task)
    request = await connection._get_request()
    return request



async def serve_websocket(
    handler: Callable[[WebSocketRequest], Awaitable[None]],
    host: str | bytes | None,
    port: int,
    ssl_context: ssl.SSLContext | None,
    *,
    handler_nursery: trio.Nursery | None = None,
    message_queue_size: int = MESSAGE_QUEUE_SIZE,
    max_message_size: int = MAX_MESSAGE_SIZE,
    receive_buffer_size: Union[None, int] = RECEIVE_BYTES,
    connect_timeout: float = CONN_TIMEOUT,
    disconnect_timeout: float = CONN_TIMEOUT,
    task_status: trio.TaskStatus[WebSocketServer] = trio.TASK_STATUS_IGNORED,
) -> NoReturn:
    """
    Serve a WebSocket over TCP.

    This function supports the Trio nursery start protocol: ``server = await
    nursery.start(serve_websocket, …)``. It will block until the server
    is accepting connections and then return a :class:`WebSocketServer` object.

    Note that if ``host`` is ``None`` and ``port`` is zero, then you may get
    multiple listeners that have *different port numbers!*

    :param handler: An async function that is invoked with a request
        for each new connection.
    :param host: The host interface to bind. This can be an address of an
        interface, a name that resolves to an interface address (e.g.
        ``localhost``), or a wildcard address like ``0.0.0.0`` for IPv4 or
        ``::`` for IPv6. If ``None``, then all local interfaces are bound.
    :type host: str, bytes, or None
    :param int port: The port to bind to.
    :param ssl_context: The SSL context to use for encrypted connections, or
        ``None`` for unencrypted connection.
    :type ssl_context: ssl.SSLContext or None
    :param handler_nursery: An optional nursery to spawn handlers and background
        tasks in. If not specified, a new nursery will be created internally.
    :param int message_queue_size: The maximum number of messages that will be
        buffered in the library's internal message queue.
    :param int max_message_size: The maximum message size as measured by
        ``len()``. If a message is received that is larger than this size,
        then the connection is closed with code 1009 (Message Too Big).
    :param Optional[int] receive_buffer_size: The buffer size we use to
        receive messages internally. None to let trio choose. Defaults
        to 4 KiB.
    :param float connect_timeout: The number of seconds to wait for a client
        to finish connection handshake before timing out.
    :param float disconnect_timeout: The number of seconds to wait for a client
        to finish the closing handshake before timing out.
    :param task_status: Part of Trio nursery start protocol.
    :returns: This function runs until cancelled.
    """
    open_tcp_listeners: (
        partial[Coroutine[Any, Any, list[trio.SocketListener]]]
        | partial[Coroutine[Any, Any, list[trio.SSLListener[trio.SocketStream]]]]
    )
    if ssl_context is None:
        open_tcp_listeners = partial(trio.open_tcp_listeners, port, host=host)
    else:
        open_tcp_listeners = partial(
            trio.open_ssl_over_tcp_listeners,
            port,
            ssl_context,
            host=host,
            https_compatible=True,
        )
    listeners = await open_tcp_listeners()
    server = WebSocketServer(
        handler,
        listeners,
        handler_nursery=handler_nursery,
        message_queue_size=message_queue_size,
        max_message_size=max_message_size,
        receive_buffer_size=receive_buffer_size,
        connect_timeout=connect_timeout,
        disconnect_timeout=disconnect_timeout,
    )
    await server.run(task_status=task_status)


class HandshakeError(Exception):
    '''
    There was an error during connection or disconnection with the websocket
    server.
    '''

class ConnectionTimeout(HandshakeError):
    '''There was a timeout when connecting to the websocket server.'''

class DisconnectionTimeout(HandshakeError):
    '''There was a timeout when disconnecting from the websocket server.'''

class ConnectionClosed(Exception):
    '''
    A WebSocket operation cannot be completed because the connection is closed
    or in the process of closing.
    '''
    def __init__(self, reason: CloseReason | None) -> None:
        '''
        Constructor.

        :param reason:
        :type reason: CloseReason
        '''
        super().__init__(reason)
        self.reason = reason

    def __repr__(self) -> str:
        ''' Return representation. '''
        return f'{self.__class__.__name__}<{self.reason}>'


class ConnectionRejected(HandshakeError):
    '''
    A WebSocket connection could not be established because the server rejected
    the connection attempt.
    '''
    def __init__(
        self,
        status_code: int,
        headers: tuple[tuple[bytes, bytes], ...],
        body: bytes | None,
    ) -> None:
        '''
        Constructor.

        :param reason:
        :type reason: CloseReason
        '''
        super().__init__(status_code, headers, body)
        #: a 3 digit HTTP status code
        self.status_code = status_code
        #: a tuple of 2-tuples containing header key/value pairs
        self.headers = headers
        #: an optional ``bytes`` response body
        self.body = body

    def __repr__(self) -> str:
        ''' Return representation. '''
        return f'{self.__class__.__name__}<status_code={self.status_code}>'


class CloseReason:
    ''' Contains information about why a WebSocket was closed. '''
    def __init__(self, code: int, reason: str | None) -> None:
        '''
        Constructor.

        :param int code:
        :param Optional[str] reason:
        '''
        self._code = code
        try:
            self._name = wsframeproto.CloseReason(code).name
        except ValueError:
            if 1000 <= code <= 2999:
                self._name = 'RFC_RESERVED'
            elif 3000 <= code <= 3999:
                self._name = 'IANA_RESERVED'
            elif 4000 <= code <= 4999:
                self._name = 'PRIVATE_RESERVED'
            else:
                self._name = 'INVALID_CODE'
        self._reason = reason

    @property
    def code(self) -> int:
        ''' (Read-only) The numeric close code. '''
        return self._code

    @property
    def name(self) -> str:
        ''' (Read-only) The human-readable close code. '''
        return self._name

    @property
    def reason(self) -> str | None:
        ''' (Read-only) An arbitrary reason string. '''
        return self._reason

    def __repr__(self) -> str:
        ''' Show close code, name, and reason. '''
        return f'{self.__class__.__name__}' \
               f'<code={self.code}, name={self.name}, reason={self.reason}>'


NULL: Final = object()


class Future(Generic[T]):
    ''' Represents a value that will be available in the future. '''
    def __init__(self) -> None:
        ''' Constructor. '''
        # We do some type shenanigins
        # Would do `T | Literal[NULL]` but that's not right apparently.
        self._value: T = cast(T, NULL)
        self._value_event = trio.Event()

    def set_value(self, value: T) -> None:
        '''
        Set a value, which will notify any waiters.

        :param value:
        '''
        self._value = value
        self._value_event.set()

    async def wait_value(self) -> T:
        '''
        Wait for this future to have a value, then return it.

        :returns: The value set by ``set_value()``.
        '''
        await self._value_event.wait()
        assert self._value is not NULL
        return self._value


class WebSocketRequest:
    '''
    Represents a handshake presented by a client to a server.

    The server may modify the handshake or leave it as is. The server should
    call ``accept()`` to finish the handshake and obtain a connection object.
    '''
    def __init__(
        self,
        connection: WebSocketConnection,
        event: wsproto.events.Request,
    ) -> None:
        '''
        Constructor.

        :param WebSocketConnection connection:
        :type event: wsproto.events.Request
        '''
        self._connection = connection
        self._event = event

    @property
    def headers(self) -> list[tuple[bytes, bytes]]:
        '''
        HTTP headers represented as a list of (name, value) pairs.

        :rtype: list[tuple]
        '''
        return self._event.extra_headers

    @property
    def path(self) -> str:
        '''
        The requested URL path.

        :rtype: str
        '''
        return self._event.target

    @property
    def proposed_subprotocols(self) -> tuple[str, ...]:
        '''
        A tuple of protocols proposed by the client.

        :rtype: tuple[str]
        '''
        return tuple(self._event.subprotocols)

    @property
    def local(self) -> Endpoint | str:
        '''
        The connection's local endpoint.

        :rtype: Endpoint or str
        '''
        return self._connection.local

    @property
    def remote(self) -> Endpoint | str:
        '''
        The connection's remote endpoint.

        :rtype: Endpoint or str
        '''
        return self._connection.remote

    async def accept(
        self,
        *,
        subprotocol: str | None = None,
        extra_headers: list[tuple[bytes, bytes]] | None = None,
    ) -> WebSocketConnection:
        '''
        Accept the request and return a connection object.

        :param subprotocol: The selected subprotocol for this connection.
        :type subprotocol: str or None
        :param extra_headers: A list of 2-tuples containing key/value pairs to
            send as HTTP headers.
        :type extra_headers: list[tuple[bytes,bytes]] or None
        :rtype: WebSocketConnection
        '''
        if extra_headers is None:
            extra_headers = []
        await self._connection._accept(self._event, subprotocol, extra_headers)
        return self._connection

    async def reject(
        self,
        status_code: int,
        *,
        extra_headers: list[tuple[bytes, bytes]] | None = None,
        body: bytes | None = None,
    ) -> None:
        '''
        Reject the handshake.

        :param int status_code: The 3 digit HTTP status code. In order to be
            RFC-compliant, this should NOT be 101, and would ideally be an
            appropriate code in the range 300-599.
        :param list[tuple[bytes,bytes]] extra_headers: A list of 2-tuples
            containing key/value pairs to send as HTTP headers.
        :param body: If provided, this data will be sent in the response
            body, otherwise no response body will be sent.
        :type body: bytes or None
        '''
        extra_headers = extra_headers or []
        body = body or b''
        await self._connection._reject(status_code, extra_headers, body)


def _get_stream_endpoint(
    stream: trio.abc.Stream,
    *,
    local: bool,
) -> Endpoint | str:
    '''
    Construct an endpoint from a stream.

    :param trio.Stream stream:
    :param bool local: If true, return local endpoint. Otherwise return remote.
    :returns: An endpoint instance or ``repr()`` for streams that cannot be
        represented as an endpoint.
    :rtype: Endpoint or str
    '''
    socket, is_ssl = None, False
    if isinstance(stream, trio.SocketStream):
        socket = stream.socket
    elif isinstance(stream, trio.SSLStream):
        socket = stream.transport_stream.socket
        is_ssl = True
    endpoint: Endpoint | str
    if socket:
        addr, port, *_ = socket.getsockname() if local else socket.getpeername()
        endpoint = Endpoint(addr, port, is_ssl)
    else:
        endpoint = repr(stream)
    return endpoint


class WebSocketConnection(trio.abc.AsyncResource):
    ''' A WebSocket connection. '''

    CONNECTION_ID = itertools.count()

    def __init__(
        self,
        stream: trio.abc.Stream,
        ws_connection: wsproto.WSConnection,
        *,
        host: str | None = None,
        path: str | None = None,
        client_subprotocols: Iterable[str] | None = None,
        client_extra_headers: list[tuple[bytes, bytes]] | None = None,
        message_queue_size: int = MESSAGE_QUEUE_SIZE,
        max_message_size: int = MAX_MESSAGE_SIZE,
        receive_buffer_size: Union[None, int] = RECEIVE_BYTES,
    ) -> None:
        '''
        Constructor.

        Generally speaking, users are discouraged from directly instantiating a
        ``WebSocketConnection`` and should instead use one of the convenience
        functions in this module, e.g. ``open_websocket()`` or
        ``serve_websocket()``. This class has some tricky internal logic and
        timing that depends on whether it is an instance of a client connection
        or a server connection. The convenience functions handle this complexity
        for you.

        :param SocketStream stream:
        :param ws_connection wsproto.WSConnection:
        :param str host: The hostname to send in the HTTP request headers. Only
            used for client connections.
        :param str path: The URL path for this connection.
        :param list client_subprotocols: A list of desired subprotocols. Only
            used for client connections.
        :param list[tuple[bytes,bytes]] client_extra_headers: Extra headers to
            send with the connection request. Only used for client connections.
        :param int message_queue_size: The maximum number of messages that will be
            buffered in the library's internal message queue.
        :param int max_message_size: The maximum message size as measured by
            ``len()``. If a message is received that is larger than this size,
            then the connection is closed with code 1009 (Message Too Big).
        :param Optional[int] receive_buffer_size: The buffer size we use to
            receive messages internally. None to let trio choose. Defaults
            to 4 KiB.
        '''
        # NOTE: The implementation uses _close_reason for more than an advisory
        #   purpose.  It's critical internal state, indicating when the
        #   connection is closed or closing.
        self._close_reason: Optional[CloseReason] = None
        self._id = next(self.__class__.CONNECTION_ID)
        self._stream = stream
        self._stream_lock = trio.StrictFIFOLock()
        self._wsproto = ws_connection
        self._message_size = 0
        self._message_parts: List[Union[bytes, str]] = []
        self._max_message_size = max_message_size
        self._receive_buffer_size: Optional[int] = receive_buffer_size
        self._reader_running = True
        if ws_connection.client:
            assert host is not None
            assert path is not None
            self._initial_request: Optional[Request] = Request(host=host, target=path,
                subprotocols=list(client_subprotocols or ()),
                extra_headers=client_extra_headers or [])
        else:
            self._initial_request = None
        self._path = path
        self._subprotocol: Optional[str] = None
        self._handshake_headers: tuple[tuple[bytes, bytes], ...] = ()
        self._reject_status = 0
        self._reject_headers: tuple[tuple[bytes, bytes], ...] = ()
        self._reject_body = b''
        self._send_channel, self._recv_channel = trio.open_memory_channel[
            Union[bytes, str]
        ](message_queue_size)
        self._pings: OrderedDict[bytes, trio.Event] = OrderedDict()
        # Set when the server has received a connection request event. This
        # future is never set on client connections.
        self._connection_proposal: Future[WebSocketRequest] | None = Future[WebSocketRequest]()
        # Set once the WebSocket open handshake takes place, i.e.
        # ConnectionRequested for server or ConnectedEstablished for client.
        self._open_handshake = trio.Event()
        # Set once a WebSocket closed handshake takes place, i.e after a close
        # frame has been sent and a close frame has been received.
        self._close_handshake = trio.Event()
        # Set upon receiving CloseConnection from peer.
        # Used to test close race conditions between client and server.
        self._for_testing_peer_closed_connection = trio.Event()

    @property
    def closed(self) -> CloseReason | None:
        '''
        (Read-only) The reason why the connection was or is being closed,
        else ``None``.

        :rtype: Optional[CloseReason]
        '''
        return self._close_reason

    @property
    def is_client(self) -> bool:
        ''' (Read-only) Is this a client instance? '''
        return self._wsproto.client

    @property
    def is_server(self) -> bool:
        ''' (Read-only) Is this a server instance? '''
        return not self._wsproto.client

    @property
    def local(self) -> Endpoint | str:
        '''
        The local endpoint of the connection.

        :rtype: Endpoint or str
        '''
        return _get_stream_endpoint(self._stream, local=True)

    @property
    def remote(self) -> Endpoint | str:
        '''
        The remote endpoint of the connection.

        :rtype: Endpoint or str
        '''
        return _get_stream_endpoint(self._stream, local=False)

    @property
    def path(self) -> str | None:
        '''
        The requested URL path. For clients, this is set when the connection is
        instantiated. For servers, it is set after the handshake completes.

        :rtype: str or None
        '''
        return self._path

    @property
    def subprotocol(self) -> str | None:
        '''
        (Read-only) The negotiated subprotocol, or ``None`` if there is no
        subprotocol.

        This is only valid after the opening handshake is complete.

        :rtype: str or None
        '''
        return self._subprotocol

    @property
    def handshake_headers(self) -> tuple[tuple[bytes, bytes], ...]:
        '''
        The HTTP headers that were sent by the remote during the handshake,
        stored as 2-tuples containing key/value pairs. Header keys are always
        lower case.

        :rtype: tuple[tuple[str,str]]
        '''
        return self._handshake_headers

    async def aclose(self, code: int = 1000, reason: str | None = None) -> None:  # pylint: disable=arguments-differ
        '''
        Close the WebSocket connection.

        This sends a closing frame and suspends until the connection is closed.
        After calling this method, any further I/O on this WebSocket (such as
        ``get_message()`` or ``send_message()``) will raise
        ``ConnectionClosed``.

        This method is idempotent: it may be called multiple times on the same
        connection without any errors.

        :param int code: A 4-digit code number indicating the type of closure.
        :param str reason: An optional string describing the closure.
        '''
        with _preserve_current_exception():
            await self._aclose(code, reason)

    async def _aclose(self, code: int, reason: str | None) -> None:
        if self._close_reason:
            # Per AsyncResource interface, calling aclose() on a closed resource
            # should succeed.
            return
        try:
            if self._wsproto.state == ConnectionState.OPEN:
                # Our side is initiating the close, so send a close connection
                # event to peer, while setting the local close reason to normal.
                self._close_reason = CloseReason(1000, None)
                await self._send(CloseConnection(code=code, reason=reason))
            elif self._wsproto.state in (ConnectionState.CONNECTING,
                    ConnectionState.REJECTING):
                self._close_handshake.set()
            # TODO: shouldn't the receive channel be closed earlier, so that
            #  get_message() during send of the CloseConneciton event fails?
            await self._recv_channel.aclose()
            await self._close_handshake.wait()
        except ConnectionClosed:
            # If _send() raised ConnectionClosed, then we can bail out.
            pass
        finally:
            # If cancelled during WebSocket close, make sure that the underlying
            # stream is closed.
            await self._close_stream()

    async def get_message(self) -> str | bytes:
        '''
        Receive the next WebSocket message.

        If no message is available immediately, then this function blocks until
        a message is ready.

        If the remote endpoint closes the connection, then the caller can still
        get messages sent prior to closing. Once all pending messages have been
        retrieved, additional calls to this method will raise
        ``ConnectionClosed``. If the local endpoint closes the connection, then
        pending messages are discarded and calls to this method will immediately
        raise ``ConnectionClosed``.

        :rtype: str or bytes
        :raises ConnectionClosed: if the connection is closed.
        '''
        try:
            message = await self._recv_channel.receive()
        except (trio.ClosedResourceError, trio.EndOfChannel):
            raise ConnectionClosed(self._close_reason) from None
        return message

    async def ping(self, payload: bytes | None = None) -> None:
        '''
        Send WebSocket ping to remote endpoint and wait for a correspoding pong.

        Each in-flight ping must include a unique payload. This function sends
        the ping and then waits for a corresponding pong from the remote
        endpoint.

        *Note: If the remote endpoint recieves multiple pings, it is allowed to
        send a single pong. Therefore, the order of calls to ``ping()`` is
        tracked, and a pong will wake up its corresponding ping as well as all
        previous in-flight pings.*

        :param payload: The payload to send. If ``None`` then a random 32-bit
            payload is created.
        :type payload: bytes or None
        :raises ConnectionClosed: if connection is closed.
        :raises ValueError: if ``payload`` is identical to another in-flight
            ping.
        '''
        if self._close_reason:
            raise ConnectionClosed(self._close_reason)
        if payload in self._pings:
            raise ValueError(f'Payload value {payload!r} is already in flight.')
        if payload is None:
            payload = struct.pack('!I', random.getrandbits(32))
        event = trio.Event()
        self._pings[payload] = event
        await self._send(Ping(payload=payload))
        await event.wait()

    async def pong(self, payload: bytes | None = None) -> None:
        '''
        Send an unsolicted pong.

        :param payload: The pong's payload. If ``None``, then no payload is
            sent.
        :type payload: bytes or None
        :raises ConnectionClosed: if connection is closed
        '''
        if self._close_reason:
            raise ConnectionClosed(self._close_reason)
        await self._send(Pong(payload=payload or b''))

    async def send_message(self, message: str | bytes) -> None:
        '''
        Send a WebSocket message.

        :param message: The message to send.
        :type message: str or bytes
        :raises ConnectionClosed: if connection is closed, or being closed
        '''
        if self._close_reason:
            raise ConnectionClosed(self._close_reason)
        event: TextMessage | BytesMessage
        if isinstance(message, str):
            event = TextMessage(data=message)
        elif isinstance(message, bytes):
            event = BytesMessage(data=message)
        else:
            raise ValueError('message must be str or bytes')
        await self._send(event)

    def __str__(self) -> str:
        ''' Connection ID and type. '''
        type_ = 'client' if self.is_client else 'server'
        return f'{type_}-{self._id}'

    async def _accept(
        self,
        request: Request,
        subprotocol: str | None,
        extra_headers: list[tuple[bytes, bytes]],
    ) -> None:
        '''
        Accept the handshake.

        This method is only applicable to server-side connections.

        :param wsproto.events.Request request:
        :param subprotocol:
        :type subprotocol: str or None
        :param list[tuple[bytes,bytes]] extra_headers: A list of 2-tuples
            containing key/value pairs to send as HTTP headers.
        '''
        self._subprotocol = subprotocol
        self._path = request.target
        await self._send(AcceptConnection(subprotocol=self._subprotocol,
            extra_headers=extra_headers))
        self._open_handshake.set()

    async def _reject(
        self,
        status_code: int,
        headers: list[tuple[bytes, bytes]],
        body: bytes,
    ) -> None:
        '''
        Reject the handshake.

        :param int status_code: The 3 digit HTTP status code. In order to be
            RFC-compliant, this must not be 101, and should be an appropriate
            code in the range 300-599.
        :param list[tuple[bytes,bytes]] headers: A list of 2-tuples containing
            key/value pairs to send as HTTP headers.
        :param bytes body: An optional response body.
        '''
        if body:
            headers.append((b'Content-length', str(len(body)).encode('ascii')))
        reject_conn = RejectConnection(status_code=status_code, headers=headers,
            has_body=bool(body))
        await self._send(reject_conn)
        if body:
            reject_body = RejectData(data=body)
            await self._send(reject_body)
        self._close_reason = CloseReason(1006, 'Rejected WebSocket handshake')
        self._close_handshake.set()

    async def _abort_web_socket(self) -> None:
        '''
        If a stream is closed outside of this class, e.g. due to network
        conditions or because some other code closed our stream object, then we
        cannot perform the close handshake. We just need to clean up internal
        state.
        '''
        close_reason = wsframeproto.CloseReason.ABNORMAL_CLOSURE
        if self._wsproto.state == ConnectionState.OPEN:
            self._wsproto.send(CloseConnection(code=close_reason.value))
        if self._close_reason is None:
            await self._close_web_socket(close_reason)
        self._reader_running = False
        # We didn't really handshake, but we want any task waiting on this event
        # (e.g. self.aclose()) to resume.
        self._close_handshake.set()

    async def _close_stream(self) -> None:
        ''' Close the TCP connection. '''
        self._reader_running = False
        try:
            with _preserve_current_exception():
                await self._stream.aclose()
        except trio.BrokenResourceError:
            # This means the TCP connection is already dead.
            pass

    async def _close_web_socket(self, code: int, reason: str | None = None) -> None:
        '''
        Mark the WebSocket as closed. Close the message channel so that if any
        tasks are suspended in get_message(), they will wake up with a
        ConnectionClosed exception.
        '''
        self._close_reason = CloseReason(code, reason)
        exc = ConnectionClosed(self._close_reason)
        logger.debug('%s websocket closed %r', self, exc)
        await self._send_channel.aclose()

    async def _get_request(self) -> WebSocketRequest:
        '''
        Return a proposal for a WebSocket handshake.

        This method can only be called on server connections and it may only be
        called one time.

        :rtype: WebSocketRequest
        '''
        if not self.is_server:
            raise RuntimeError('This method is only valid for server connections.')
        if self._connection_proposal is None:
            raise RuntimeError('No proposal available. Did you call this method'
                ' multiple times or at the wrong time?')
        proposal = await self._connection_proposal.wait_value()
        self._connection_proposal = None
        return proposal

    async def _handle_request_event(self, event: wsproto.events.Request) -> None:
        '''
        Handle a connection request.

        This method is async even though it never awaits, because the event
        dispatch requires an async function.

        :param event:
        '''
        proposal = WebSocketRequest(self, event)
        assert self._connection_proposal is not None
        self._connection_proposal.set_value(proposal)

    async def _handle_accept_connection_event(self, event: wsproto.events.AcceptConnection) -> None:
        '''
        Handle an AcceptConnection event.

        :param wsproto.eventsAcceptConnection event:
        '''
        self._subprotocol = event.subprotocol
        self._handshake_headers = tuple(event.extra_headers)
        self._open_handshake.set()

    async def _handle_reject_connection_event(self, event: wsproto.events.RejectConnection) -> None:
        '''
        Handle a RejectConnection event.

        :param event:
        '''
        self._reject_status = event.status_code
        self._reject_headers = tuple(event.headers)
        if not event.has_body:
            raise ConnectionRejected(self._reject_status, self._reject_headers,
                body=None)

    async def _handle_reject_data_event(self, event: wsproto.events.RejectData) -> None:
        '''
        Handle a RejectData event.

        :param event:
        '''
        self._reject_body += event.data
        if event.body_finished:
            raise ConnectionRejected(self._reject_status, self._reject_headers,
                body=self._reject_body)

    async def _handle_close_connection_event(self, event: wsproto.events.CloseConnection) -> None:
        '''
        Handle a close event.

        :param wsproto.events.CloseConnection event:
        '''
        if self._wsproto.state == ConnectionState.REMOTE_CLOSING:
            # Set _close_reason in advance, so that send_message() will raise
            # ConnectionClosed during the close handshake.
            self._close_reason = CloseReason(event.code, event.reason or None)
            self._for_testing_peer_closed_connection.set()
            await self._send(event.response())
        await self._close_web_socket(event.code, event.reason or None)
        self._close_handshake.set()
        # RFC: "When a server is instructed to Close the WebSocket Connection
        #   it SHOULD initiate a TCP Close immediately, and when a client is
        #   instructed to do the same, it SHOULD wait for a TCP Close from the
        #   server."
        if self.is_server:
            await self._close_stream()

    async def _handle_message_event(
        self,
        event: wsproto.events.BytesMessage | wsproto.events.TextMessage,
    ) -> None:
        '''
        Handle a message event.

        :param event:
        :type event: wsproto.events.BytesMessage or wsproto.events.TextMessage
        '''
        self._message_size += len(event.data)
        self._message_parts.append(event.data)
        if self._message_size > self._max_message_size:
            err = f'Exceeded maximum message size: {self._max_message_size} bytes'
            self._message_size = 0
            self._message_parts = []
            self._close_reason = CloseReason(1009, err)
            await self._send(CloseConnection(code=1009, reason=err))
            await self._recv_channel.aclose()
            self._reader_running = False
        elif event.message_finished:
            msg: str | bytes
            # Type checker does not understand `_message_parts`
            if isinstance(event, BytesMessage):
                msg = b''.join(cast("list[bytes]", self._message_parts))
            else:
                msg = ''.join(cast("list[str]", self._message_parts))
            self._message_size = 0
            self._message_parts = []
            try:
                await self._send_channel.send(msg)
            except (trio.ClosedResourceError, trio.BrokenResourceError):
                # The receive channel is closed, probably because somebody
                # called ``aclose()``. We don't want to abort the reader task,
                # and there's no useful cleanup that we can do here.
                pass

    async def _handle_ping_event(self, event: wsproto.events.Ping) -> None:
        '''
        Handle a PingReceived event.

        Wsproto queues a pong frame automatically, so this handler just needs to
        send it.

        :param wsproto.events.Ping event:
        '''
        logger.debug('%s ping %r', self, event.payload)
        await self._send(event.response())

    async def _handle_pong_event(self, event: wsproto.events.Pong) -> None:
        '''
        Handle a PongReceived event.

        When a pong is received, check if we have any ping requests waiting for
        this pong response. If the remote endpoint skipped any earlier pings,
        then we wake up those skipped pings, too.

        This function is async even though it never awaits, because the other
        event handlers are async, too, and event dispatch would be more
        complicated if some handlers were sync.

        :param event:
        '''
        payload = bytes(event.payload)
        try:
            ping_event = self._pings[payload]
        except KeyError:
            # We received a pong that doesn't match any in-flight pongs. Nothing
            # we can do with it, so ignore it.
            return
        while self._pings:
            key, ping_event = self._pings.popitem(False)
            skipped = ' [skipped] ' if payload != key else ' '
            logger.debug('%s pong%s%r', self, skipped, key)
            ping_event.set()
            if payload == key:
                break

    async def _reader_task(self) -> None:
        ''' A background task that reads network data and generates events. '''
        handlers = {
            AcceptConnection: self._handle_accept_connection_event,
            BytesMessage: self._handle_message_event,
            CloseConnection: self._handle_close_connection_event,
            Ping: self._handle_ping_event,
            Pong: self._handle_pong_event,
            RejectConnection: self._handle_reject_connection_event,
            RejectData: self._handle_reject_data_event,
            Request: self._handle_request_event,
            TextMessage: self._handle_message_event,
        }

        # Clients need to initiate the opening handshake.
        if self._initial_request:
            try:
                await self._send(self._initial_request)
            except ConnectionClosed:
                self._reader_running = False

        async with self._send_channel:
            while self._reader_running:
                # Process events.
                for event in self._wsproto.events():
                    event_type = type(event)
                    try:
                        handler = handlers[event_type]
                        logger.debug('%s received event: %s', self,
                            event_type)
                        # Type checkers don't understand looking up type in handlers.
                        # If we wanted to fix, best I can figure is we'd need a huge
                        # if-else or case block for every type individually.
                        await handler(event)  # type: ignore[operator]
                    except KeyError:
                        logger.warning('%s received unknown event type: "%s"', self,
                            event_type)
                    except ConnectionClosed:
                        self._reader_running = False
                        break

                # Get network data.
                try:
                    data = await self._stream.receive_some(self._receive_buffer_size)
                except (trio.BrokenResourceError, trio.ClosedResourceError):
                    await self._abort_web_socket()
                    break
                if len(data) == 0:
                    logger.debug('%s received zero bytes (connection closed)',
                        self)
                    # If TCP closed before WebSocket, then record it as an abnormal
                    # closure.
                    if self._wsproto.state != ConnectionState.CLOSED:
                        await self._abort_web_socket()
                    break
                logger.debug('%s received %d bytes', self, len(data))
                if self._wsproto.state != ConnectionState.CLOSED:
                    try:
                        self._wsproto.receive_data(data)
                    except wsproto.utilities.RemoteProtocolError as err:
                        logger.debug('%s remote protocol error: %s', self, err)
                        if err.event_hint:
                            await self._send(err.event_hint)
                        await self._close_stream()

        logger.debug('%s reader task finished', self)

    async def _send(self, event: wsproto.events.Event) -> None:
        '''
        Send an event to the remote WebSocket.

        The reader task and one or more writers might try to send messages at
        the same time, so this method uses an internal lock to serialize
        requests to send data.

        :param wsproto.events.Event event:
        '''
        data = self._wsproto.send(event)
        async with self._stream_lock:
            logger.debug('%s sending %d bytes', self, len(data))
            try:
                await self._stream.send_all(data)
            except (trio.BrokenResourceError, trio.ClosedResourceError):
                await self._abort_web_socket()
                assert self._close_reason is not None
                raise ConnectionClosed(self._close_reason) from None


class Endpoint:
    ''' Represents a connection endpoint. '''
    def __init__(self, address: str | int, port: int, is_ssl: bool) -> None:
        #: IP address :class:`ipaddress.ip_address`
        self.address = ip_address(address)
        #: TCP port
        self.port = port
        #: Whether SSL is in use
        self.is_ssl = is_ssl

    @property
    def url(self) -> str:
        ''' Return a URL representation of a TCP endpoint, e.g.
        ``ws://127.0.0.1:80``. '''
        scheme = 'wss' if self.is_ssl else 'ws'
        if (self.port == 80 and not self.is_ssl) or \
           (self.port == 443 and self.is_ssl):
            port_str = ''
        else:
            port_str = ':' + str(self.port)
        if self.address.version == 4:
            return f'{scheme}://{self.address}{port_str}'
        return f'{scheme}://[{self.address}]{port_str}'

    def __repr__(self) -> str:
        ''' Return endpoint info as string. '''
        return f'Endpoint(address="{self.address}", port={self.port}, is_ssl={self.is_ssl})'


class WebSocketServer:
    '''
    WebSocket server.

    The server class handles incoming connections on one or more ``Listener``
    objects. For each incoming connection, it creates a ``WebSocketConnection``
    instance and starts some background tasks,
    '''

    def __init__(
        self,
        handler: Callable[[WebSocketRequest], Awaitable[None]],
        listeners: Sequence[trio.SSLListener[trio.SocketStream] | trio.SocketListener],
        *,
        handler_nursery: trio.Nursery | None = None,
        message_queue_size: int = MESSAGE_QUEUE_SIZE,
        max_message_size: int = MAX_MESSAGE_SIZE,
        receive_buffer_size: Union[None, int] = RECEIVE_BYTES,
        connect_timeout: float = CONN_TIMEOUT,
        disconnect_timeout: float = CONN_TIMEOUT,
    ) -> None:
        '''
        Constructor.

        Note that if ``host`` is ``None`` and ``port`` is zero, then you may get
        multiple listeners that have _different port numbers!_ See the
        ``listeners`` property.

        :param handler: the async function called with a :class:`WebSocketRequest`
            on each new connection.  The call will be made
            once the HTTP handshake completes, which notably implies that the
            connection's `path` property will be valid.
        :param listeners: The WebSocket will be served on each of the listeners.
        :param handler_nursery: An optional nursery to spawn connection tasks
            inside of. If ``None``, then a new nursery will be created
            internally.
        :param Optional[int] receive_buffer_size: The buffer size we use to
            receive messages internally. None to let trio choose. Defaults
            to 4 KiB.
        :param float connect_timeout: The number of seconds to wait for a client
            to finish connection handshake before timing out.
        :param float disconnect_timeout: The number of seconds to wait for a client
            to finish the closing handshake before timing out.
        '''
        if len(listeners) == 0:
            raise ValueError('Listeners must contain at least one item.')
        self._handler = handler
        self._handler_nursery = handler_nursery
        self._listeners = listeners
        self._message_queue_size = message_queue_size
        self._max_message_size = max_message_size
        self._receive_buffer_size = receive_buffer_size
        self._connect_timeout = connect_timeout
        self._disconnect_timeout = disconnect_timeout

    @property
    def port(self) -> int:
        """Returns the requested or kernel-assigned port number.

        In the case of kernel-assigned port (requested with port=0 in the
        constructor), the assigned port will be reflected after calling
        starting the `listen` task.  (Technically, once listen reaches the
        "started" state.)

        This property only works if you have a single listener, and that
        listener must be socket-based.
        """
        if len(self._listeners) > 1:
            raise RuntimeError('Cannot get port because this server has'
                ' more than 1 listener.')
        listener = self.listeners[0]
        try:
            return listener.port  # type: ignore[union-attr]
        except AttributeError:
            raise RuntimeError(f'This socket does not have a port: {repr(listener)}') from None

    @property
    def listeners(self) -> list[Endpoint | str]:
        '''
        Return a list of listener metadata. Each TCP listener is represented as
        an ``Endpoint`` instance. Other listener types are represented by their
        ``repr()``.

        :returns: Listeners
        :rtype list[Endpoint or str]:
        '''
        listeners: list[Endpoint | str] = []
        for listener in self._listeners:
            socket, is_ssl = None, False
            if isinstance(listener, trio.SocketListener):
                socket = listener.socket
            elif isinstance(listener, trio.SSLListener):
                internal_listener = listener.transport_listener
                assert isinstance(internal_listener, trio.SocketListener)
                socket = internal_listener.socket
                is_ssl = True
            if socket:
                sockname = socket.getsockname()
                listeners.append(Endpoint(sockname[0], sockname[1], is_ssl))
            else:
                listeners.append(repr(listener))
        return listeners

    # Type ignore is because type checker does not think NoReturn is
    # real for Trio 0.25.1 (current version used in requirements file as
    # of writing). Not a problem for newer versions however, which is
    # why we have unused-ignore as well.
    async def run(  # type: ignore[misc,unused-ignore]
        self,
        *,
        task_status: trio.TaskStatus[WebSocketServer] = trio.TASK_STATUS_IGNORED,
    ) -> NoReturn:
        '''
        Start serving incoming connections requests.

        This method supports the Trio nursery start protocol: ``server = await
        nursery.start(server.run, …)``. It will block until the server is
        accepting connections and then return a :class:`WebSocketServer` object.

        :param task_status: Part of the Trio nursery start protocol.
        :returns: This method never returns unless cancelled.
        '''
        async with trio.open_nursery() as nursery:
            serve_listeners = partial(trio.serve_listeners,
                self._handle_connection, list(self._listeners),
                handler_nursery=self._handler_nursery)
            await nursery.start(serve_listeners)
            logger.debug('Listening on %s',
                ','.join([str(l) for l in self.listeners]))
            task_status.started(self)
            await trio.sleep_forever()

    async def _handle_connection(self, stream: trio.abc.Stream) -> None:
        '''
        Handle an incoming connection by spawning a connection background task
        and a handler task inside a new nursery.

        :param stream:
        :type stream: trio.abc.Stream
        '''
        async with trio.open_nursery() as nursery:
            connection = WebSocketConnection(stream,
                WSConnection(ConnectionType.SERVER),
                message_queue_size=self._message_queue_size,
                max_message_size=self._max_message_size,
                receive_buffer_size=self._receive_buffer_size)
            nursery.start_soon(connection._reader_task)
            with trio.move_on_after(self._connect_timeout) as connect_scope:
                request = await connection._get_request()
            if connect_scope.cancelled_caught:
                nursery.cancel_scope.cancel()
                await stream.aclose()
                return
            try:
                await self._handler(request)
            finally:
                with trio.move_on_after(self._disconnect_timeout):
                    # aclose() will shut down the reader task even if it's
                    # cancelled:
                    await connection.aclose()
