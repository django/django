# Copyright 2014-2021 The aiosmtpd Developers
# SPDX-License-Identifier: Apache-2.0

import asyncio
import errno
import os
import ssl
import threading
import time
from abc import ABCMeta, abstractmethod
from contextlib import ExitStack
from pathlib import Path
from socket import AF_INET6, SOCK_STREAM, create_connection, has_ipv6
from socket import socket as makesock
from socket import timeout as socket_timeout

try:
    from socket import AF_UNIX
except ImportError:  # pragma: on-not-win32
    AF_UNIX = None  # type: ignore[assignment]
from typing import Any, Awaitable, Dict, Literal, Optional, Union
from warnings import warn

from public import public

from aiosmtpd.smtp import SMTP

DEFAULT_READY_TIMEOUT: float = 5.0


@public
class IP6_IS:
    # Apparently errno.E* constants adapts to the OS, so on Windows they will
    # automatically use the WSAE* constants
    NO = {errno.EADDRNOTAVAIL, errno.EAFNOSUPPORT}
    YES = {errno.EADDRINUSE}


def _has_ipv6() -> bool:
    # Helper function to assist in mocking
    return has_ipv6


@public
def get_localhost() -> Literal["::1", "127.0.0.1"]:
    """Returns numeric address to localhost depending on IPv6 availability"""
    # Ref:
    #  - https://github.com/urllib3/urllib3/pull/611#issuecomment-100954017
    #  - https://github.com/python/cpython/blob/ :
    #    - v3.6.13/Lib/test/support/__init__.py#L745-L758
    #    - v3.9.1/Lib/test/support/socket_helper.py#L124-L137
    if not _has_ipv6():
        # socket.has_ipv6 only tells us of current Python's IPv6 support, not the
        # system's. But if the current Python does not support IPv6, it's pointless to
        # explore further.
        return "127.0.0.1"
    try:
        with makesock(AF_INET6, SOCK_STREAM) as sock:
            sock.bind(("::1", 0))
        # If we reach this point, that means we can successfully bind ::1 (on random
        # unused port), so IPv6 is definitely supported
        return "::1"
    except OSError as e:
        if e.errno in IP6_IS.NO:
            return "127.0.0.1"
        if e.errno in IP6_IS.YES:
            # We shouldn't ever get these errors, but if we do, that means IPv6 is
            # supported
            return "::1"
        # Other kinds of errors MUST be raised so we can inspect
        raise


def _server_to_client_ssl_ctx(server_ctx: ssl.SSLContext) -> ssl.SSLContext:
    """
    Given an SSLContext object with TLS_SERVER_PROTOCOL return a client
    context that can connect to the server.
    """
    client_ctx = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
    client_ctx.options = server_ctx.options
    client_ctx.check_hostname = False
    # We do not verify the ssl cert for the server here simply because this
    # is a local connection to poke at the server for it to do its lazy
    # initialization sequence. The only purpose of this client context
    # is to make a connection to the *local* server created using the same
    # code. That is also the reason why we disable cert verification below
    # and the flake8 check for the same.
    client_ctx.verify_mode = ssl.CERT_NONE    # noqa: DUO122
    return client_ctx


class _FakeServer(asyncio.StreamReaderProtocol):
    """
    Returned by _factory_invoker() in lieu of an SMTP instance in case
    factory() failed to instantiate an SMTP instance.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop):
        # Imitate what SMTP does
        super().__init__(
            asyncio.StreamReader(loop=loop),
            client_connected_cb=self._cb_client_connected,
            loop=loop,
        )

    def _cb_client_connected(
            self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        pass


@public
class BaseController(metaclass=ABCMeta):
    smtpd = None
    server: Optional[asyncio.AbstractServer] = None
    server_coro: Optional[Awaitable[asyncio.AbstractServer]] = None
    _thread_exception: Optional[Exception] = None

    def __init__(
        self,
        handler: Any,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        *,
        ssl_context: Optional[ssl.SSLContext] = None,
        # SMTP parameters
        server_hostname: Optional[str] = None,
        **SMTP_parameters,
    ):
        self.handler = handler
        if loop is None:
            self.loop = asyncio.new_event_loop()
        else:
            self.loop = loop
        self.ssl_context = ssl_context
        self.SMTP_kwargs: Dict[str, Any] = {}
        if "server_kwargs" in SMTP_parameters:
            warn(
                "server_kwargs will be removed in version 2.0. "
                "Just specify the keyword arguments to forward to SMTP "
                "as kwargs to this __init__ method.",
                DeprecationWarning,
            )
            self.SMTP_kwargs = SMTP_parameters.pop("server_kwargs")
        self.SMTP_kwargs.update(SMTP_parameters)
        if server_hostname:
            self.SMTP_kwargs["hostname"] = server_hostname
        # Emulate previous behavior of defaulting enable_SMTPUTF8 to True
        # It actually conflicts with SMTP class's default, but the reasoning is
        # discussed in the docs.
        self.SMTP_kwargs.setdefault("enable_SMTPUTF8", True)
        #
        self._factory_invoked = threading.Event()

    def factory(self):
        """Subclasses can override this to customize the handler/server creation."""
        return SMTP(self.handler, **self.SMTP_kwargs)

    def _factory_invoker(self) -> Union[SMTP, _FakeServer]:
        """Wraps factory() to catch exceptions during instantiation"""
        try:
            self.smtpd = self.factory()
            if self.smtpd is None:
                raise RuntimeError("factory() returned None")
            return self.smtpd
        except Exception as err:
            self._thread_exception = err
            return _FakeServer(self.loop)
        finally:
            self._factory_invoked.set()

    @abstractmethod
    def _create_server(self) -> Awaitable[asyncio.AbstractServer]:
        """
        Overridden by subclasses to actually perform the async binding to the
        listener endpoint. When overridden, MUST refer the _factory_invoker() method.
        """

    def _cleanup(self):
        """Reset internal variables to prevent contamination"""
        self._thread_exception = None
        self._factory_invoked.clear()
        self.server_coro = None
        self.server = None
        self.smtpd = None

    def cancel_tasks(self, stop_loop: bool = True):
        """
        Convenience method to stop the loop and cancel all tasks.
        Use loop.call_soon_threadsafe() to invoke this.
        """
        if stop_loop:  # pragma: nobranch
            self.loop.stop()
        for task in asyncio.all_tasks(self.loop):
            # This needs to be invoked in a thread-safe way
            task.cancel()


@public
class BaseThreadedController(BaseController, metaclass=ABCMeta):
    _thread: Optional[threading.Thread] = None

    def __init__(
        self,
        handler: Any,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        *,
        ready_timeout: float = DEFAULT_READY_TIMEOUT,
        ssl_context: Optional[ssl.SSLContext] = None,
        # SMTP parameters
        server_hostname: Optional[str] = None,
        **SMTP_parameters,
    ):
        super().__init__(
            handler,
            loop,
            ssl_context=ssl_context,
            server_hostname=server_hostname,
            **SMTP_parameters,
        )
        self.ready_timeout = float(
            os.getenv("AIOSMTPD_CONTROLLER_TIMEOUT", ready_timeout)
        )

    @abstractmethod
    def _trigger_server(self):
        """
        Overridden by subclasses to trigger asyncio to actually initialize the SMTP
        class (it's lazy initialization, done only on initial connection).
        """

    def _run(self, ready_event: threading.Event) -> None:
        asyncio.set_event_loop(self.loop)
        try:
            self.server_coro = self._create_server()
            self.server = self.loop.run_until_complete(self.server_coro)
        except Exception as error:  # pragma: on-wsl
            # Usually will enter this part only if create_server() cannot bind to the
            # specified host:port.
            #
            # Somehow WSL 1.0 (Windows Subsystem for Linux) allows multiple
            # listeners on one port?!
            # That is why we add "pragma: on-wsl" there, so this block will not affect
            # coverage on WSL 1.0.
            self._thread_exception = error
            return
        self.loop.call_soon(ready_event.set)
        self.loop.run_forever()
        # We reach this point when loop is ended (by external code)
        # Perform some stoppages to ensure endpoint no longer bound.
        assert self.server is not None
        self.server.close()
        self.loop.run_until_complete(self.server.wait_closed())
        self.loop.close()
        self.server = None

    def start(self):
        """
        Start a thread and run the asyncio event loop in that thread
        """
        assert self._thread is None, "SMTP daemon already running"
        self._factory_invoked.clear()

        ready_event = threading.Event()
        self._thread = threading.Thread(target=self._run, args=(ready_event,))
        self._thread.daemon = True
        self._thread.start()
        # Wait a while until the server is responding.
        start = time.monotonic()
        if not ready_event.wait(self.ready_timeout):
            # An exception within self._run will also result in ready_event not set
            # So, we first test for that, before raising TimeoutError
            if self._thread_exception is not None:  # pragma: on-wsl
                # See comment about WSL1.0 in the _run() method
                raise self._thread_exception
            else:
                raise TimeoutError(
                    "SMTP server failed to start within allotted time. "
                    "This might happen if the system is too busy. "
                    "Try increasing the `ready_timeout` parameter."
                )
        respond_timeout = self.ready_timeout - (time.monotonic() - start)

        # Apparently create_server invokes factory() "lazily", so exceptions in
        # factory() go undetected. To trigger factory() invocation we need to open
        # a connection to the server and 'exchange' some traffic.
        try:
            self._trigger_server()
        except socket_timeout:
            # We totally don't care of timeout experienced by _testconn,
            pass
        except Exception:
            # Raise other exceptions though
            raise
        if not self._factory_invoked.wait(respond_timeout):
            raise TimeoutError(
                "SMTP server started, but not responding within allotted time. "
                "This might happen if the system is too busy. "
                "Try increasing the `ready_timeout` parameter."
            )
        if self._thread_exception is not None:
            raise self._thread_exception

        # Defensive
        if self.smtpd is None:
            raise RuntimeError("Unknown Error, failed to init SMTP server")

    def stop(self, no_assert: bool = False):
        """
        Stop the loop, the tasks in the loop, and terminate the thread as well.
        """
        assert no_assert or self._thread is not None, "SMTP daemon not running"
        self.loop.call_soon_threadsafe(self.cancel_tasks)
        if self._thread is not None:
            self._thread.join()
            self._thread = None
        self._cleanup()


@public
class BaseUnthreadedController(BaseController, metaclass=ABCMeta):
    def __init__(
        self,
        handler: Any,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        *,
        ssl_context: Optional[ssl.SSLContext] = None,
        # SMTP parameters
        server_hostname: Optional[str] = None,
        **SMTP_parameters,
    ):
        super().__init__(
            handler,
            loop,
            ssl_context=ssl_context,
            server_hostname=server_hostname,
            **SMTP_parameters,
        )
        self.ended = threading.Event()

    def begin(self):
        """
        Sets up the asyncio server task and inject it into the asyncio event loop.
        Does NOT actually start the event loop itself.
        """
        asyncio.set_event_loop(self.loop)
        self.server_coro = self._create_server()
        self.server = self.loop.run_until_complete(self.server_coro)

    async def finalize(self):
        """
        Perform orderly closing of the server listener.
        NOTE: This is an async method; await this from an async or use
        loop.create_task() (if loop is still running), or
        loop.run_until_complete() (if loop has stopped)
        """
        self.ended.clear()
        server = self.server
        assert server is not None
        server.close()
        await server.wait_closed()
        assert self.server_coro is not None
        # TODO: Where does .close() come from...?
        self.server_coro.close()  # type: ignore[attr-defined]
        self._cleanup()
        self.ended.set()

    def end(self):
        """
        Convenience method to asynchronously invoke finalize().
        Consider using loop.call_soon_threadsafe to invoke this method, especially
        if your loop is running in a different thread. You can afterwards .wait() on
        ended attribute (a threading.Event) to check for completion, if needed.
        """
        self.ended.clear()
        if self.loop.is_running():
            # TODO: Should store and await on task at some point.
            self.loop.create_task(self.finalize())  # type: ignore[unused-awaitable]
        else:
            self.loop.run_until_complete(self.finalize())


@public
class InetMixin(BaseController, metaclass=ABCMeta):
    def __init__(
        self,
        handler: Any,
        hostname: Optional[str] = None,
        port: int = 8025,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        **kwargs,
    ):
        super().__init__(
            handler,
            loop,
            **kwargs,
        )
        self._localhost = get_localhost()
        self.hostname = self._localhost if hostname is None else hostname
        self.port = port

    def _create_server(self) -> Awaitable[asyncio.AbstractServer]:
        """
        Creates a 'server task' that listens on an INET host:port.
        Does NOT actually start the protocol object itself;
        _factory_invoker() is only called upon fist connection attempt.
        """
        return self.loop.create_server(
            self._factory_invoker,
            host=self.hostname,
            port=self.port,
            ssl=self.ssl_context,
        )

    def _trigger_server(self):
        """
        Opens a socket connection to the newly launched server, wrapping in an SSL
        Context if necessary, and read some data from it to ensure that factory()
        gets invoked.
        """
        # At this point, if self.hostname is Falsy, it most likely is "" (bind to all
        # addresses). In such case, it should be safe to connect to localhost)
        hostname = self.hostname or self._localhost
        with ExitStack() as stk:
            s = stk.enter_context(create_connection((hostname, self.port), 1.0))
            if self.ssl_context:
                client_ctx = _server_to_client_ssl_ctx(self.ssl_context)
                s = stk.enter_context(client_ctx.wrap_socket(s))
            s.recv(1024)


@public
class UnixSocketMixin(BaseController, metaclass=ABCMeta):  # pragma: no-unixsock
    def __init__(
        self,
        handler: Any,
        unix_socket: Union[str, Path],
        loop: Optional[asyncio.AbstractEventLoop] = None,
        **kwargs,
    ):
        super().__init__(
            handler,
            loop,
            **kwargs,
        )
        self.unix_socket = str(unix_socket)

    def _create_server(self) -> Awaitable[asyncio.AbstractServer]:
        """
        Creates a 'server task' that listens on a Unix Socket file.
        Does NOT actually start the protocol object itself;
        _factory_invoker() is only called upon fist connection attempt.
        """
        return self.loop.create_unix_server(
            self._factory_invoker,
            path=self.unix_socket,
            ssl=self.ssl_context,
        )

    def _trigger_server(self):
        """
        Opens a socket connection to the newly launched server, wrapping in an SSL
        Context if necessary, and read some data from it to ensure that factory()
        gets invoked.
        """
        with ExitStack() as stk:
            s: makesock = stk.enter_context(makesock(AF_UNIX, SOCK_STREAM))
            s.connect(self.unix_socket)
            if self.ssl_context:
                client_ctx = _server_to_client_ssl_ctx(self.ssl_context)
                s = stk.enter_context(client_ctx.wrap_socket(s))
            s.recv(1024)


@public
class Controller(InetMixin, BaseThreadedController):
    """Provides a multithreaded controller that listens on an INET endpoint"""

    def _trigger_server(self):
        # Prevent confusion on which _trigger_server() to invoke.
        # Or so LGTM.com claimed
        InetMixin._trigger_server(self)


@public
class UnixSocketController(  # pragma: no-unixsock
    UnixSocketMixin, BaseThreadedController
):
    """Provides a multithreaded controller that listens on a Unix Socket file"""

    def _trigger_server(self):  # pragma: no-unixsock
        # Prevent confusion on which _trigger_server() to invoke.
        # Or so LGTM.com claimed
        UnixSocketMixin._trigger_server(self)


@public
class UnthreadedController(InetMixin, BaseUnthreadedController):
    """Provides an unthreaded controller that listens on an INET endpoint"""


@public
class UnixSocketUnthreadedController(  # pragma: no-unixsock
    UnixSocketMixin, BaseUnthreadedController
):
    """Provides an unthreaded controller that listens on a Unix Socket file"""
