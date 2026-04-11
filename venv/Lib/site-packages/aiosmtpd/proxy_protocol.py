# Copyright 2014-2021 The aiosmtpd Developers
# SPDX-License-Identifier: Apache-2.0

import contextlib
import logging
import re
import struct
from collections import deque
from enum import IntEnum
from functools import partial
from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import Any, ByteString, Dict, Optional, Protocol, Tuple, Union

import attr
from public import public

V2_SIGNATURE = b"\r\n\r\n\x00\r\nQUIT\n"


class V2_CMD(IntEnum):
    """
    Valid Version 2 "command"
    """

    LOCAL = 0
    PROXY = 1


class AF(IntEnum):
    """
    Valid address families. Version 1 "UNKNOWN" mapped to "UNSPEC"
    """

    UNSPEC = 0
    """For version 1, means UNKNOWN"""
    INET = 1
    """Internet Protocol v4"""
    INET6 = 2
    """Internet Protocol v6"""
    UNIX = 3
    """Unix Socket; invalid for version 1"""


class PROTO(IntEnum):
    """
    Valid transport protocols. Version 1 "UNKNOWN" mapped to "UNSPEC"
    """

    UNSPEC = 0
    """For version 1, means UNKNOWN"""
    STREAM = 1
    """TCP"""
    DGRAM = 2
    """UDP; invalid for version 1"""


V2_VALID_CMDS = {item.value for item in V2_CMD}
V2_VALID_FAMS = {item.value for item in AF}
V2_VALID_PROS = {item.value for item in PROTO}
V2_PARSE_ADDR_FAMPRO = {
    (AF.INET << 4) | PROTO.STREAM,
    (AF.INET << 4) | PROTO.DGRAM,
    (AF.INET6 << 4) | PROTO.STREAM,
    (AF.INET6 << 4) | PROTO.DGRAM,
    (AF.UNIX << 4) | PROTO.STREAM,
    (AF.UNIX << 4) | PROTO.DGRAM,
}
"""Family & Proto combinations that need address parsing"""


__all__ = ["struct", "partial", "IPv4Address", "IPv6Address"]
__all__.extend(
    k for k in globals().keys() if k.startswith("V1_") or k.startswith("V2_")
)


_NOT_FOUND = object()

log = logging.getLogger("mail.debug")


# region #### Custom Types ############################################################

EndpointAddress = Union[IPv4Address, IPv6Address, Union[str, bytes]]


@public
class MalformedTLV(RuntimeError):
    pass


@public
class UnknownTypeTLV(KeyError):
    pass


@public
class AsyncReader(Protocol):
    async def read(self, n: int = ...) -> bytes:
        ...

    async def readexactly(self, n: int) -> bytes:
        ...

    async def readuntil(self, separator: bytes = ...) -> bytes:
        ...


_anoinit = partial(attr.ib, init=False)


@public
class ProxyTLV(dict):
    """
    Represents the TLV Vectors inside a PROXYv2 Handshake
    """

    __slots__ = ("tlv_loc",)

    # https://github.com/haproxy/haproxy/blob/v2.3.0/doc/proxy-protocol.txt#L538-L549
    PP2_TYPENAME: Dict[int, str] = {
        0x01: "ALPN",
        0x02: "AUTHORITY",
        0x03: "CRC32C",
        0x04: "NOOP",
        0x05: "UNIQUE_ID",
        0x20: "SSL",
        0x21: "SSL_VERSION",
        0x22: "SSL_CN",
        0x23: "SSL_CIPHER",
        0x24: "SSL_SIG_ALG",
        0x25: "SSL_KEY_ALG",
        0x30: "NETNS",
    }

    def __init__(self, *args, _tlv_loc: Dict[str, int], **kwargs):
        super().__init__(*args, **kwargs)
        self.tlv_loc = _tlv_loc

    def __getattr__(self, item: str) -> Any:
        return self.get(item)

    def same_attribs(self, _raises: bool = False, **kwargs) -> bool:
        """
        Helper function to test whether attribute(s) exists, and whether the attribute's
        value is as expected. For ProxyTLV, since it inherits from dict, you can also
        use direct dict comparison.

        :param _raises: If True, raises an Error instead of returning bool
        """
        for k, v in kwargs.items():
            actual = self.get(k, _NOT_FOUND)
            if actual is _NOT_FOUND:
                if _raises:
                    raise KeyError(f"notfound:{k}")
                else:
                    return False
            if actual != v:
                if _raises:
                    raise ValueError(f"mismatch:{k} actual={actual!r} expect={v!r}")
                else:
                    return False
        return True

    @classmethod
    def parse(
        cls,
        data: ByteString,
        partial_ok: bool = True,
        strict: bool = False,
    ) -> Tuple[Dict[str, Any], Dict[str, int]]:
        """
        Parse a bunch of bytes into TLV Vectors.

        :param data: The bunch of bytes to parse
        :param partial_ok: Keep result of parsing so far if error encountered
        :param strict: If true, reject unrecognized TYPEs
        """
        rslt: Dict[str, Any] = {}
        tlv_loc: Dict[str, int] = {}

        def _pars(chunk: ByteString, *, offset: int) -> None:
            i = 0
            while i < len(chunk):
                typ = chunk[i]
                len_ = int.from_bytes(chunk[i + 1 : i + 3], "big")
                val = chunk[i + 3 : i + 3 + len_]
                if len(val) < len_:
                    raise MalformedTLV(f"TLV 0x{typ:02X} is malformed!")
                typ_name = cls.PP2_TYPENAME.get(typ)
                if typ_name is None:
                    typ_name = f"x{typ:02X}"
                    if strict:
                        raise UnknownTypeTLV(typ_name)
                tlv_loc[typ_name] = offset + i
                if typ_name == "SSL":
                    rslt["SSL_CLIENT"] = val[0]
                    rslt["SSL_VERIFY"] = int.from_bytes(val[1:5], "big")
                    try:
                        _pars(val[5:], offset=i)
                        rslt["SSL"] = True
                    except MalformedTLV:
                        rslt["SSL"] = False
                        if not partial_ok:
                            raise
                        else:
                            return
                else:
                    rslt[typ_name] = val
                i += 3 + len_

        try:
            _pars(data, offset=0)
        except MalformedTLV:
            if not partial_ok:
                raise
        return rslt, tlv_loc

    @classmethod
    def from_raw(
        cls, raw: ByteString, strict: bool = False
    ) -> Optional["ProxyTLV"]:
        """
        Parses raw bytes for TLV Vectors, decode them and giving them human-readable
        name if applicable, and returns a ProxyTLV object.

        :param raw: The raw bytes
        :param strict: If true, reject unrecognized TYPEs
        """
        if len(raw) == 0:
            return None
        parsed, tlv_loc = cls.parse(raw, partial_ok=False, strict=strict)
        return cls(parsed, _tlv_loc=tlv_loc)

    @classmethod
    def name_to_num(cls, name: str) -> Optional[int]:
        """
        Perform backmapping from TYPENAME to TYPE (numeric)

        :param name: TYPENAME to backmap
        :return: TYPE (int) if backmap available, else None
        """
        for k, v in cls.PP2_TYPENAME.items():
            if name == v:
                return k
        return None


@public
@attr.s(slots=True)
class ProxyData:
    """
    Represents data received during PROXY Protocol Handshake, in an already-parsed form
    """

    version: Optional[int] = attr.ib(kw_only=True, init=True)
    """PROXY Protocol version; None if not recognized/malformed"""
    command: Optional[V2_CMD] = _anoinit(default=None)
    """PROXYv2 command"""
    family: Optional[AF] = _anoinit(default=None)
    """Address Family (AF)"""
    protocol: Optional[PROTO] = _anoinit(default=None)
    """Proxied Protocol (PROTO)"""
    src_addr: Optional[EndpointAddress] = _anoinit(default=None)
    dst_addr: Optional[EndpointAddress] = _anoinit(default=None)
    src_port: Optional[int] = _anoinit(default=None)
    dst_port: Optional[int] = _anoinit(default=None)
    rest: ByteString = _anoinit(default=b"")
    """
    Rest of PROXY Protocol data following UNKNOWN (v1) or UNSPEC (v2), or containing
    undecoded TLV (v2). If the latter, you can use the ProxyTLV class to parse the
    binary data.
    """
    whole_raw: bytearray = _anoinit(factory=bytearray)
    """
    The whole undecoded PROXY Header as-received. This can be used to (1) perform
    troubleshooting, and/or (2) calculate CRC32C (which will NOT be implemented in
    this module to reduce number of deps.
    """
    tlv_start: int = _anoinit(default=None)
    """
    Byte offset of the first TLV Vector within whole_raw.
    """
    error: str = _anoinit(default="")
    """
    If not an empty string, contains the error encountered when parsing
    """
    _tlv: Optional[ProxyTLV] = _anoinit(default=None)

    @property
    def valid(self) -> bool:
        return not (self.error or self.version is None or self.protocol is None)

    @property
    def tlv(self) -> Optional[ProxyTLV]:
        if self._tlv is None:
            with contextlib.suppress(MalformedTLV):
                self._tlv = ProxyTLV.from_raw(self.rest)
        return self._tlv

    def with_error(self, error_msg: str, log_prefix: bool = True) -> "ProxyData":
        """
        Returns a ProxyData with its .error attrib set to error_msg, at the same time
        sending a log.warning.

        :param error_msg: Error message
        :param log_prefix: If True, add "PROXY error:" prefix to log message
        """
        if log_prefix:
            log.warning(f"PROXY error: {error_msg}")
        else:
            log.warning(error_msg)
        self.error = error_msg
        return self

    def same_attribs(self, _raises: bool = False, **kwargs) -> bool:
        for k, v in kwargs.items():
            actual = getattr(self, k, _NOT_FOUND)
            if actual is _NOT_FOUND:
                if _raises:
                    raise KeyError(f"notfound:{k}")
                else:
                    return False
            if actual != v:
                if _raises:
                    raise ValueError(f"mismatch:{k} actual={actual!r} expect={v!r}")
                else:
                    return False
        return True

    def __bool__(self) -> bool:
        return self.valid


# endregion

RE_ADDR_ALLOWCHARS = re.compile(r"^[0-9a-fA-F.:]+$")
RE_PORT_NOLEADZERO = re.compile(r"^[1-9]\d{0,4}|0$")

# Reference: https://github.com/haproxy/haproxy/blob/v2.3.0/doc/proxy-protocol.txt


async def _get_v1(reader: AsyncReader, initial: ByteString = b"") -> ProxyData:
    proxy_data = ProxyData(version=1)
    proxy_data.whole_raw = bytearray(initial)

    log.debug("Get all PROXYv1 handshake")
    data = await reader.readuntil()
    log.debug("Got PROXYv1 handshake")
    proxy_data.whole_raw += data
    if len(proxy_data.whole_raw) > 107:
        return proxy_data.with_error("PROXYv1 header too long")
    if not data.endswith(b"\r\n"):
        return proxy_data.with_error("PROXYv1 malformed")
    # Split using b" " so two consecutive SP will result in an empty field
    # (instead of silently treated as an SP)
    data_parts = deque(data[:-2].split(b" "))

    if data_parts.popleft() != b"":
        # If first elem is not b"", then between proxy_line[5] and first b" " there
        # are characters. Or, in other words, there are characters _right_after_
        # the b"PROXY" signature
        return proxy_data.with_error("PROXYv1 wrong signature")

    proto = data_parts.popleft()

    if proto == b"UNKNOWN":
        proxy_data.protocol = PROTO.UNSPEC
        proxy_data.family = AF.UNSPEC
        proxy_data.rest = (b" " + b" ".join(data_parts)) if data_parts else b""
        return proxy_data

    if proto.endswith(b"4"):
        af = AF.INET
    elif proto.endswith(b"6"):
        af = AF.INET6
    else:
        return proxy_data.with_error("PROXYv1 unrecognized family")
    proxy_data.family = af

    if not proto.startswith(b"TCP"):
        return proxy_data.with_error("PROXYv1 unrecognized protocol")

    proxy_data.protocol = PROTO.STREAM

    async def get_ap(matcher: "re.Pattern[str]") -> str:
        chunk = data_parts.popleft().decode("latin-1")
        if not matcher.match(chunk):
            raise ValueError
        return chunk

    try:
        addr = await get_ap(RE_ADDR_ALLOWCHARS)
        src_addr = ip_address(addr)
        addr = await get_ap(RE_ADDR_ALLOWCHARS)
        dst_addr = ip_address(addr)
    except ValueError:
        return proxy_data.with_error("PROXYv1 address malformed")

    if af == AF.INET and not src_addr.version == dst_addr.version == 4:
        return proxy_data.with_error("PROXYv1 address not IPv4")
    elif af == AF.INET6 and not src_addr.version == dst_addr.version == 6:
        return proxy_data.with_error("PROXYv1 address not IPv6")

    proxy_data.src_addr = src_addr
    proxy_data.dst_addr = dst_addr

    try:
        port = await get_ap(RE_PORT_NOLEADZERO)
        proxy_data.src_port = int(port)
        port = await get_ap(RE_PORT_NOLEADZERO)
        proxy_data.dst_port = int(port)
    except ValueError:
        return proxy_data.with_error("PROXYv1 port malformed")

    if not 0 <= proxy_data.src_port <= 65535:
        return proxy_data.with_error("PROXYv1 src port out of bounds")
    if not 0 <= proxy_data.dst_port <= 65535:
        return proxy_data.with_error("PROXYv1 dst port out of bounds")

    if data_parts:
        return proxy_data.with_error("PROXYv1 unrecognized extraneous data")

    return proxy_data


async def _get_v2(reader: AsyncReader, initial: ByteString = b"") -> ProxyData:
    proxy_data = ProxyData(version=2)
    whole_raw = bytearray()

    async def read_rest(
        field_name: str, field_buf: bytearray, field_len: int
    ) -> Tuple[bytearray, bytearray]:
        left = field_len - len(field_buf)
        while left > 0:
            piece = await reader.read(left)
            left -= len(piece)
            if not piece or left < 0:
                raise ConnectionError(f"Connection lost while waiting for {field_name}")
            field_buf += piece
        return field_buf[0:field_len], field_buf[field_len:]

    signature = bytearray(initial)
    log.debug("Waiting for PROXYv2 signature")
    signature, header = await read_rest("signature", signature, 12)
    if signature != V2_SIGNATURE:
        return proxy_data.with_error("PROXYv2 wrong signature")
    log.debug("Got PROXYv2 signature")
    whole_raw += signature

    log.debug("Waiting for PROXYv2 Header")
    header, tail_part = await read_rest("header", header, 4)
    log.debug("Got PROXYv2 header")
    whole_raw += header

    ver_cmd, fam_proto, len_tail = struct.unpack("!BBH", header)

    if (ver_cmd & 0xF0) != 0x20:
        return proxy_data.with_error("PROXYv2 illegal version")

    proxy_data.command = ver_cmd & 0x0F
    if proxy_data.command not in V2_VALID_CMDS:
        return proxy_data.with_error("PROXYv2 unsupported command")

    proxy_data.family = (fam_proto & 0xF0) >> 4
    if proxy_data.family not in V2_VALID_FAMS:
        return proxy_data.with_error("PROXYv2 unsupported family")

    proxy_data.protocol = fam_proto & 0x0F
    if proxy_data.protocol not in V2_VALID_PROS:
        return proxy_data.with_error("PROXYv2 unsupported protocol")

    log.debug("Waiting for PROXYv2 tail part")
    tail_part, _ = await read_rest("tail part", tail_part, len_tail)
    log.debug("Got PROXYv2 tail part")
    whole_raw += tail_part
    proxy_data.whole_raw = whole_raw

    if fam_proto not in V2_PARSE_ADDR_FAMPRO:
        proxy_data.rest = tail_part
        return proxy_data

    if proxy_data.family == AF.INET:
        unpacker = "!4s4sHH"
    elif proxy_data.family == AF.INET6:
        unpacker = "!16s16sHH"
    else:
        assert proxy_data.family == AF.UNIX
        unpacker = "108s108s0s0s"

    addr_len = struct.calcsize(unpacker)
    addr_struct = tail_part[0:addr_len]
    if len(addr_struct) < addr_len:
        return proxy_data.with_error("PROXYv2 truncated address")
    tail_part = tail_part[addr_len:]
    s_addr, d_addr, s_port, d_port = struct.unpack(unpacker, addr_struct)

    if proxy_data.family == AF.INET:
        proxy_data.src_addr = IPv4Address(s_addr)
        proxy_data.dst_addr = IPv4Address(d_addr)
        proxy_data.src_port = s_port
        proxy_data.dst_port = d_port
    elif proxy_data.family == AF.INET6:
        proxy_data.src_addr = IPv6Address(s_addr)
        proxy_data.dst_addr = IPv6Address(d_addr)
        proxy_data.src_port = s_port
        proxy_data.dst_port = d_port
    else:
        assert proxy_data.family == AF.UNIX
        proxy_data.src_addr = s_addr
        proxy_data.dst_addr = d_addr

    proxy_data.rest = tail_part
    if tail_part:
        proxy_data.tlv_start = 16 + addr_len

    return proxy_data


@public
async def get_proxy(reader_func: AsyncReader) -> ProxyData:
    """
    :param reader_func: Async function that implements the AsyncReader protocol.
    :return: Proxy Data
    """
    log.debug("Waiting for PROXY signature")
    signature = await reader_func.readexactly(5)
    try:
        if signature == b"PROXY":
            log.debug("PROXY version 1")
            return await _get_v1(reader_func, signature)
        elif signature == V2_SIGNATURE[0:5]:
            log.debug("PROXY version 2")
            return await _get_v2(reader_func, signature)
        else:
            return ProxyData(version=None).with_error("PROXY unrecognized signature")
    except Exception as e:
        return ProxyData(version=None).with_error(f"PROXY exception: {str(e)}", False)
