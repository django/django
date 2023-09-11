# This should eventually be cleaned up and become public, but for right now I'm just
# implementing enough to test DTLS.

# TODO:
# - user-defined routers
# - TCP
# - UDP broadcast

import errno
import ipaddress
import os
from typing import Optional, Union

import attr

import trio
from trio._util import Final, NoPublicConstructor

IPAddress = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]


def _family_for(ip: IPAddress) -> int:
    if isinstance(ip, ipaddress.IPv4Address):
        return trio.socket.AF_INET
    elif isinstance(ip, ipaddress.IPv6Address):
        return trio.socket.AF_INET6
    assert False  # pragma: no cover


def _wildcard_ip_for(family: int) -> IPAddress:
    if family == trio.socket.AF_INET:
        return ipaddress.ip_address("0.0.0.0")
    elif family == trio.socket.AF_INET6:
        return ipaddress.ip_address("::")
    else:
        assert False


def _localhost_ip_for(family: int) -> IPAddress:
    if family == trio.socket.AF_INET:
        return ipaddress.ip_address("127.0.0.1")
    elif family == trio.socket.AF_INET6:
        return ipaddress.ip_address("::1")
    else:
        assert False


def _fake_err(code):
    raise OSError(code, os.strerror(code))


def _scatter(data, buffers):
    written = 0
    for buf in buffers:
        next_piece = data[written : written + len(buf)]
        with memoryview(buf) as mbuf:
            mbuf[: len(next_piece)] = next_piece
        written += len(next_piece)
        if written == len(data):
            break
    return written


@attr.frozen
class UDPEndpoint:
    ip: IPAddress
    port: int

    def as_python_sockaddr(self):
        sockaddr = (self.ip.compressed, self.port)
        if isinstance(self.ip, ipaddress.IPv6Address):
            sockaddr += (0, 0)
        return sockaddr

    @classmethod
    def from_python_sockaddr(cls, sockaddr):
        ip, port = sockaddr[:2]
        return cls(ip=ipaddress.ip_address(ip), port=port)


@attr.frozen
class UDPBinding:
    local: UDPEndpoint


@attr.frozen
class UDPPacket:
    source: UDPEndpoint
    destination: UDPEndpoint
    payload: bytes = attr.ib(repr=lambda p: p.hex())

    def reply(self, payload):
        return UDPPacket(
            source=self.destination, destination=self.source, payload=payload
        )


@attr.frozen
class FakeSocketFactory(trio.abc.SocketFactory):
    fake_net: "FakeNet"

    def socket(self, family: int, type: int, proto: int) -> "FakeSocket":
        return FakeSocket._create(self.fake_net, family, type, proto)


@attr.frozen
class FakeHostnameResolver(trio.abc.HostnameResolver):
    fake_net: "FakeNet"

    async def getaddrinfo(
        self, host: str, port: Union[int, str], family=0, type=0, proto=0, flags=0
    ):
        raise NotImplementedError("FakeNet doesn't do fake DNS yet")

    async def getnameinfo(self, sockaddr, flags: int):
        raise NotImplementedError("FakeNet doesn't do fake DNS yet")


class FakeNet(metaclass=Final):
    def __init__(self):
        # When we need to pick an arbitrary unique ip address/port, use these:
        self._auto_ipv4_iter = ipaddress.IPv4Network("1.0.0.0/8").hosts()
        self._auto_ipv4_iter = ipaddress.IPv6Network("1::/16").hosts()
        self._auto_port_iter = iter(range(50000, 65535))

        self._bound: Dict[UDPBinding, FakeSocket] = {}

        self.route_packet = None

    def _bind(self, binding: UDPBinding, socket: "FakeSocket") -> None:
        if binding in self._bound:
            _fake_err(errno.EADDRINUSE)
        self._bound[binding] = socket

    def enable(self) -> None:
        trio.socket.set_custom_socket_factory(FakeSocketFactory(self))
        trio.socket.set_custom_hostname_resolver(FakeHostnameResolver(self))

    def send_packet(self, packet) -> None:
        if self.route_packet is None:
            self.deliver_packet(packet)
        else:
            self.route_packet(packet)

    def deliver_packet(self, packet) -> None:
        binding = UDPBinding(local=packet.destination)
        if binding in self._bound:
            self._bound[binding]._deliver_packet(packet)
        else:
            # No valid destination, so drop it
            pass


class FakeSocket(trio.socket.SocketType, metaclass=NoPublicConstructor):
    def __init__(self, fake_net: FakeNet, family: int, type: int, proto: int):
        self._fake_net = fake_net

        if not family:
            family = trio.socket.AF_INET
        if not type:
            type = trio.socket.SOCK_STREAM

        if family not in (trio.socket.AF_INET, trio.socket.AF_INET6):
            raise NotImplementedError(f"FakeNet doesn't (yet) support family={family}")
        if type != trio.socket.SOCK_DGRAM:
            raise NotImplementedError(f"FakeNet doesn't (yet) support type={type}")

        self.family = family
        self.type = type
        self.proto = proto

        self._closed = False

        self._packet_sender, self._packet_receiver = trio.open_memory_channel(
            float("inf")
        )

        # This is the source-of-truth for what port etc. this socket is bound to
        self._binding: Optional[UDPBinding] = None

    def _check_closed(self):
        if self._closed:
            _fake_err(errno.EBADF)

    def close(self):
        # breakpoint()
        if self._closed:
            return
        self._closed = True
        if self._binding is not None:
            del self._fake_net._bound[self._binding]
        self._packet_receiver.close()

    async def _resolve_address_nocp(self, address, *, local):
        return await trio._socket._resolve_address_nocp(
            self.type,
            self.family,
            self.proto,
            address=address,
            ipv6_v6only=False,
            local=local,
        )

    def _deliver_packet(self, packet: UDPPacket):
        try:
            self._packet_sender.send_nowait(packet)
        except trio.BrokenResourceError:
            # sending to a closed socket -- UDP packets get dropped
            pass

    ################################################################
    # Actual IO operation implementations
    ################################################################

    async def bind(self, addr):
        self._check_closed()
        if self._binding is not None:
            _fake_error(errno.EINVAL)
        await trio.lowlevel.checkpoint()
        ip_str, port = await self._resolve_address_nocp(addr, local=True)
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

    async def connect(self, peer):
        raise NotImplementedError("FakeNet does not (yet) support connected sockets")

    async def sendmsg(self, *args):
        self._check_closed()
        ancdata = []
        flags = 0
        address = None
        if len(args) == 1:
            (buffers,) = args
        elif len(args) == 2:
            buffers, address = args
        elif len(args) == 3:
            buffers, flags, address = args
        elif len(args) == 4:
            buffers, ancdata, flags, address = args
        else:
            raise TypeError("wrong number of arguments")

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

        packet = UDPPacket(
            source=self._binding.local,
            destination=destination,
            payload=payload,
        )

        self._fake_net.send_packet(packet)

        return len(payload)

    async def recvmsg_into(self, buffers, ancbufsize=0, flags=0):
        if ancbufsize != 0:
            raise NotImplementedError("FakeNet doesn't support ancillary data")
        if flags != 0:
            raise NotImplementedError("FakeNet doesn't support any recv flags")

        self._check_closed()

        ancdata = []
        msg_flags = 0

        packet = await self._packet_receiver.receive()
        address = packet.source.as_python_sockaddr()
        written = _scatter(packet.payload, buffers)
        if written < len(packet.payload):
            msg_flags |= trio.socket.MSG_TRUNC
        return written, ancdata, msg_flags, address

    ################################################################
    # Simple state query stuff
    ################################################################

    def getsockname(self):
        self._check_closed()
        if self._binding is not None:
            return self._binding.local.as_python_sockaddr()
        elif self.family == trio.socket.AF_INET:
            return ("0.0.0.0", 0)
        else:
            assert self.family == trio.socket.AF_INET6
            return ("::", 0)

    def getpeername(self):
        self._check_closed()
        if self._binding is not None:
            if self._binding.remote is not None:
                return self._binding.remote.as_python_sockaddr()
        _fake_err(errno.ENOTCONN)

    def getsockopt(self, level, item):
        self._check_closed()
        raise OSError(f"FakeNet doesn't implement getsockopt({level}, {item})")

    def setsockopt(self, level, item, value):
        self._check_closed()

        if (level, item) == (trio.socket.IPPROTO_IPV6, trio.socket.IPV6_V6ONLY):
            if not value:
                raise NotImplementedError("FakeNet always has IPV6_V6ONLY=True")

        raise OSError(f"FakeNet doesn't implement setsockopt({level}, {item}, ...)")

    ################################################################
    # Various boilerplate and trivial stubs
    ################################################################

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    async def send(self, data, flags=0):
        return await self.sendto(data, flags, None)

    async def sendto(self, *args):
        if len(args) == 2:
            data, address = args
            flags = 0
        elif len(args) == 3:
            data, flags, address = args
        else:
            raise TypeError("wrong number of arguments")
        return await self.sendmsg([data], [], flags, address)

    async def recv(self, bufsize, flags=0):
        data, address = await self.recvfrom(bufsize, flags)
        return data

    async def recv_into(self, buf, nbytes=0, flags=0):
        got_bytes, address = await self.recvfrom_into(buf, nbytes, flags)
        return got_bytes

    async def recvfrom(self, bufsize, flags=0):
        data, ancdata, msg_flags, address = await self.recvmsg(bufsize, flags)
        return data, address

    async def recvfrom_into(self, buf, nbytes=0, flags=0):
        if nbytes != 0 and nbytes != len(buf):
            raise NotImplementedError("partial recvfrom_into")
        got_nbytes, ancdata, msg_flags, address = await self.recvmsg_into(
            [buf], 0, flags
        )
        return got_nbytes, address

    async def recvmsg(self, bufsize, ancbufsize=0, flags=0):
        buf = bytearray(bufsize)
        got_nbytes, ancdata, msg_flags, address = await self.recvmsg_into(
            [buf], ancbufsize, flags
        )
        return (bytes(buf[:got_nbytes]), ancdata, msg_flags, address)

    def fileno(self):
        raise NotImplementedError("can't get fileno() for FakeNet sockets")

    def detach(self):
        raise NotImplementedError("can't detach() a FakeNet socket")

    def get_inheritable(self):
        return False

    def set_inheritable(self, inheritable):
        if inheritable:
            raise NotImplementedError("FakeNet can't make inheritable sockets")

    def share(self, process_id):
        raise NotImplementedError("FakeNet can't share sockets")
