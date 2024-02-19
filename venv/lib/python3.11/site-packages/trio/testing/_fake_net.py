# This should eventually be cleaned up and become public, but for right now I'm just
# implementing enough to test DTLS.

# TODO:
# - user-defined routers
# - TCP
# - UDP broadcast

from __future__ import annotations

import contextlib
import errno
import ipaddress
import os
import socket
import sys
from typing import (
    TYPE_CHECKING,
    Any,
    Iterable,
    NoReturn,
    TypeVar,
    Union,
    overload,
)

import attr

import trio
from trio._util import NoPublicConstructor, final

if TYPE_CHECKING:
    import builtins
    from socket import AddressFamily, SocketKind
    from types import TracebackType

    from typing_extensions import Buffer, Self, TypeAlias

IPAddress: TypeAlias = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]


def _family_for(ip: IPAddress) -> int:
    if isinstance(ip, ipaddress.IPv4Address):
        return trio.socket.AF_INET
    elif isinstance(ip, ipaddress.IPv6Address):
        return trio.socket.AF_INET6
    raise NotImplementedError("Unhandled IPAddress instance type")  # pragma: no cover


def _wildcard_ip_for(family: int) -> IPAddress:
    if family == trio.socket.AF_INET:
        return ipaddress.ip_address("0.0.0.0")
    elif family == trio.socket.AF_INET6:
        return ipaddress.ip_address("::")
    raise NotImplementedError("Unhandled ip address family")  # pragma: no cover


# not used anywhere
def _localhost_ip_for(family: int) -> IPAddress:  # pragma: no cover
    if family == trio.socket.AF_INET:
        return ipaddress.ip_address("127.0.0.1")
    elif family == trio.socket.AF_INET6:
        return ipaddress.ip_address("::1")
    raise NotImplementedError("Unhandled ip address family")


def _fake_err(code: int) -> NoReturn:
    raise OSError(code, os.strerror(code))


def _scatter(data: bytes, buffers: Iterable[Buffer]) -> int:
    written = 0
    for buf in buffers:  # pragma: no branch
        next_piece = data[written : written + memoryview(buf).nbytes]
        with memoryview(buf) as mbuf:
            mbuf[: len(next_piece)] = next_piece
        written += len(next_piece)
        if written == len(data):  # pragma: no branch
            break
    return written


T_UDPEndpoint = TypeVar("T_UDPEndpoint", bound="UDPEndpoint")


@attr.frozen
class UDPEndpoint:
    ip: IPAddress
    port: int

    def as_python_sockaddr(self) -> tuple[str, int] | tuple[str, int, int, int]:
        sockaddr: tuple[str, int] | tuple[str, int, int, int] = (
            self.ip.compressed,
            self.port,
        )
        if isinstance(self.ip, ipaddress.IPv6Address):
            sockaddr += (0, 0)  # type: ignore[assignment]
        return sockaddr

    @classmethod
    def from_python_sockaddr(
        cls: type[T_UDPEndpoint], sockaddr: tuple[str, int] | tuple[str, int, int, int]
    ) -> T_UDPEndpoint:
        ip, port = sockaddr[:2]
        return cls(ip=ipaddress.ip_address(ip), port=port)


@attr.frozen
class UDPBinding:
    local: UDPEndpoint
    # remote: UDPEndpoint # ??


@attr.frozen
class UDPPacket:
    source: UDPEndpoint
    destination: UDPEndpoint
    payload: bytes = attr.ib(repr=lambda p: p.hex())

    # not used/tested anywhere
    def reply(self, payload: bytes) -> UDPPacket:  # pragma: no cover
        return UDPPacket(
            source=self.destination, destination=self.source, payload=payload
        )


@attr.frozen
class FakeSocketFactory(trio.abc.SocketFactory):
    fake_net: FakeNet

    def socket(self, family: int, type: int, proto: int) -> FakeSocket:  # type: ignore[override]
        return FakeSocket._create(self.fake_net, family, type, proto)


@attr.frozen
class FakeHostnameResolver(trio.abc.HostnameResolver):
    fake_net: FakeNet

    async def getaddrinfo(
        self,
        host: bytes | str | None,
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
            tuple[str, int] | tuple[str, int, int, int],
        ]
    ]:
        raise NotImplementedError("FakeNet doesn't do fake DNS yet")

    async def getnameinfo(
        self, sockaddr: tuple[str, int] | tuple[str, int, int, int], flags: int
    ) -> tuple[str, str]:
        raise NotImplementedError("FakeNet doesn't do fake DNS yet")


@final
class FakeNet:
    def __init__(self) -> None:
        # When we need to pick an arbitrary unique ip address/port, use these:
        self._auto_ipv4_iter = ipaddress.IPv4Network("1.0.0.0/8").hosts()  # untested
        self._auto_ipv6_iter = ipaddress.IPv6Network("1::/16").hosts()  # untested
        self._auto_port_iter = iter(range(50000, 65535))

        self._bound: dict[UDPBinding, FakeSocket] = {}

        self.route_packet = None

    def _bind(self, binding: UDPBinding, socket: FakeSocket) -> None:
        if binding in self._bound:
            _fake_err(errno.EADDRINUSE)
        self._bound[binding] = socket

    def enable(self) -> None:
        trio.socket.set_custom_socket_factory(FakeSocketFactory(self))
        trio.socket.set_custom_hostname_resolver(FakeHostnameResolver(self))

    def send_packet(self, packet: UDPPacket) -> None:
        if self.route_packet is None:
            self.deliver_packet(packet)
        else:
            self.route_packet(packet)

    def deliver_packet(self, packet: UDPPacket) -> None:
        binding = UDPBinding(local=packet.destination)
        if binding in self._bound:
            self._bound[binding]._deliver_packet(packet)
        else:
            # No valid destination, so drop it
            pass


@final
class FakeSocket(trio.socket.SocketType, metaclass=NoPublicConstructor):
    def __init__(
        self, fake_net: FakeNet, family: AddressFamily, type: SocketKind, proto: int
    ):
        self._fake_net = fake_net

        if not family:  # pragma: no cover
            family = trio.socket.AF_INET
        if not type:  # pragma: no cover
            type = trio.socket.SOCK_STREAM

        if family not in (trio.socket.AF_INET, trio.socket.AF_INET6):
            raise NotImplementedError(f"FakeNet doesn't (yet) support family={family}")
        if type != trio.socket.SOCK_DGRAM:
            raise NotImplementedError(f"FakeNet doesn't (yet) support type={type}")

        self._family = family
        self._type = type
        self._proto = proto

        self._closed = False

        self._packet_sender, self._packet_receiver = trio.open_memory_channel[
            UDPPacket
        ](float("inf"))

        # This is the source-of-truth for what port etc. this socket is bound to
        self._binding: UDPBinding | None = None

    @property
    def type(self) -> SocketKind:
        return self._type

    @property
    def family(self) -> AddressFamily:
        return self._family

    @property
    def proto(self) -> int:
        return self._proto

    def _check_closed(self) -> None:
        if self._closed:
            _fake_err(errno.EBADF)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._binding is not None:
            del self._fake_net._bound[self._binding]
        self._packet_receiver.close()

    async def _resolve_address_nocp(
        self, address: object, *, local: bool
    ) -> tuple[str, int]:
        return await trio._socket._resolve_address_nocp(  # type: ignore[no-any-return]
            self.type,
            self.family,
            self.proto,
            address=address,
            ipv6_v6only=False,
            local=local,
        )

    def _deliver_packet(self, packet: UDPPacket) -> None:
        # sending to a closed socket -- UDP packets get dropped
        with contextlib.suppress(trio.BrokenResourceError):
            self._packet_sender.send_nowait(packet)

    ################################################################
    # Actual IO operation implementations
    ################################################################

    async def bind(self, addr: object) -> None:
        self._check_closed()
        if self._binding is not None:
            _fake_err(errno.EINVAL)
        await trio.lowlevel.checkpoint()
        ip_str, port, *_ = await self._resolve_address_nocp(addr, local=True)
        assert _ == [], "TODO: handle other values?"

        ip = ipaddress.ip_address(ip_str)
        assert _family_for(ip) == self.family
        # We convert binds to INET_ANY into binds to localhost
        if ip == ipaddress.ip_address("0.0.0.0"):
            ip = ipaddress.ip_address("127.0.0.1")
        elif ip == ipaddress.ip_address("::"):
            ip = ipaddress.ip_address("::1")
        if port == 0:
            port = next(self._fake_net._auto_port_iter)
        binding = UDPBinding(local=UDPEndpoint(ip, port))
        self._fake_net._bind(binding, self)
        self._binding = binding

    async def connect(self, peer: object) -> NoReturn:
        raise NotImplementedError("FakeNet does not (yet) support connected sockets")

    async def _sendmsg(
        self,
        buffers: Iterable[Buffer],
        ancdata: Iterable[tuple[int, int, Buffer]] = (),
        flags: int = 0,
        address: Any | None = None,
    ) -> int:
        self._check_closed()

        await trio.lowlevel.checkpoint()

        if address is not None:
            address = await self._resolve_address_nocp(address, local=False)
        if ancdata:
            raise NotImplementedError("FakeNet doesn't support ancillary data")
        if flags:
            raise NotImplementedError(f"FakeNet send flags must be 0, not {flags}")

        if address is None:
            _fake_err(errno.ENOTCONN)

        destination = UDPEndpoint.from_python_sockaddr(address)

        if self._binding is None:
            await self.bind((_wildcard_ip_for(self.family).compressed, 0))

        payload = b"".join(buffers)

        assert self._binding is not None
        packet = UDPPacket(
            source=self._binding.local,
            destination=destination,
            payload=payload,
        )

        self._fake_net.send_packet(packet)

        return len(payload)

    if sys.platform != "win32" or (
        not TYPE_CHECKING and hasattr(socket.socket, "sendmsg")
    ):
        sendmsg = _sendmsg

    async def _recvmsg_into(
        self,
        buffers: Iterable[Buffer],
        ancbufsize: int = 0,
        flags: int = 0,
    ) -> tuple[int, list[tuple[int, int, bytes]], int, Any]:
        if ancbufsize != 0:
            raise NotImplementedError("FakeNet doesn't support ancillary data")
        if flags != 0:
            raise NotImplementedError("FakeNet doesn't support any recv flags")
        if self._binding is None:
            # I messed this up a few times when writing tests ... but it also never happens
            # in any of the existing tests, so maybe it could be intentional...
            raise NotImplementedError(
                "The code will most likely hang if you try to receive on a fakesocket "
                "without a binding. If that is not the case, or you explicitly want to "
                "test that, remove this warning."
            )

        self._check_closed()

        ancdata: list[tuple[int, int, bytes]] = []
        msg_flags = 0

        packet = await self._packet_receiver.receive()
        address = packet.source.as_python_sockaddr()
        written = _scatter(packet.payload, buffers)
        if written < len(packet.payload):
            msg_flags |= trio.socket.MSG_TRUNC
        return written, ancdata, msg_flags, address

    if sys.platform != "win32" or (
        not TYPE_CHECKING and hasattr(socket.socket, "sendmsg")
    ):
        recvmsg_into = _recvmsg_into

    ################################################################
    # Simple state query stuff
    ################################################################

    def getsockname(self) -> tuple[str, int] | tuple[str, int, int, int]:
        self._check_closed()
        if self._binding is not None:
            return self._binding.local.as_python_sockaddr()
        elif self.family == trio.socket.AF_INET:
            return ("0.0.0.0", 0)
        else:
            assert self.family == trio.socket.AF_INET6
            return ("::", 0)

    # TODO: This method is not tested, and seems to make incorrect assumptions. It should maybe raise NotImplementedError.
    def getpeername(self) -> tuple[str, int] | tuple[str, int, int, int]:
        self._check_closed()
        if self._binding is not None:
            assert hasattr(
                self._binding, "remote"
            ), "This method seems to assume that self._binding has a remote UDPEndpoint"
            if self._binding.remote is not None:  # pragma: no cover
                assert isinstance(
                    self._binding.remote, UDPEndpoint
                ), "Self._binding.remote should be a UDPEndpoint"
                return self._binding.remote.as_python_sockaddr()
        _fake_err(errno.ENOTCONN)

    @overload
    def getsockopt(self, /, level: int, optname: int) -> int:
        ...

    @overload
    def getsockopt(self, /, level: int, optname: int, buflen: int) -> bytes:
        ...

    def getsockopt(
        self, /, level: int, optname: int, buflen: int | None = None
    ) -> int | bytes:
        self._check_closed()
        raise OSError(f"FakeNet doesn't implement getsockopt({level}, {optname})")

    @overload
    def setsockopt(self, /, level: int, optname: int, value: int | Buffer) -> None:
        ...

    @overload
    def setsockopt(self, /, level: int, optname: int, value: None, optlen: int) -> None:
        ...

    def setsockopt(
        self,
        /,
        level: int,
        optname: int,
        value: int | Buffer | None,
        optlen: int | None = None,
    ) -> None:
        self._check_closed()

        if (level, optname) == (
            trio.socket.IPPROTO_IPV6,
            trio.socket.IPV6_V6ONLY,
        ) and not value:
            raise NotImplementedError("FakeNet always has IPV6_V6ONLY=True")

        raise OSError(f"FakeNet doesn't implement setsockopt({level}, {optname}, ...)")

    ################################################################
    # Various boilerplate and trivial stubs
    ################################################################

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: builtins.type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    async def send(self, data: Buffer, flags: int = 0) -> int:
        return await self.sendto(data, flags, None)

    @overload
    async def sendto(
        self, __data: Buffer, __address: tuple[object, ...] | str | Buffer
    ) -> int:
        ...

    @overload
    async def sendto(
        self,
        __data: Buffer,
        __flags: int,
        __address: tuple[object, ...] | str | None | Buffer,
    ) -> int:
        ...

    async def sendto(self, *args: Any) -> int:
        data: Buffer
        flags: int
        address: tuple[object, ...] | str | Buffer
        if len(args) == 2:
            data, address = args
            flags = 0
        elif len(args) == 3:
            data, flags, address = args
        else:
            raise TypeError("wrong number of arguments")
        return await self._sendmsg([data], [], flags, address)

    async def recv(self, bufsize: int, flags: int = 0) -> bytes:
        data, address = await self.recvfrom(bufsize, flags)
        return data

    async def recv_into(self, buf: Buffer, nbytes: int = 0, flags: int = 0) -> int:
        got_bytes, address = await self.recvfrom_into(buf, nbytes, flags)
        return got_bytes

    async def recvfrom(self, bufsize: int, flags: int = 0) -> tuple[bytes, Any]:
        data, ancdata, msg_flags, address = await self._recvmsg(bufsize, flags)
        return data, address

    async def recvfrom_into(
        self, buf: Buffer, nbytes: int = 0, flags: int = 0
    ) -> tuple[int, Any]:
        if nbytes != 0 and nbytes != memoryview(buf).nbytes:
            raise NotImplementedError("partial recvfrom_into")
        got_nbytes, ancdata, msg_flags, address = await self._recvmsg_into(
            [buf], 0, flags
        )
        return got_nbytes, address

    async def _recvmsg(
        self, bufsize: int, ancbufsize: int = 0, flags: int = 0
    ) -> tuple[bytes, list[tuple[int, int, bytes]], int, Any]:
        buf = bytearray(bufsize)
        got_nbytes, ancdata, msg_flags, address = await self._recvmsg_into(
            [buf], ancbufsize, flags
        )
        return (bytes(buf[:got_nbytes]), ancdata, msg_flags, address)

    if sys.platform != "win32" or (
        not TYPE_CHECKING and hasattr(socket.socket, "sendmsg")
    ):
        recvmsg = _recvmsg

    def fileno(self) -> int:
        raise NotImplementedError("can't get fileno() for FakeNet sockets")

    def detach(self) -> int:
        raise NotImplementedError("can't detach() a FakeNet socket")

    def get_inheritable(self) -> bool:
        return False

    def set_inheritable(self, inheritable: bool) -> None:
        if inheritable:
            raise NotImplementedError("FakeNet can't make inheritable sockets")

    if sys.platform == "win32" or (
        not TYPE_CHECKING and hasattr(socket.socket, "share")
    ):

        def share(self, process_id: int) -> bytes:
            raise NotImplementedError("FakeNet can't share sockets")
