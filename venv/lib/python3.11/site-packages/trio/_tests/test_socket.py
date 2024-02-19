from __future__ import annotations

import errno
import inspect
import os
import socket as stdlib_socket
import sys
import tempfile
from socket import AddressFamily, SocketKind
from typing import TYPE_CHECKING, Any, Callable, List, Tuple, Union

import attr
import pytest

from .. import _core, socket as tsocket
from .._core._tests.tutil import binds_ipv6, creates_ipv6
from .._socket import _NUMERIC_ONLY, SocketType, _SocketType, _try_sync
from ..testing import assert_checkpoints, wait_all_tasks_blocked

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

    from .._highlevel_socket import SocketStream

    GaiTuple: TypeAlias = Tuple[
        AddressFamily,
        SocketKind,
        int,
        str,
        Union[Tuple[str, int], Tuple[str, int, int, int]],
    ]
    GetAddrInfoResponse: TypeAlias = List[GaiTuple]
else:
    GaiTuple: object
    GetAddrInfoResponse = object

################################################################
# utils
################################################################


class MonkeypatchedGAI:
    def __init__(self, orig_getaddrinfo: Callable[..., GetAddrInfoResponse]) -> None:
        self._orig_getaddrinfo = orig_getaddrinfo
        self._responses: dict[tuple[Any, ...], GetAddrInfoResponse | str] = {}
        self.record: list[tuple[Any, ...]] = []

    # get a normalized getaddrinfo argument tuple
    def _frozenbind(self, *args: Any, **kwargs: Any) -> tuple[Any, ...]:
        sig = inspect.signature(self._orig_getaddrinfo)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        frozenbound = bound.args
        assert not bound.kwargs
        return frozenbound

    def set(
        self, response: GetAddrInfoResponse | str, *args: Any, **kwargs: Any
    ) -> None:
        self._responses[self._frozenbind(*args, **kwargs)] = response

    def getaddrinfo(self, *args: Any, **kwargs: Any) -> GetAddrInfoResponse | str:
        bound = self._frozenbind(*args, **kwargs)
        self.record.append(bound)
        if bound in self._responses:
            return self._responses[bound]
        elif bound[-1] & stdlib_socket.AI_NUMERICHOST:
            return self._orig_getaddrinfo(*args, **kwargs)
        else:
            raise RuntimeError(f"gai called with unexpected arguments {bound}")


@pytest.fixture
def monkeygai(monkeypatch: pytest.MonkeyPatch) -> MonkeypatchedGAI:
    controller = MonkeypatchedGAI(stdlib_socket.getaddrinfo)
    monkeypatch.setattr(stdlib_socket, "getaddrinfo", controller.getaddrinfo)
    return controller


async def test__try_sync() -> None:
    with assert_checkpoints():
        async with _try_sync():
            pass

    with assert_checkpoints():
        with pytest.raises(KeyError):
            async with _try_sync():
                raise KeyError

    async with _try_sync():
        raise BlockingIOError

    def _is_ValueError(exc: BaseException) -> bool:
        return isinstance(exc, ValueError)

    async with _try_sync(_is_ValueError):
        raise ValueError

    with assert_checkpoints():
        with pytest.raises(BlockingIOError):
            async with _try_sync(_is_ValueError):
                raise BlockingIOError


################################################################
# basic re-exports
################################################################


def test_socket_has_some_reexports() -> None:
    assert tsocket.SOL_SOCKET == stdlib_socket.SOL_SOCKET
    assert tsocket.TCP_NODELAY == stdlib_socket.TCP_NODELAY
    assert tsocket.gaierror == stdlib_socket.gaierror
    assert tsocket.ntohs == stdlib_socket.ntohs


################################################################
# name resolution
################################################################


async def test_getaddrinfo(monkeygai: MonkeypatchedGAI) -> None:
    def check(got: GetAddrInfoResponse, expected: GetAddrInfoResponse) -> None:
        # win32 returns 0 for the proto field
        # musl and glibc have inconsistent handling of the canonical name
        # field (https://github.com/python-trio/trio/issues/1499)
        # Neither field gets used much and there isn't much opportunity for us
        # to mess them up, so we don't bother checking them here
        def interesting_fields(
            gai_tup: GaiTuple,
        ) -> tuple[
            AddressFamily,
            SocketKind,
            tuple[str, int] | tuple[str, int, int] | tuple[str, int, int, int],
        ]:
            # (family, type, proto, canonname, sockaddr)
            family, type, proto, canonname, sockaddr = gai_tup
            return (family, type, sockaddr)

        def filtered(
            gai_list: GetAddrInfoResponse,
        ) -> list[
            tuple[
                AddressFamily,
                SocketKind,
                tuple[str, int] | tuple[str, int, int] | tuple[str, int, int, int],
            ]
        ]:
            return [interesting_fields(gai_tup) for gai_tup in gai_list]

        assert filtered(got) == filtered(expected)

    # Simple non-blocking non-error cases, ipv4 and ipv6:
    with assert_checkpoints():
        res = await tsocket.getaddrinfo("127.0.0.1", "12345", type=tsocket.SOCK_STREAM)

    check(
        res,
        [
            (
                tsocket.AF_INET,  # 127.0.0.1 is ipv4
                tsocket.SOCK_STREAM,
                tsocket.IPPROTO_TCP,
                "",
                ("127.0.0.1", 12345),
            ),
        ],
    )

    with assert_checkpoints():
        res = await tsocket.getaddrinfo("::1", "12345", type=tsocket.SOCK_DGRAM)
    check(
        res,
        [
            (
                tsocket.AF_INET6,
                tsocket.SOCK_DGRAM,
                tsocket.IPPROTO_UDP,
                "",
                ("::1", 12345, 0, 0),
            ),
        ],
    )

    monkeygai.set("x", b"host", "port", family=0, type=0, proto=0, flags=0)
    with assert_checkpoints():
        res = await tsocket.getaddrinfo("host", "port")
    assert res == "x"
    assert monkeygai.record[-1] == (b"host", "port", 0, 0, 0, 0)

    # check raising an error from a non-blocking getaddrinfo
    with assert_checkpoints():
        with pytest.raises(tsocket.gaierror) as excinfo:
            await tsocket.getaddrinfo("::1", "12345", type=-1)
    # Linux + glibc, Windows
    expected_errnos = {tsocket.EAI_SOCKTYPE}
    # Linux + musl
    expected_errnos.add(tsocket.EAI_SERVICE)
    # macOS
    if hasattr(tsocket, "EAI_BADHINTS"):
        expected_errnos.add(tsocket.EAI_BADHINTS)
    assert excinfo.value.errno in expected_errnos

    # check raising an error from a blocking getaddrinfo (exploits the fact
    # that monkeygai raises if it gets a non-numeric request it hasn't been
    # given an answer for)
    with assert_checkpoints():
        with pytest.raises(RuntimeError):
            await tsocket.getaddrinfo("asdf", "12345")


async def test_getnameinfo() -> None:
    # Trivial test:
    ni_numeric = stdlib_socket.NI_NUMERICHOST | stdlib_socket.NI_NUMERICSERV
    with assert_checkpoints():
        got = await tsocket.getnameinfo(("127.0.0.1", 1234), ni_numeric)
    assert got == ("127.0.0.1", "1234")

    # getnameinfo requires a numeric address as input:
    with assert_checkpoints():
        with pytest.raises(tsocket.gaierror):
            await tsocket.getnameinfo(("google.com", 80), 0)

    with assert_checkpoints():
        with pytest.raises(tsocket.gaierror):
            await tsocket.getnameinfo(("localhost", 80), 0)

    # Blocking call to get expected values:
    host, service = stdlib_socket.getnameinfo(("127.0.0.1", 80), 0)

    # Some working calls:
    got = await tsocket.getnameinfo(("127.0.0.1", 80), 0)
    assert got == (host, service)

    got = await tsocket.getnameinfo(("127.0.0.1", 80), tsocket.NI_NUMERICHOST)
    assert got == ("127.0.0.1", service)

    got = await tsocket.getnameinfo(("127.0.0.1", 80), tsocket.NI_NUMERICSERV)
    assert got == (host, "80")


################################################################
# constructors
################################################################


async def test_from_stdlib_socket() -> None:
    sa, sb = stdlib_socket.socketpair()
    assert not isinstance(sa, tsocket.SocketType)
    with sa, sb:
        ta = tsocket.from_stdlib_socket(sa)
        assert isinstance(ta, tsocket.SocketType)
        assert sa.fileno() == ta.fileno()
        await ta.send(b"x")
        assert sb.recv(1) == b"x"

    # rejects other types
    with pytest.raises(TypeError):
        tsocket.from_stdlib_socket(1)  # type: ignore[arg-type]

    class MySocket(stdlib_socket.socket):
        pass

    with MySocket() as mysock:
        with pytest.raises(TypeError):
            tsocket.from_stdlib_socket(mysock)


async def test_from_fd() -> None:
    sa, sb = stdlib_socket.socketpair()
    ta = tsocket.fromfd(sa.fileno(), sa.family, sa.type, sa.proto)
    with sa, sb, ta:
        assert ta.fileno() != sa.fileno()
        await ta.send(b"x")
        assert sb.recv(3) == b"x"


async def test_socketpair_simple() -> None:
    async def child(sock: SocketType) -> None:
        print("sending hello")
        await sock.send(b"h")
        assert await sock.recv(1) == b"h"

    a, b = tsocket.socketpair()
    with a, b:
        async with _core.open_nursery() as nursery:
            nursery.start_soon(child, a)
            nursery.start_soon(child, b)


@pytest.mark.skipif(not hasattr(tsocket, "fromshare"), reason="windows only")
async def test_fromshare() -> None:
    if TYPE_CHECKING and sys.platform != "win32":  # pragma: no cover
        return
    a, b = tsocket.socketpair()
    with a, b:
        # share with ourselves
        shared = a.share(os.getpid())
        a2 = tsocket.fromshare(shared)
        with a2:
            assert a.fileno() != a2.fileno()
            await a2.send(b"x")
            assert await b.recv(1) == b"x"


async def test_socket() -> None:
    with tsocket.socket() as s:
        assert isinstance(s, tsocket.SocketType)
        assert s.family == tsocket.AF_INET


@creates_ipv6
async def test_socket_v6() -> None:
    with tsocket.socket(tsocket.AF_INET6, tsocket.SOCK_DGRAM) as s:
        assert isinstance(s, tsocket.SocketType)
        assert s.family == tsocket.AF_INET6


@pytest.mark.skipif(sys.platform != "linux", reason="linux only")
async def test_sniff_sockopts() -> None:
    from socket import AF_INET, AF_INET6, SOCK_DGRAM, SOCK_STREAM

    # generate the combinations of families/types we're testing:
    sockets = []
    for family in [AF_INET, AF_INET6]:
        for type in [SOCK_DGRAM, SOCK_STREAM]:
            sockets.append(stdlib_socket.socket(family, type))
    for socket in sockets:
        # regular Trio socket constructor
        tsocket_socket = tsocket.socket(fileno=socket.fileno())
        # check family / type for correctness:
        assert tsocket_socket.family == socket.family
        assert tsocket_socket.type == socket.type
        tsocket_socket.detach()

        # fromfd constructor
        tsocket_from_fd = tsocket.fromfd(socket.fileno(), AF_INET, SOCK_STREAM)
        # check family / type for correctness:
        assert tsocket_from_fd.family == socket.family
        assert tsocket_from_fd.type == socket.type
        tsocket_from_fd.close()

        socket.close()


################################################################
# _SocketType
################################################################


async def test_SocketType_basics() -> None:
    sock = tsocket.socket()
    with sock as cm_enter_value:
        assert cm_enter_value is sock
        assert isinstance(sock.fileno(), int)
        assert not sock.get_inheritable()
        sock.set_inheritable(True)
        assert sock.get_inheritable()

        sock.setsockopt(tsocket.IPPROTO_TCP, tsocket.TCP_NODELAY, False)
        assert not sock.getsockopt(tsocket.IPPROTO_TCP, tsocket.TCP_NODELAY)
        sock.setsockopt(tsocket.IPPROTO_TCP, tsocket.TCP_NODELAY, True)
        assert sock.getsockopt(tsocket.IPPROTO_TCP, tsocket.TCP_NODELAY)
    # closed sockets have fileno() == -1
    assert sock.fileno() == -1

    # smoke test
    repr(sock)

    # detach
    with tsocket.socket() as sock:
        fd = sock.fileno()
        assert sock.detach() == fd
        assert sock.fileno() == -1

    # close
    sock = tsocket.socket()
    assert sock.fileno() >= 0
    sock.close()
    assert sock.fileno() == -1

    # share was tested above together with fromshare

    # check __dir__
    assert "family" in dir(sock)
    assert "recv" in dir(sock)
    assert "setsockopt" in dir(sock)

    # our __getattr__ handles unknown names
    with pytest.raises(AttributeError):
        sock.asdf  # type: ignore[attr-defined]  # noqa: B018

    # type family proto
    stdlib_sock = stdlib_socket.socket()
    sock = tsocket.from_stdlib_socket(stdlib_sock)
    assert sock.type == stdlib_sock.type
    assert sock.family == stdlib_sock.family
    assert sock.proto == stdlib_sock.proto
    sock.close()


async def test_SocketType_setsockopt() -> None:
    sock = tsocket.socket()
    with sock as _:
        setsockopt_tests(sock)


def setsockopt_tests(sock: SocketType | SocketStream) -> None:
    """Extract these out, to be reused for SocketStream also."""
    # specifying optlen. Not supported on pypy, and I couldn't find
    # valid calls on darwin or win32.
    if hasattr(tsocket, "SO_BINDTODEVICE"):
        sock.setsockopt(tsocket.SOL_SOCKET, tsocket.SO_BINDTODEVICE, None, 0)

    # specifying value
    sock.setsockopt(tsocket.IPPROTO_TCP, tsocket.TCP_NODELAY, False)

    # specifying both
    with pytest.raises(TypeError, match="invalid value for argument 'value'"):
        sock.setsockopt(tsocket.IPPROTO_TCP, tsocket.TCP_NODELAY, False, 5)  # type: ignore[call-overload]

    # specifying neither
    with pytest.raises(TypeError, match="invalid value for argument 'value'"):
        sock.setsockopt(tsocket.IPPROTO_TCP, tsocket.TCP_NODELAY, None)  # type: ignore[call-overload]


async def test_SocketType_dup() -> None:
    a, b = tsocket.socketpair()
    with a, b:
        a2 = a.dup()
        with a2:
            assert isinstance(a2, tsocket.SocketType)
            assert a2.fileno() != a.fileno()
            a.close()
            await a2.send(b"x")
            assert await b.recv(1) == b"x"


async def test_SocketType_shutdown() -> None:
    a, b = tsocket.socketpair()
    with a, b:
        await a.send(b"x")
        assert await b.recv(1) == b"x"
        assert not a.did_shutdown_SHUT_WR
        assert not b.did_shutdown_SHUT_WR
        a.shutdown(tsocket.SHUT_WR)
        assert a.did_shutdown_SHUT_WR
        assert not b.did_shutdown_SHUT_WR
        assert await b.recv(1) == b""
        await b.send(b"y")
        assert await a.recv(1) == b"y"

    a, b = tsocket.socketpair()
    with a, b:
        assert not a.did_shutdown_SHUT_WR
        a.shutdown(tsocket.SHUT_RD)
        assert not a.did_shutdown_SHUT_WR

    a, b = tsocket.socketpair()
    with a, b:
        assert not a.did_shutdown_SHUT_WR
        a.shutdown(tsocket.SHUT_RDWR)
        assert a.did_shutdown_SHUT_WR


@pytest.mark.parametrize(
    ("address", "socket_type"),
    [
        ("127.0.0.1", tsocket.AF_INET),
        pytest.param("::1", tsocket.AF_INET6, marks=binds_ipv6),
    ],
)
async def test_SocketType_simple_server(
    address: str, socket_type: AddressFamily
) -> None:
    # listen, bind, accept, connect, getpeername, getsockname
    listener = tsocket.socket(socket_type)
    client = tsocket.socket(socket_type)
    with listener, client:
        await listener.bind((address, 0))
        listener.listen(20)
        addr = listener.getsockname()[:2]
        async with _core.open_nursery() as nursery:
            nursery.start_soon(client.connect, addr)
            server, client_addr = await listener.accept()
        with server:
            assert client_addr == server.getpeername() == client.getsockname()
            await server.send(b"x")
            assert await client.recv(1) == b"x"


async def test_SocketType_is_readable() -> None:
    a, b = tsocket.socketpair()
    with a, b:
        assert not a.is_readable()
        await b.send(b"x")
        await _core.wait_readable(a)
        assert a.is_readable()
        assert await a.recv(1) == b"x"
        assert not a.is_readable()


# On some macOS systems, getaddrinfo likes to return V4-mapped addresses even
# when we *don't* pass AI_V4MAPPED.
# https://github.com/python-trio/trio/issues/580
def gai_without_v4mapped_is_buggy() -> bool:  # pragma: no cover
    try:
        stdlib_socket.getaddrinfo("1.2.3.4", 0, family=stdlib_socket.AF_INET6)
    except stdlib_socket.gaierror:
        return False
    else:
        return True


@attr.s
class Addresses:
    bind_all: str = attr.ib()
    localhost: str = attr.ib()
    arbitrary: str = attr.ib()
    broadcast: str = attr.ib()


# Direct thorough tests of the implicit resolver helpers
@pytest.mark.parametrize(
    ("socket_type", "addrs"),
    [
        (
            tsocket.AF_INET,
            Addresses(
                bind_all="0.0.0.0",
                localhost="127.0.0.1",
                arbitrary="1.2.3.4",
                broadcast="255.255.255.255",
            ),
        ),
        pytest.param(
            tsocket.AF_INET6,
            Addresses(
                bind_all="::",
                localhost="::1",
                arbitrary="1::2",
                broadcast="::ffff:255.255.255.255",
            ),
            marks=creates_ipv6,
        ),
    ],
)
async def test_SocketType_resolve(socket_type: AddressFamily, addrs: Addresses) -> None:
    v6 = socket_type == tsocket.AF_INET6

    def pad(addr: tuple[str | int, ...]) -> tuple[str | int, ...]:
        if v6:
            while len(addr) < 4:
                addr += (0,)
        return addr

    def assert_eq(
        actual: tuple[str | int, ...], expected: tuple[str | int, ...]
    ) -> None:
        assert pad(expected) == pad(actual)

    with tsocket.socket(family=socket_type) as sock:
        # testing internal functionality, so we check it against the internal type
        assert isinstance(sock, _SocketType)

        # For some reason the stdlib special-cases "" to pass NULL to
        # getaddrinfo. They also error out on None, but whatever, None is much
        # more consistent, so we accept it too.
        # TODO: this implies that we can send host=None, but what does that imply for the return value, and other stuff?
        for null in [None, ""]:
            got = await sock._resolve_address_nocp((null, 80), local=True)
            assert not isinstance(got, (str, bytes))
            assert_eq(got, (addrs.bind_all, 80))
            got = await sock._resolve_address_nocp((null, 80), local=False)
            assert not isinstance(got, (str, bytes))
            assert_eq(got, (addrs.localhost, 80))

        # AI_PASSIVE only affects the wildcard address, so for everything else
        # local=True/local=False should work the same:
        for local in [False, True]:

            async def res(
                args: tuple[str, int]
                | tuple[str, int, int]
                | tuple[str, int, int, int]
                | tuple[str, str]
                | tuple[str, str, int]
                | tuple[str, str, int, int]
            ) -> Any:
                return await sock._resolve_address_nocp(
                    args,
                    local=local,  # noqa: B023  # local is not bound in function definition
                )

            assert_eq(await res((addrs.arbitrary, "http")), (addrs.arbitrary, 80))
            if v6:
                # Check handling of different length ipv6 address tuples
                assert_eq(await res(("1::2", 80)), ("1::2", 80, 0, 0))
                assert_eq(await res(("1::2", 80, 0)), ("1::2", 80, 0, 0))
                assert_eq(await res(("1::2", 80, 0, 0)), ("1::2", 80, 0, 0))
                # Non-zero flowinfo/scopeid get passed through
                assert_eq(await res(("1::2", 80, 1)), ("1::2", 80, 1, 0))
                assert_eq(await res(("1::2", 80, 1, 2)), ("1::2", 80, 1, 2))

                # And again with a string port, as a trick to avoid the
                # already-resolved address fastpath and make sure we call
                # getaddrinfo
                assert_eq(await res(("1::2", "80")), ("1::2", 80, 0, 0))
                assert_eq(await res(("1::2", "80", 0)), ("1::2", 80, 0, 0))
                assert_eq(await res(("1::2", "80", 0, 0)), ("1::2", 80, 0, 0))
                assert_eq(await res(("1::2", "80", 1)), ("1::2", 80, 1, 0))
                assert_eq(await res(("1::2", "80", 1, 2)), ("1::2", 80, 1, 2))

                # V4 mapped addresses resolved if V6ONLY is False
                sock.setsockopt(tsocket.IPPROTO_IPV6, tsocket.IPV6_V6ONLY, False)
                assert_eq(await res(("1.2.3.4", "http")), ("::ffff:1.2.3.4", 80))

            # Check the <broadcast> special case, because why not
            assert_eq(await res(("<broadcast>", 123)), (addrs.broadcast, 123))

            # But not if it's true (at least on systems where getaddrinfo works
            # correctly)
            if v6 and not gai_without_v4mapped_is_buggy():
                sock.setsockopt(tsocket.IPPROTO_IPV6, tsocket.IPV6_V6ONLY, True)
                with pytest.raises(tsocket.gaierror) as excinfo:
                    await res(("1.2.3.4", 80))
                # Windows, macOS
                expected_errnos = {tsocket.EAI_NONAME}
                # Linux
                if hasattr(tsocket, "EAI_ADDRFAMILY"):
                    expected_errnos.add(tsocket.EAI_ADDRFAMILY)
                assert excinfo.value.errno in expected_errnos

            # A family where we know nothing about the addresses, so should just
            # pass them through. This should work on Linux, which is enough to
            # smoke test the basic functionality...
            try:
                netlink_sock = tsocket.socket(
                    family=tsocket.AF_NETLINK, type=tsocket.SOCK_DGRAM
                )
            except (AttributeError, OSError):
                pass
            else:
                assert isinstance(netlink_sock, _SocketType)
                assert (
                    await netlink_sock._resolve_address_nocp("asdf", local=local)
                    == "asdf"
                )
                netlink_sock.close()

            address = r"^address should be a \(host, port(, \[flowinfo, \[scopeid\]\])*\) tuple$"
            with pytest.raises(ValueError, match=address):
                await res("1.2.3.4")  # type: ignore[arg-type]
            with pytest.raises(ValueError, match=address):
                await res(("1.2.3.4",))  # type: ignore[arg-type]
            with pytest.raises(  # noqa: PT012
                ValueError,
                match=address,
            ):
                if v6:
                    await res(("1.2.3.4", 80, 0, 0, 0))  # type: ignore[arg-type]
                else:
                    # I guess in theory there could be enough overloads that this could error?
                    await res(("1.2.3.4", 80, 0, 0))


async def test_SocketType_unresolved_names() -> None:
    with tsocket.socket() as sock:
        await sock.bind(("localhost", 0))
        assert sock.getsockname()[0] == "127.0.0.1"
        sock.listen(10)

        with tsocket.socket() as sock2:
            await sock2.connect(("localhost", sock.getsockname()[1]))
            assert sock2.getpeername() == sock.getsockname()

    # check gaierror propagates out
    with tsocket.socket() as sock:
        with pytest.raises(tsocket.gaierror):
            # definitely not a valid request
            await sock.bind(("1.2:3", -1))


# This tests all the complicated paths through _nonblocking_helper, using recv
# as a stand-in for all the methods that use _nonblocking_helper.
async def test_SocketType_non_blocking_paths() -> None:
    a, b = stdlib_socket.socketpair()
    with a, b:
        ta = tsocket.from_stdlib_socket(a)
        b.setblocking(False)

        # cancel before even calling
        b.send(b"1")
        with _core.CancelScope() as cscope:
            cscope.cancel()
            with assert_checkpoints():
                with pytest.raises(_core.Cancelled):
                    await ta.recv(10)
        # immediate success (also checks that the previous attempt didn't
        # actually read anything)
        with assert_checkpoints():
            assert await ta.recv(10) == b"1"
        # immediate failure
        with assert_checkpoints():
            with pytest.raises(TypeError):
                await ta.recv("haha")  # type: ignore[arg-type]
        # block then succeed

        async def do_successful_blocking_recv() -> None:
            with assert_checkpoints():
                assert await ta.recv(10) == b"2"

        async with _core.open_nursery() as nursery:
            nursery.start_soon(do_successful_blocking_recv)
            await wait_all_tasks_blocked()
            b.send(b"2")
        # block then cancelled

        async def do_cancelled_blocking_recv() -> None:
            with assert_checkpoints():
                with pytest.raises(_core.Cancelled):
                    await ta.recv(10)

        async with _core.open_nursery() as nursery:
            nursery.start_soon(do_cancelled_blocking_recv)
            await wait_all_tasks_blocked()
            nursery.cancel_scope.cancel()
        # Okay, here's the trickiest one: we want to exercise the path where
        # the task is signaled to wake, goes to recv, but then the recv fails,
        # so it has to go back to sleep and try again. Strategy: have two
        # tasks waiting on two sockets (to work around the rule against having
        # two tasks waiting on the same socket), wake them both up at the same
        # time, and whichever one runs first "steals" the data from the
        # other:
        tb = tsocket.from_stdlib_socket(b)

        async def t1() -> None:
            with assert_checkpoints():
                assert await ta.recv(1) == b"a"
            with assert_checkpoints():
                assert await tb.recv(1) == b"b"

        async def t2() -> None:
            with assert_checkpoints():
                assert await tb.recv(1) == b"b"
            with assert_checkpoints():
                assert await ta.recv(1) == b"a"

        async with _core.open_nursery() as nursery:
            nursery.start_soon(t1)
            nursery.start_soon(t2)
            await wait_all_tasks_blocked()
            a.send(b"b")
            b.send(b"a")
            await wait_all_tasks_blocked()
            a.send(b"b")
            b.send(b"a")


# This tests the complicated paths through connect
async def test_SocketType_connect_paths() -> None:
    with tsocket.socket() as sock:
        with pytest.raises(
            ValueError,
            match=r"^address should be a \(host, port(, \[flowinfo, \[scopeid\]\])*\) tuple$",
        ):
            # Should be a tuple
            await sock.connect("localhost")

    # cancelled before we start
    with tsocket.socket() as sock:
        with _core.CancelScope() as cancel_scope:
            cancel_scope.cancel()
            with pytest.raises(_core.Cancelled):
                await sock.connect(("127.0.0.1", 80))

    # Cancelled in between the connect() call and the connect completing
    with _core.CancelScope() as cancel_scope:
        with tsocket.socket() as sock, tsocket.socket() as listener:
            await listener.bind(("127.0.0.1", 0))
            listener.listen()

            # Swap in our weird subclass under the trio.socket._SocketType's
            # nose -- and then swap it back out again before we hit
            # wait_socket_writable, which insists on a real socket.
            class CancelSocket(stdlib_socket.socket):
                def connect(self, *args: Any, **kwargs: Any) -> None:
                    # accessing private method only available in _SocketType
                    assert isinstance(sock, _SocketType)

                    cancel_scope.cancel()
                    sock._sock = stdlib_socket.fromfd(
                        self.detach(), self.family, self.type
                    )
                    sock._sock.connect(*args, **kwargs)
                    # If connect *doesn't* raise, then pretend it did
                    raise BlockingIOError  # pragma: no cover

            # accessing private method only available in _SocketType
            assert isinstance(sock, _SocketType)
            sock._sock.close()
            sock._sock = CancelSocket()

            with assert_checkpoints():
                with pytest.raises(_core.Cancelled):
                    await sock.connect(listener.getsockname())
            assert sock.fileno() == -1

    # Failed connect (hopefully after raising BlockingIOError)
    with tsocket.socket() as sock:
        with pytest.raises(
            OSError,
            match=r"^\[\w+ \d+\] Error connecting to \('127\.0\.0\.\d', \d+\): (Connection refused|Unknown error)$",
        ):
            # TCP port 2 is not assigned. Pretty sure nothing will be
            # listening there. (We used to bind a port and then *not* call
            # listen() to ensure nothing was listening there, but it turns
            # out on macOS if you do this it takes 30 seconds for the
            # connect to fail. Really. Also if you use a non-routable
            # address. This way fails instantly though. As long as nothing
            # is listening on port 2.)
            await sock.connect(("127.0.0.1", 2))


# Fix issue #1810
async def test_address_in_socket_error() -> None:
    address = "127.0.0.1"
    with tsocket.socket() as sock:
        with pytest.raises(
            OSError,
            match=rf"^\[\w+ \d+\] Error connecting to \({address!r}, 2\): (Connection refused|Unknown error)$",
        ):
            await sock.connect((address, 2))


async def test_resolve_address_exception_in_connect_closes_socket() -> None:
    # Here we are testing issue 247, any cancellation will leave the socket closed
    with _core.CancelScope() as cancel_scope:
        with tsocket.socket() as sock:

            async def _resolve_address_nocp(
                self: Any, *args: Any, **kwargs: Any
            ) -> None:
                cancel_scope.cancel()
                await _core.checkpoint()

            assert isinstance(sock, _SocketType)
            sock._resolve_address_nocp = _resolve_address_nocp  # type: ignore[method-assign, assignment]
            with assert_checkpoints():
                with pytest.raises(_core.Cancelled):
                    await sock.connect("")
            assert sock.fileno() == -1


async def test_send_recv_variants() -> None:
    a, b = tsocket.socketpair()
    with a, b:
        # recv, including with flags
        assert await a.send(b"x") == 1
        assert await b.recv(10, tsocket.MSG_PEEK) == b"x"
        assert await b.recv(10) == b"x"

        # recv_into
        await a.send(b"x")
        buf = bytearray(10)
        await b.recv_into(buf)
        assert buf == b"x" + b"\x00" * 9

        if hasattr(a, "sendmsg"):
            assert await a.sendmsg([b"xxx"], []) == 3
            assert await b.recv(10) == b"xxx"

    a = tsocket.socket(type=tsocket.SOCK_DGRAM)
    b = tsocket.socket(type=tsocket.SOCK_DGRAM)
    with a, b:
        await a.bind(("127.0.0.1", 0))
        await b.bind(("127.0.0.1", 0))

        targets = [b.getsockname(), ("localhost", b.getsockname()[1])]

        # recvfrom + sendto, with and without names
        for target in targets:
            assert await a.sendto(b"xxx", target) == 3
            (data, addr) = await b.recvfrom(10)
            assert data == b"xxx"
            assert addr == a.getsockname()

        # sendto + flags
        #
        # I can't find any flags that send() accepts... on Linux at least
        # passing MSG_MORE to send_some on a connected UDP socket seems to
        # just be ignored.
        #
        # But there's no MSG_MORE on Windows or macOS. I guess send_some flags
        # are really not very useful, but at least this tests them a bit.
        if hasattr(tsocket, "MSG_MORE"):
            await a.sendto(b"xxx", tsocket.MSG_MORE, b.getsockname())
            await a.sendto(b"yyy", tsocket.MSG_MORE, b.getsockname())
            await a.sendto(b"zzz", b.getsockname())
            (data, addr) = await b.recvfrom(10)
            assert data == b"xxxyyyzzz"
            assert addr == a.getsockname()

        # recvfrom_into
        assert await a.sendto(b"xxx", b.getsockname()) == 3
        buf = bytearray(10)
        (nbytes, addr) = await b.recvfrom_into(buf)
        assert nbytes == 3
        assert buf == b"xxx" + b"\x00" * 7
        assert addr == a.getsockname()

        if hasattr(b, "recvmsg"):
            assert await a.sendto(b"xxx", b.getsockname()) == 3
            (data, ancdata, msg_flags, addr) = await b.recvmsg(10)
            assert data == b"xxx"
            assert ancdata == []
            assert msg_flags == 0
            assert addr == a.getsockname()

        if hasattr(b, "recvmsg_into"):
            assert await a.sendto(b"xyzw", b.getsockname()) == 4
            buf1 = bytearray(2)
            buf2 = bytearray(3)
            ret = await b.recvmsg_into([buf1, buf2])
            (nbytes, ancdata, msg_flags, addr) = ret
            assert nbytes == 4
            assert buf1 == b"xy"
            assert buf2 == b"zw" + b"\x00"
            assert ancdata == []
            assert msg_flags == 0
            assert addr == a.getsockname()

        if hasattr(a, "sendmsg"):
            for target in targets:
                assert await a.sendmsg([b"x", b"yz"], [], 0, target) == 3
                assert await b.recvfrom(10) == (b"xyz", a.getsockname())

    a = tsocket.socket(type=tsocket.SOCK_DGRAM)
    b = tsocket.socket(type=tsocket.SOCK_DGRAM)
    with a, b:
        await b.bind(("127.0.0.1", 0))
        await a.connect(b.getsockname())
        # send on a connected udp socket; each call creates a separate
        # datagram
        await a.send(b"xxx")
        await a.send(b"yyy")
        assert await b.recv(10) == b"xxx"
        assert await b.recv(10) == b"yyy"


async def test_idna(monkeygai: MonkeypatchedGAI) -> None:
    # This is the encoding for "faß.de", which uses one of the characters that
    # IDNA 2003 handles incorrectly:
    monkeygai.set("ok faß.de", b"xn--fa-hia.de", 80)
    monkeygai.set("ok ::1", "::1", 80, flags=_NUMERIC_ONLY)
    monkeygai.set("ok ::1", b"::1", 80, flags=_NUMERIC_ONLY)
    # Some things that should not reach the underlying socket.getaddrinfo:
    monkeygai.set("bad", "fass.de", 80)
    # We always call socket.getaddrinfo with bytes objects:
    monkeygai.set("bad", "xn--fa-hia.de", 80)

    assert await tsocket.getaddrinfo("::1", 80) == "ok ::1"
    assert await tsocket.getaddrinfo(b"::1", 80) == "ok ::1"
    assert await tsocket.getaddrinfo("faß.de", 80) == "ok faß.de"
    assert await tsocket.getaddrinfo("xn--fa-hia.de", 80) == "ok faß.de"
    assert await tsocket.getaddrinfo(b"xn--fa-hia.de", 80) == "ok faß.de"


async def test_getprotobyname() -> None:
    # These are the constants used in IP header fields, so the numeric values
    # had *better* be stable across systems...
    assert await tsocket.getprotobyname("udp") == 17
    assert await tsocket.getprotobyname("tcp") == 6


async def test_custom_hostname_resolver(monkeygai: MonkeypatchedGAI) -> None:
    # This intentionally breaks the signatures used in HostnameResolver
    class CustomResolver:
        async def getaddrinfo(
            self, host: str, port: str, family: int, type: int, proto: int, flags: int
        ) -> tuple[str, str, str, int, int, int, int]:
            return ("custom_gai", host, port, family, type, proto, flags)

        async def getnameinfo(
            self, sockaddr: tuple[str, int] | tuple[str, int, int, int], flags: int
        ) -> tuple[str, tuple[str, int] | tuple[str, int, int, int], int]:
            return ("custom_gni", sockaddr, flags)

    cr = CustomResolver()

    assert tsocket.set_custom_hostname_resolver(cr) is None  # type: ignore[arg-type]

    # Check that the arguments are all getting passed through.
    # We have to use valid calls to avoid making the underlying system
    # getaddrinfo cranky when it's used for NUMERIC checks.
    for vals in [
        (tsocket.AF_INET, 0, 0, 0),
        (0, tsocket.SOCK_STREAM, 0, 0),
        (0, 0, tsocket.IPPROTO_TCP, 0),
        (0, 0, 0, tsocket.AI_CANONNAME),
    ]:
        assert await tsocket.getaddrinfo("localhost", "foo", *vals) == (
            "custom_gai",
            b"localhost",
            "foo",
            *vals,
        )

    # IDNA encoding is handled before calling the special object
    got = await tsocket.getaddrinfo("föö", "foo")
    expected = ("custom_gai", b"xn--f-1gaa", "foo", 0, 0, 0, 0)
    assert got == expected

    assert await tsocket.getnameinfo("a", 0) == (  # type: ignore[arg-type]
        "custom_gni",
        "a",
        0,
    )

    # We can set it back to None
    assert tsocket.set_custom_hostname_resolver(None) is cr

    # And now Trio switches back to calling socket.getaddrinfo (specifically
    # our monkeypatched version of socket.getaddrinfo)
    monkeygai.set("x", b"host", "port", family=0, type=0, proto=0, flags=0)
    assert await tsocket.getaddrinfo("host", "port") == "x"


async def test_custom_socket_factory() -> None:
    class CustomSocketFactory:
        def socket(
            self, family: AddressFamily, type: SocketKind, proto: int
        ) -> tuple[str, AddressFamily, SocketKind, int]:
            return ("hi", family, type, proto)

    csf = CustomSocketFactory()

    assert tsocket.set_custom_socket_factory(csf) is None  # type: ignore[arg-type]

    assert tsocket.socket() == ("hi", tsocket.AF_INET, tsocket.SOCK_STREAM, 0)
    assert tsocket.socket(1, 2, 3) == ("hi", 1, 2, 3)

    # socket with fileno= doesn't call our custom method
    fd = stdlib_socket.socket().detach()
    wrapped = tsocket.socket(fileno=fd)
    assert hasattr(wrapped, "bind")
    wrapped.close()

    # Likewise for socketpair
    a, b = tsocket.socketpair()
    with a, b:
        assert hasattr(a, "bind")
        assert hasattr(b, "bind")

    assert tsocket.set_custom_socket_factory(None) is csf


async def test_SocketType_is_abstract() -> None:
    with pytest.raises(TypeError):
        tsocket.SocketType()


@pytest.mark.skipif(not hasattr(tsocket, "AF_UNIX"), reason="no unix domain sockets")
async def test_unix_domain_socket() -> None:
    # Bind has a special branch to use a thread, since it has to do filesystem
    # traversal. Maybe connect should too? Not sure.

    async def check_AF_UNIX(path: str | bytes) -> None:
        with tsocket.socket(family=tsocket.AF_UNIX) as lsock:
            await lsock.bind(path)
            lsock.listen(10)
            with tsocket.socket(family=tsocket.AF_UNIX) as csock:
                await csock.connect(path)
                ssock, _ = await lsock.accept()
                with ssock:
                    await csock.send(b"x")
                    assert await ssock.recv(1) == b"x"

    # Can't use tmpdir fixture, because we can exceed the maximum AF_UNIX path
    # length on macOS.
    with tempfile.TemporaryDirectory() as tmpdir:
        path = f"{tmpdir}/sock"
        await check_AF_UNIX(path)

    try:
        cookie = os.urandom(20).hex().encode("ascii")
        await check_AF_UNIX(b"\x00trio-test-" + cookie)
    except FileNotFoundError:
        # macOS doesn't support abstract filenames with the leading NUL byte
        pass


async def test_interrupted_by_close() -> None:
    a_stdlib, b_stdlib = stdlib_socket.socketpair()
    with a_stdlib, b_stdlib:
        a_stdlib.setblocking(False)

        data = b"x" * 99999

        try:
            while True:
                a_stdlib.send(data)
        except BlockingIOError:
            pass

        a = tsocket.from_stdlib_socket(a_stdlib)

        async def sender() -> None:
            with pytest.raises(_core.ClosedResourceError):
                await a.send(data)

        async def receiver() -> None:
            with pytest.raises(_core.ClosedResourceError):
                await a.recv(1)

        async with _core.open_nursery() as nursery:
            nursery.start_soon(sender)
            nursery.start_soon(receiver)
            await wait_all_tasks_blocked()
            a.close()


async def test_many_sockets() -> None:
    total = 5000  # Must be more than MAX_AFD_GROUP_SIZE
    sockets = []
    # Open at most <total> socket pairs
    for opened in range(0, total, 2):
        try:
            a, b = stdlib_socket.socketpair()
        except OSError as exc:  # pragma: no cover
            # Semi-expecting following errors (sockets are files):
            # EMFILE: "Too many open files" (reached kernel cap)
            # ENFILE: "File table overflow" (beyond kernel cap)
            assert exc.errno in (errno.EMFILE, errno.ENFILE)  # noqa: PT017
            print(f"Unable to open more than {opened} sockets.")
            # Stop opening any more sockets if too many are open
            break
        sockets += [a, b]
    async with _core.open_nursery() as nursery:
        for socket in sockets:
            nursery.start_soon(_core.wait_readable, socket)
        await _core.wait_all_tasks_blocked()
        nursery.cancel_scope.cancel()
    for socket in sockets:
        socket.close()
