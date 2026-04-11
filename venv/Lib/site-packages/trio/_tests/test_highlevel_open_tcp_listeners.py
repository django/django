from __future__ import annotations

import errno
import socket as stdlib_socket
import sys
from socket import AddressFamily, SocketKind
from typing import TYPE_CHECKING, cast, overload

import attrs
import pytest

import trio
from trio import (
    SocketListener,
    open_tcp_listeners,
    open_tcp_stream,
    serve_tcp,
)
from trio.abc import HostnameResolver, SendStream, SocketFactory
from trio.testing import open_stream_to_socket_listener

from .. import socket as tsocket
from .._core._tests.tutil import binds_ipv6, slow

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup

if TYPE_CHECKING:
    from collections.abc import Sequence

    from typing_extensions import Buffer

    from trio._socket import AddressFormat


async def test_open_tcp_listeners_basic() -> None:
    listeners = await open_tcp_listeners(0)
    assert isinstance(listeners, list)
    for obj in listeners:
        assert isinstance(obj, SocketListener)
        # Binds to wildcard address by default
        assert obj.socket.family in [tsocket.AF_INET, tsocket.AF_INET6]
        assert obj.socket.getsockname()[0] in ["0.0.0.0", "::"]

    listener = listeners[0]
    # Make sure the backlog is at least 2
    c1 = await open_stream_to_socket_listener(listener)
    c2 = await open_stream_to_socket_listener(listener)

    s1 = await listener.accept()
    s2 = await listener.accept()

    # Note that we don't know which client stream is connected to which server
    # stream
    await s1.send_all(b"x")
    await s2.send_all(b"x")
    assert await c1.receive_some(1) == b"x"
    assert await c2.receive_some(1) == b"x"

    for resource in [c1, c2, s1, s2, *listeners]:
        await resource.aclose()


async def test_open_tcp_listeners_specific_port_specific_host() -> None:
    # Pick a port
    sock = tsocket.socket()
    await sock.bind(("127.0.0.1", 0))
    host, port = sock.getsockname()
    sock.close()

    (listener,) = await open_tcp_listeners(port, host=host)
    async with listener:
        assert listener.socket.getsockname() == (host, port)


@binds_ipv6
@slow
async def test_open_tcp_listeners_ipv6_v6only() -> None:
    # Check IPV6_V6ONLY is working properly
    (ipv6_listener,) = await open_tcp_listeners(0, host="::1")
    async with ipv6_listener:
        _, port, *_ = ipv6_listener.socket.getsockname()

        with pytest.raises(
            OSError,
            match=r"(Error|all attempts to) connect(ing)* to (\(')*127\.0\.0\.1(', |:)\d+(\): Connection refused| failed)$",
        ):
            # Windows retries failed connections so this takes seconds
            # (and that's why this is marked @slow)
            await open_tcp_stream("127.0.0.1", port)


async def test_open_tcp_listeners_rebind() -> None:
    (l1,) = await open_tcp_listeners(0, host="127.0.0.1")
    sockaddr1 = l1.socket.getsockname()

    # Plain old rebinding while it's still there should fail, even if we have
    # SO_REUSEADDR set
    with stdlib_socket.socket() as probe:
        probe.setsockopt(stdlib_socket.SOL_SOCKET, stdlib_socket.SO_REUSEADDR, 1)
        with pytest.raises(
            OSError,
            match=r"(Address (already )?in use|An attempt was made to access a socket in a way forbidden by its access permissions)$",
        ):
            probe.bind(sockaddr1)

    # Now use the first listener to set up some connections in various states,
    # and make sure that they don't create any obstacle to rebinding a second
    # listener after the first one is closed.
    c_established = await open_stream_to_socket_listener(l1)
    s_established = await l1.accept()

    c_time_wait = await open_stream_to_socket_listener(l1)
    s_time_wait = await l1.accept()
    # Server-initiated close leaves socket in TIME_WAIT
    await s_time_wait.aclose()

    await l1.aclose()
    (l2,) = await open_tcp_listeners(sockaddr1[1], host="127.0.0.1")
    sockaddr2 = l2.socket.getsockname()

    assert sockaddr1 == sockaddr2
    assert s_established.socket.getsockname() == sockaddr2
    assert c_time_wait.socket.getpeername() == sockaddr2

    for resource in [
        l1,
        l2,
        c_established,
        s_established,
        c_time_wait,
        s_time_wait,
    ]:
        await resource.aclose()


class FakeOSError(OSError):
    pass


@attrs.define(slots=False)
class FakeSocket(tsocket.SocketType):
    _family: AddressFamily = attrs.field(converter=AddressFamily)
    _type: SocketKind = attrs.field(converter=SocketKind)
    _proto: int

    closed: bool = False
    poison_listen: bool = False
    backlog: int | None = None

    @property
    def type(self) -> SocketKind:
        return self._type

    @property
    def family(self) -> AddressFamily:
        return self._family

    @property
    def proto(self) -> int:  # pragma: no cover
        return self._proto

    @overload
    def getsockopt(self, /, level: int, optname: int) -> int: ...

    @overload
    def getsockopt(self, /, level: int, optname: int, buflen: int) -> bytes: ...

    def getsockopt(
        self,
        /,
        level: int,
        optname: int,
        buflen: int | None = None,
    ) -> int | bytes:
        if (level, optname) == (tsocket.SOL_SOCKET, tsocket.SO_ACCEPTCONN):
            return True
        raise AssertionError()  # pragma: no cover

    @overload
    def setsockopt(self, /, level: int, optname: int, value: int | Buffer) -> None: ...

    @overload
    def setsockopt(
        self,
        /,
        level: int,
        optname: int,
        value: None,
        optlen: int,
    ) -> None: ...

    def setsockopt(
        self,
        /,
        level: int,
        optname: int,
        value: int | Buffer | None,
        optlen: int | None = None,
    ) -> None:
        pass

    async def bind(self, address: AddressFormat) -> None:
        pass

    def listen(self, /, backlog: int = min(stdlib_socket.SOMAXCONN, 128)) -> None:
        assert self.backlog is None
        assert backlog is not None
        self.backlog = backlog
        if self.poison_listen:
            raise FakeOSError("whoops")

    def close(self) -> None:
        self.closed = True


@attrs.define(slots=False)
class FakeSocketFactory(SocketFactory):
    poison_after: int
    sockets: list[tsocket.SocketType] = attrs.Factory(list)
    raise_on_family: dict[AddressFamily, int] = attrs.Factory(dict)  # family => errno

    def socket(
        self,
        family: AddressFamily | int | None = None,
        type_: SocketKind | int | None = None,
        proto: int = 0,
    ) -> tsocket.SocketType:
        assert family is not None
        assert type_ is not None
        if isinstance(family, int) and not isinstance(family, AddressFamily):
            family = AddressFamily(family)  # pragma: no cover
        if family in self.raise_on_family:
            raise OSError(self.raise_on_family[family], "nope")
        sock = FakeSocket(family, type_, proto)
        self.poison_after -= 1
        if self.poison_after == 0:
            sock.poison_listen = True
        self.sockets.append(sock)
        return sock


@attrs.define(slots=False)
class FakeHostnameResolver(HostnameResolver):
    family_addr_pairs: Sequence[tuple[AddressFamily, str]]

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
        assert isinstance(port, int)
        return [
            (family, tsocket.SOCK_STREAM, 0, "", (addr, port))
            for family, addr in self.family_addr_pairs
        ]

    async def getnameinfo(
        self,
        sockaddr: tuple[str, int] | tuple[str, int, int, int],
        flags: int,
    ) -> tuple[str, str]:
        raise NotImplementedError()


async def test_open_tcp_listeners_multiple_host_cleanup_on_error() -> None:
    # If we were trying to bind to multiple hosts and one of them failed, they
    # call get cleaned up before returning
    fsf = FakeSocketFactory(3)
    tsocket.set_custom_socket_factory(fsf)
    tsocket.set_custom_hostname_resolver(
        FakeHostnameResolver(
            [
                (tsocket.AF_INET, "1.1.1.1"),
                (tsocket.AF_INET, "2.2.2.2"),
                (tsocket.AF_INET, "3.3.3.3"),
            ],
        ),
    )

    with pytest.raises(FakeOSError):
        await open_tcp_listeners(80, host="example.org")

    assert len(fsf.sockets) == 3
    for sock in fsf.sockets:
        # property only exists on FakeSocket
        assert sock.closed  # type: ignore[attr-defined]


async def test_open_tcp_listeners_port_checking() -> None:
    for host in ["127.0.0.1", None]:
        with pytest.raises(TypeError):
            await open_tcp_listeners(None, host=host)  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            await open_tcp_listeners(b"80", host=host)  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            await open_tcp_listeners("http", host=host)  # type: ignore[arg-type]


async def test_serve_tcp() -> None:
    async def handler(stream: SendStream) -> None:
        await stream.send_all(b"x")

    async with trio.open_nursery() as nursery:
        # nursery.start is incorrectly typed, awaiting #2773
        value = await nursery.start(serve_tcp, handler, 0)
        assert isinstance(value, list)
        listeners = cast("list[SocketListener]", value)
        stream = await open_stream_to_socket_listener(listeners[0])
        async with stream:
            assert await stream.receive_some(1) == b"x"
            nursery.cancel_scope.cancel()


@pytest.mark.parametrize(
    "try_families",
    [{tsocket.AF_INET}, {tsocket.AF_INET6}, {tsocket.AF_INET, tsocket.AF_INET6}],
)
@pytest.mark.parametrize(
    "fail_families",
    [{tsocket.AF_INET}, {tsocket.AF_INET6}, {tsocket.AF_INET, tsocket.AF_INET6}],
)
async def test_open_tcp_listeners_some_address_families_unavailable(
    try_families: set[AddressFamily],
    fail_families: set[AddressFamily],
) -> None:
    fsf = FakeSocketFactory(
        10,
        raise_on_family=dict.fromkeys(fail_families, errno.EAFNOSUPPORT),
    )
    tsocket.set_custom_socket_factory(fsf)
    tsocket.set_custom_hostname_resolver(
        FakeHostnameResolver([(family, "foo") for family in try_families]),
    )

    should_succeed = try_families - fail_families

    if not should_succeed:
        with pytest.raises(OSError, match="This system doesn't support") as exc_info:
            await open_tcp_listeners(80, host="example.org")

        # open_listeners always creates an exceptiongroup with the
        # unsupported address families, regardless of the value of
        # strict_exception_groups or number of unsupported families.
        assert isinstance(exc_info.value.__cause__, BaseExceptionGroup)
        for subexc in exc_info.value.__cause__.exceptions:
            assert "nope" in str(subexc)
    else:
        listeners = await open_tcp_listeners(80)
        for listener in listeners:
            should_succeed.remove(listener.socket.family)
        assert not should_succeed


async def test_open_tcp_listeners_socket_fails_not_afnosupport() -> None:
    fsf = FakeSocketFactory(
        10,
        raise_on_family={
            tsocket.AF_INET: errno.EAFNOSUPPORT,
            tsocket.AF_INET6: errno.EINVAL,
        },
    )
    tsocket.set_custom_socket_factory(fsf)
    tsocket.set_custom_hostname_resolver(
        FakeHostnameResolver([(tsocket.AF_INET, "foo"), (tsocket.AF_INET6, "bar")]),
    )

    with pytest.raises(OSError, match="nope") as exc_info:
        await open_tcp_listeners(80, host="example.org")
    assert exc_info.value.errno == errno.EINVAL
    assert exc_info.value.__cause__ is None
    assert "nope" in str(exc_info.value)


# We used to have an elaborate test that opened a real TCP listening socket
# and then tried to measure its backlog by making connections to it. And most
# of the time, it worked. But no matter what we tried, it was always fragile,
# because it had to do things like use timeouts to guess when the listening
# queue was full, sometimes the CI hosts go into SYN-cookie mode (where there
# effectively is no backlog), sometimes the host might not be enough resources
# to give us the full requested backlog... it was a mess. So now we just check
# that the backlog argument is passed through correctly.
async def test_open_tcp_listeners_backlog() -> None:
    fsf = FakeSocketFactory(99)
    tsocket.set_custom_socket_factory(fsf)
    for given, expected in [
        (None, 0xFFFF),
        (99999999, 0xFFFF),
        (10, 10),
        (1, 1),
    ]:
        listeners = await open_tcp_listeners(0, backlog=given)
        assert listeners
        for listener in listeners:
            # `backlog` only exists on FakeSocket
            assert listener.socket.backlog == expected  # type: ignore[attr-defined]


async def test_open_tcp_listeners_backlog_float_error() -> None:
    fsf = FakeSocketFactory(99)
    tsocket.set_custom_socket_factory(fsf)
    for should_fail in (0.0, 2.18, 3.15, 9.75):
        with pytest.raises(
            TypeError,
            match=f"backlog must be an int or None, not {should_fail!r}",
        ):
            await open_tcp_listeners(0, backlog=should_fail)  # type: ignore[arg-type]
