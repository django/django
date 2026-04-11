from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, NoReturn, cast

import attrs
import pytest

import trio
from trio.socket import AF_INET, IPPROTO_TCP, SOCK_STREAM

from .._highlevel_ssl_helpers import (
    open_ssl_over_tcp_listeners,
    open_ssl_over_tcp_stream,
    serve_ssl_over_tcp,
)

# using noqa because linters don't understand how pytest fixtures work.
from .test_ssl import SERVER_CTX, client_ctx  # noqa: F401

if TYPE_CHECKING:
    from socket import AddressFamily, SocketKind
    from ssl import SSLContext

    from trio.abc import Stream

    from .._highlevel_socket import SocketListener
    from .._ssl import SSLListener


async def echo_handler(stream: Stream) -> None:
    async with stream:
        try:
            while True:
                data = await stream.receive_some(10000)
                if not data:
                    break
                await stream.send_all(data)
        except trio.BrokenResourceError:
            pass


# Resolver that always returns the given sockaddr, no matter what host/port
# you ask for.
@attrs.define(slots=False)
class FakeHostnameResolver(trio.abc.HostnameResolver):
    sockaddr: tuple[str, int] | tuple[str, int, int, int] | tuple[int, bytes]

    async def getaddrinfo(
        self,
        host: bytes | None,
        port: bytes | str | int | None,
        family: int = 0,
        type: int = 0,
        proto: int = 0,
        flags: int = 0,
    ) -> list[
        tuple[
            AddressFamily,
            SocketKind,
            int,
            str,
            tuple[str, int] | tuple[str, int, int, int] | tuple[int, bytes],
        ]
    ]:
        return [(AF_INET, SOCK_STREAM, IPPROTO_TCP, "", self.sockaddr)]

    async def getnameinfo(
        self,
        sockaddr: tuple[str, int] | tuple[str, int, int, int],
        flags: int,
    ) -> NoReturn:  # pragma: no cover
        raise NotImplementedError


# This uses serve_ssl_over_tcp, which uses open_ssl_over_tcp_listeners...
# using noqa because linters don't understand how pytest fixtures work.
async def test_open_ssl_over_tcp_stream_and_everything_else(
    client_ctx: SSLContext,  # noqa: F811 # linters doesn't understand fixture
) -> None:
    async with trio.open_nursery() as nursery:
        # TODO: this function wraps an SSLListener around a SocketListener, this is illegal
        # according to current type hints, and probably for good reason. But there should
        # maybe be a different wrapper class/function that could be used instead?
        value = await nursery.start(
            partial(
                serve_ssl_over_tcp,
                echo_handler,
                0,
                SERVER_CTX,
                host="127.0.0.1",
            ),
        )
        assert isinstance(value, list)
        res = cast("list[SSLListener[SocketListener]]", value)  # type: ignore[type-var]
        (listener,) = res
        async with listener:
            # listener.transport_listener is of type Listener[Stream]
            tp_listener: SocketListener = listener.transport_listener  # type: ignore[assignment]

            sockaddr = tp_listener.socket.getsockname()
            hostname_resolver = FakeHostnameResolver(sockaddr)
            trio.socket.set_custom_hostname_resolver(hostname_resolver)

            # We don't have the right trust set up
            # (checks that ssl_context=None is doing some validation)
            stream = await open_ssl_over_tcp_stream("trio-test-1.example.org", 80)
            async with stream:
                with pytest.raises(trio.BrokenResourceError):
                    await stream.do_handshake()

            # We have the trust but not the hostname
            # (checks custom ssl_context + hostname checking)
            stream = await open_ssl_over_tcp_stream(
                "xyzzy.example.org",
                80,
                ssl_context=client_ctx,
            )
            async with stream:
                with pytest.raises(trio.BrokenResourceError):
                    await stream.do_handshake()

            # This one should work!
            stream = await open_ssl_over_tcp_stream(
                "trio-test-1.example.org",
                80,
                ssl_context=client_ctx,
            )
            async with stream:
                assert isinstance(stream, trio.SSLStream)
                assert stream.server_hostname == "trio-test-1.example.org"
                await stream.send_all(b"x")
                assert await stream.receive_some(1) == b"x"

            # Check https_compatible settings are being passed through
            assert not stream._https_compatible
            stream = await open_ssl_over_tcp_stream(
                "trio-test-1.example.org",
                80,
                ssl_context=client_ctx,
                https_compatible=True,
                # also, smoke test happy_eyeballs_delay
                happy_eyeballs_delay=1,
            )
            async with stream:
                assert stream._https_compatible

            # Stop the echo server
            nursery.cancel_scope.cancel()


async def test_open_ssl_over_tcp_listeners() -> None:
    (listener,) = await open_ssl_over_tcp_listeners(0, SERVER_CTX, host="127.0.0.1")
    async with listener:
        assert isinstance(listener, trio.SSLListener)
        tl = listener.transport_listener
        assert isinstance(tl, trio.SocketListener)
        assert tl.socket.getsockname()[0] == "127.0.0.1"

        assert not listener._https_compatible

    (listener,) = await open_ssl_over_tcp_listeners(
        0,
        SERVER_CTX,
        host="127.0.0.1",
        https_compatible=True,
    )
    async with listener:
        assert listener._https_compatible
