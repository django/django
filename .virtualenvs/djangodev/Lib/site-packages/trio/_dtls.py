# Implementation of DTLS 1.2, using pyopenssl
# https://datatracker.ietf.org/doc/html/rfc6347
#
# OpenSSL's APIs for DTLS are extremely awkward and limited, which forces us to jump
# through a *lot* of hoops and implement important chunks of the protocol ourselves.
# Hopefully they fix this before implementing DTLS 1.3, because it's a very different
# protocol, and it's probably impossible to pull tricks like we do here.

from __future__ import annotations

import contextlib
import enum
import errno
import hmac
import os
import struct
import warnings
import weakref
from itertools import count
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Generic,
    Iterable,
    Iterator,
    TypeVar,
    Union,
)
from weakref import ReferenceType, WeakValueDictionary

import attrs

import trio

from ._util import NoPublicConstructor, final

if TYPE_CHECKING:
    from types import TracebackType

    # See DTLSEndpoint.__init__ for why this is imported here
    from OpenSSL import SSL  # noqa: TCH004
    from typing_extensions import Self, TypeAlias, TypeVarTuple, Unpack

    from trio.socket import SocketType

    PosArgsT = TypeVarTuple("PosArgsT")

MAX_UDP_PACKET_SIZE = 65527


def packet_header_overhead(sock: SocketType) -> int:
    if sock.family == trio.socket.AF_INET:
        return 28
    else:
        return 48


def worst_case_mtu(sock: SocketType) -> int:
    if sock.family == trio.socket.AF_INET:
        return 576 - packet_header_overhead(sock)
    else:
        return 1280 - packet_header_overhead(sock)


def best_guess_mtu(sock: SocketType) -> int:
    return 1500 - packet_header_overhead(sock)


# There are a bunch of different RFCs that define these codes, so for a
# comprehensive collection look here:
# https://www.iana.org/assignments/tls-parameters/tls-parameters.xhtml
class ContentType(enum.IntEnum):
    change_cipher_spec = 20
    alert = 21
    handshake = 22
    application_data = 23
    heartbeat = 24


class HandshakeType(enum.IntEnum):
    hello_request = 0
    client_hello = 1
    server_hello = 2
    hello_verify_request = 3
    new_session_ticket = 4
    end_of_early_data = 4
    encrypted_extensions = 8
    certificate = 11
    server_key_exchange = 12
    certificate_request = 13
    server_hello_done = 14
    certificate_verify = 15
    client_key_exchange = 16
    finished = 20
    certificate_url = 21
    certificate_status = 22
    supplemental_data = 23
    key_update = 24
    compressed_certificate = 25
    ekt_key = 26
    message_hash = 254


class ProtocolVersion:
    DTLS10 = bytes([254, 255])
    DTLS12 = bytes([254, 253])


EPOCH_MASK = 0xFFFF << (6 * 8)


# Conventions:
# - All functions that handle network data end in _untrusted.
# - All functions end in _untrusted MUST make sure that bad data from the
#   network cannot *only* cause BadPacket to be raised. No IndexError or
#   struct.error or whatever.
class BadPacket(Exception):
    pass


# This checks that the DTLS 'epoch' field is 0, which is true iff we're in the
# initial handshake. It doesn't check the ContentType, because not all
# handshake messages have ContentType==handshake -- for example,
# ChangeCipherSpec is used during the handshake but has its own ContentType.
#
# Cannot fail.
def part_of_handshake_untrusted(packet: bytes) -> bool:
    # If the packet is too short, then slicing will successfully return a
    # short string, which will necessarily fail to match.
    return packet[3:5] == b"\x00\x00"


# Cannot fail
def is_client_hello_untrusted(packet: bytes) -> bool:
    try:
        return (
            packet[0] == ContentType.handshake
            and packet[13] == HandshakeType.client_hello
        )
    except IndexError:
        # Invalid DTLS record
        return False


# DTLS records are:
# - 1 byte content type
# - 2 bytes version
# - 8 bytes epoch+seqno
#    Technically this is 2 bytes epoch then 6 bytes seqno, but we treat it as
#    a single 8-byte integer, where epoch changes are represented as jumping
#    forward by 2**(6*8).
# - 2 bytes payload length (unsigned big-endian)
# - payload
RECORD_HEADER = struct.Struct("!B2sQH")


def to_hex(data: bytes) -> str:  # pragma: no cover
    return data.hex()


@attrs.frozen
class Record:
    content_type: int
    version: bytes = attrs.field(repr=to_hex)
    epoch_seqno: int
    payload: bytes = attrs.field(repr=to_hex)


def records_untrusted(packet: bytes) -> Iterator[Record]:
    i = 0
    while i < len(packet):
        try:
            ct, version, epoch_seqno, payload_len = RECORD_HEADER.unpack_from(packet, i)
        # Marked as no-cover because at time of writing, this code is unreachable
        # (records_untrusted only gets called on packets that are either trusted or that
        # have passed is_client_hello_untrusted, which filters out short packets)
        except struct.error as exc:  # pragma: no cover
            raise BadPacket("invalid record header") from exc
        i += RECORD_HEADER.size
        payload = packet[i : i + payload_len]
        if len(payload) != payload_len:
            raise BadPacket("short record")
        i += payload_len
        yield Record(ct, version, epoch_seqno, payload)


def encode_record(record: Record) -> bytes:
    header = RECORD_HEADER.pack(
        record.content_type,
        record.version,
        record.epoch_seqno,
        len(record.payload),
    )
    return header + record.payload


# Handshake messages are:
# - 1 byte message type
# - 3 bytes total message length
# - 2 bytes message sequence number
# - 3 bytes fragment offset
# - 3 bytes fragment length
HANDSHAKE_MESSAGE_HEADER = struct.Struct("!B3sH3s3s")


@attrs.frozen
class HandshakeFragment:
    msg_type: int
    msg_len: int
    msg_seq: int
    frag_offset: int
    frag_len: int
    frag: bytes = attrs.field(repr=to_hex)


def decode_handshake_fragment_untrusted(payload: bytes) -> HandshakeFragment:
    # Raises BadPacket if decoding fails
    try:
        (
            msg_type,
            msg_len_bytes,
            msg_seq,
            frag_offset_bytes,
            frag_len_bytes,
        ) = HANDSHAKE_MESSAGE_HEADER.unpack_from(payload)
    except struct.error as exc:
        raise BadPacket("bad handshake message header") from exc
    # 'struct' doesn't have built-in support for 24-bit integers, so we
    # have to do it by hand. These can't fail.
    msg_len = int.from_bytes(msg_len_bytes, "big")
    frag_offset = int.from_bytes(frag_offset_bytes, "big")
    frag_len = int.from_bytes(frag_len_bytes, "big")
    frag = payload[HANDSHAKE_MESSAGE_HEADER.size :]
    if len(frag) != frag_len:
        raise BadPacket("handshake fragment length doesn't match record length")
    return HandshakeFragment(
        msg_type,
        msg_len,
        msg_seq,
        frag_offset,
        frag_len,
        frag,
    )


def encode_handshake_fragment(hsf: HandshakeFragment) -> bytes:
    hs_header = HANDSHAKE_MESSAGE_HEADER.pack(
        hsf.msg_type,
        hsf.msg_len.to_bytes(3, "big"),
        hsf.msg_seq,
        hsf.frag_offset.to_bytes(3, "big"),
        hsf.frag_len.to_bytes(3, "big"),
    )
    return hs_header + hsf.frag


def decode_client_hello_untrusted(packet: bytes) -> tuple[int, bytes, bytes]:
    # Raises BadPacket if parsing fails
    # Returns (record epoch_seqno, cookie from the packet, data that should be
    # hashed into cookie)
    try:
        # ClientHello has to be the first record in the packet
        record = next(records_untrusted(packet))
        # no-cover because at time of writing, this is unreachable:
        # decode_client_hello_untrusted is only called on packets that have passed
        # is_client_hello_untrusted, which confirms the content type.
        if record.content_type != ContentType.handshake:  # pragma: no cover
            raise BadPacket("not a handshake record")
        fragment = decode_handshake_fragment_untrusted(record.payload)
        if fragment.msg_type != HandshakeType.client_hello:
            raise BadPacket("not a ClientHello")
        # ClientHello can't be fragmented, because reassembly requires holding
        # per-connection state, and we refuse to allocate per-connection state
        # until after we get a valid ClientHello.
        if fragment.frag_offset != 0:
            raise BadPacket("fragmented ClientHello")
        if fragment.frag_len != fragment.msg_len:
            raise BadPacket("fragmented ClientHello")

        # As per RFC 6347:
        #
        #   When responding to a HelloVerifyRequest, the client MUST use the
        #   same parameter values (version, random, session_id, cipher_suites,
        #   compression_method) as it did in the original ClientHello.  The
        #   server SHOULD use those values to generate its cookie and verify that
        #   they are correct upon cookie receipt.
        #
        # However, the record-layer framing can and will change (e.g. the
        # second ClientHello will have a new record-layer sequence number). So
        # we need to pull out the handshake message alone, discarding the
        # record-layer stuff, and then we're going to hash all of it *except*
        # the cookie.

        body = fragment.frag
        # ClientHello is:
        #
        # - 2 bytes client_version
        # - 32 bytes random
        # - 1 byte session_id length
        # - session_id
        # - 1 byte cookie length
        # - cookie
        # - everything else
        #
        # So to find the cookie, so we need to figure out how long the
        # session_id is and skip past it.
        session_id_len = body[2 + 32]
        cookie_len_offset = 2 + 32 + 1 + session_id_len
        cookie_len = body[cookie_len_offset]

        cookie_start = cookie_len_offset + 1
        cookie_end = cookie_start + cookie_len

        before_cookie = body[:cookie_len_offset]
        cookie = body[cookie_start:cookie_end]
        after_cookie = body[cookie_end:]

        if len(cookie) != cookie_len:
            raise BadPacket("short cookie")
        return (record.epoch_seqno, cookie, before_cookie + after_cookie)

    except (struct.error, IndexError) as exc:
        raise BadPacket("bad ClientHello") from exc


@attrs.frozen
class HandshakeMessage:
    record_version: bytes = attrs.field(repr=to_hex)
    msg_type: HandshakeType
    msg_seq: int
    body: bytearray = attrs.field(repr=to_hex)


# ChangeCipherSpec is part of the handshake, but it's not a "handshake
# message" and can't be fragmented the same way. Sigh.
@attrs.frozen
class PseudoHandshakeMessage:
    record_version: bytes = attrs.field(repr=to_hex)
    content_type: int
    payload: bytes = attrs.field(repr=to_hex)


# The final record in a handshake is Finished, which is encrypted, can't be fragmented
# (at least by us), and keeps its record number (because it's in a new epoch). So we
# just pass it through unchanged. (Fortunately, the payload is only a single hash value,
# so the largest it will ever be is 64 bytes for a 512-bit hash. Which is small enough
# that it never requires fragmenting to fit into a UDP packet.
@attrs.frozen
class OpaqueHandshakeMessage:
    record: Record


_AnyHandshakeMessage: TypeAlias = Union[
    HandshakeMessage, PseudoHandshakeMessage, OpaqueHandshakeMessage
]


# This takes a raw outgoing handshake volley that openssl generated, and
# reconstructs the handshake messages inside it, so that we can repack them
# into records while retransmitting. So the data ought to be well-behaved --
# it's not coming from the network.
def decode_volley_trusted(
    volley: bytes,
) -> list[_AnyHandshakeMessage]:
    messages: list[_AnyHandshakeMessage] = []
    messages_by_seq = {}
    for record in records_untrusted(volley):
        # ChangeCipherSpec isn't a handshake message, so it can't be fragmented.
        # Handshake messages with epoch > 0 are encrypted, so we can't fragment them
        # either. Fortunately, ChangeCipherSpec has a 1 byte payload, and the only
        # encrypted handshake message is Finished, whose payload is a single hash value
        # -- so 32 bytes for SHA-256, 64 for SHA-512, etc. Neither is going to be so
        # large that it has to be fragmented to fit into a single packet.
        if record.epoch_seqno & EPOCH_MASK:
            messages.append(OpaqueHandshakeMessage(record))
        elif record.content_type in (ContentType.change_cipher_spec, ContentType.alert):
            messages.append(
                PseudoHandshakeMessage(
                    record.version, record.content_type, record.payload
                )
            )
        else:
            assert record.content_type == ContentType.handshake
            fragment = decode_handshake_fragment_untrusted(record.payload)
            msg_type = HandshakeType(fragment.msg_type)
            if fragment.msg_seq not in messages_by_seq:
                msg = HandshakeMessage(
                    record.version,
                    msg_type,
                    fragment.msg_seq,
                    bytearray(fragment.msg_len),
                )
                messages.append(msg)
                messages_by_seq[fragment.msg_seq] = msg
            else:
                msg = messages_by_seq[fragment.msg_seq]
            assert msg.msg_type == fragment.msg_type
            assert msg.msg_seq == fragment.msg_seq
            assert len(msg.body) == fragment.msg_len

            msg.body[
                fragment.frag_offset : fragment.frag_offset + fragment.frag_len
            ] = fragment.frag

    return messages


class RecordEncoder:
    def __init__(self) -> None:
        self._record_seq = count()

    def set_first_record_number(self, n: int) -> None:
        self._record_seq = count(n)

    def encode_volley(
        self,
        messages: Iterable[_AnyHandshakeMessage],
        mtu: int,
    ) -> list[bytearray]:
        packets = []
        packet = bytearray()
        for message in messages:
            if isinstance(message, OpaqueHandshakeMessage):
                encoded = encode_record(message.record)
                if mtu - len(packet) - len(encoded) <= 0:
                    packets.append(packet)
                    packet = bytearray()
                packet += encoded
                assert len(packet) <= mtu
            elif isinstance(message, PseudoHandshakeMessage):
                space = mtu - len(packet) - RECORD_HEADER.size - len(message.payload)
                if space <= 0:
                    packets.append(packet)
                    packet = bytearray()
                packet += RECORD_HEADER.pack(
                    message.content_type,
                    message.record_version,
                    next(self._record_seq),
                    len(message.payload),
                )
                packet += message.payload
                assert len(packet) <= mtu
            else:
                msg_len_bytes = len(message.body).to_bytes(3, "big")
                frag_offset = 0
                frags_encoded = 0
                # If message.body is empty, then we still want to encode it in one
                # fragment, not zero.
                while frag_offset < len(message.body) or not frags_encoded:
                    space = (
                        mtu
                        - len(packet)
                        - RECORD_HEADER.size
                        - HANDSHAKE_MESSAGE_HEADER.size
                    )
                    if space <= 0:
                        packets.append(packet)
                        packet = bytearray()
                        continue
                    frag = message.body[frag_offset : frag_offset + space]
                    frag_offset_bytes = frag_offset.to_bytes(3, "big")
                    frag_len_bytes = len(frag).to_bytes(3, "big")
                    frag_offset += len(frag)

                    packet += RECORD_HEADER.pack(
                        ContentType.handshake,
                        message.record_version,
                        next(self._record_seq),
                        HANDSHAKE_MESSAGE_HEADER.size + len(frag),
                    )

                    packet += HANDSHAKE_MESSAGE_HEADER.pack(
                        message.msg_type,
                        msg_len_bytes,
                        message.msg_seq,
                        frag_offset_bytes,
                        frag_len_bytes,
                    )

                    packet += frag

                    frags_encoded += 1
                    assert len(packet) <= mtu

        if packet:
            packets.append(packet)

        return packets


# This bit requires implementing a bona fide cryptographic protocol, so even though it's
# a simple one let's take a moment to discuss the design.
#
# Our goal is to force new incoming handshakes that claim to be coming from a
# given ip:port to prove that they can also receive packets sent to that
# ip:port. (There's nothing in UDP to stop someone from forging the return
# address, and it's often used for stuff like DoS reflection attacks, where
# an attacker tries to trick us into sending data at some innocent victim.)
# For more details, see:
#
#    https://datatracker.ietf.org/doc/html/rfc6347#section-4.2.1
#
# To do this, when we receive an initial ClientHello, we calculate a magic
# cookie, and send it back as a HelloVerifyRequest. Then the client sends us a
# second ClientHello, this time with the magic cookie included, and after we
# check that this cookie is valid we go ahead and start the handshake proper.
#
# So the magic cookie needs the following properties:
# - No-one can forge it without knowing our secret key
# - It ensures that the ip, port, and ClientHello contents from the response
#   match those in the challenge
# - It expires after a short-ish period (so that if an attacker manages to steal one, it
#   won't be useful for long)
# - It doesn't require storing any peer-specific state on our side
#
# To do that, we take the ip/port/ClientHello data and compute an HMAC of them, using a
# secret key we generate on startup. We also include:
#
# - The current time (using Trio's clock), rounded to the nearest 30 seconds
# - A random salt
#
# Then the cookie is the salt and the HMAC digest concatenated together.
#
# When verifying a cookie, we use the salt + new ip/port/ClientHello data to recompute
# the HMAC digest, for both the current time and the current time minus 30 seconds, and
# if either of them match, we consider the cookie good.
#
# Including the rounded-off time like this means that each cookie is good for at least
# 30 seconds, and possibly as much as 60 seconds.
#
# The salt is probably not necessary -- I'm pretty sure that all it does is make it hard
# for an attacker to figure out when our clock ticks over a 30 second boundary. Which is
# probably pretty harmless? But it's easier to add the salt than to convince myself that
# it's *completely* harmless, so, salt it is.

COOKIE_REFRESH_INTERVAL = 30  # seconds
KEY_BYTES = 32
COOKIE_HASH = "sha256"
SALT_BYTES = 8
# 32 bytes was the maximum cookie length in DTLS 1.0. DTLS 1.2 raised it to 255. I doubt
# there are any DTLS 1.0 implementations still in the wild, but really 32 bytes is
# plenty, and it also gets rid of a confusing warning in Wireshark output.
#
# We truncate the cookie to 32 bytes, of which 8 bytes is salt, so that leaves 24 bytes
# of truncated HMAC = 192 bit security, which is still massive overkill. (TCP uses 32
# *bits* for this.) HMAC truncation is explicitly noted as safe in RFC 2104:
#   https://datatracker.ietf.org/doc/html/rfc2104#section-5
COOKIE_LENGTH = 32


def _current_cookie_tick() -> int:
    return int(trio.current_time() / COOKIE_REFRESH_INTERVAL)


# Simple deterministic and invertible serializer -- i.e., a useful tool for converting
# structured data into something we can cryptographically sign.
def _signable(*fields: bytes) -> bytes:
    out = []
    for field in fields:
        out.append(struct.pack("!Q", len(field)))
        out.append(field)
    return b"".join(out)


def _make_cookie(
    key: bytes, salt: bytes, tick: int, address: Any, client_hello_bits: bytes
) -> bytes:
    assert len(salt) == SALT_BYTES
    assert len(key) == KEY_BYTES

    signable_data = _signable(
        salt,
        struct.pack("!Q", tick),
        # address is a mix of strings and ints, and variable length, so pack
        # it into a single nested field
        _signable(*(str(part).encode() for part in address)),
        client_hello_bits,
    )

    return (salt + hmac.digest(key, signable_data, COOKIE_HASH))[:COOKIE_LENGTH]


def valid_cookie(
    key: bytes, cookie: bytes, address: Any, client_hello_bits: bytes
) -> bool:
    if len(cookie) > SALT_BYTES:
        salt = cookie[:SALT_BYTES]

        tick = _current_cookie_tick()

        cur_cookie = _make_cookie(key, salt, tick, address, client_hello_bits)
        old_cookie = _make_cookie(
            key, salt, max(tick - 1, 0), address, client_hello_bits
        )

        # I doubt using a short-circuiting 'or' here would leak any meaningful
        # information, but why risk it when '|' is just as easy.
        return hmac.compare_digest(cookie, cur_cookie) | hmac.compare_digest(
            cookie, old_cookie
        )
    else:
        return False


def challenge_for(
    key: bytes, address: Any, epoch_seqno: int, client_hello_bits: bytes
) -> bytes:
    salt = os.urandom(SALT_BYTES)
    tick = _current_cookie_tick()
    cookie = _make_cookie(key, salt, tick, address, client_hello_bits)

    # HelloVerifyRequest body is:
    # - 2 bytes version
    # - length-prefixed cookie
    #
    # The DTLS 1.2 spec says that for this message specifically we should use
    # the DTLS 1.0 version.
    #
    # (It also says the opposite of that, but that part is a mistake:
    #    https://www.rfc-editor.org/errata/eid4103
    # ).
    #
    # And I guess we use this for both the message-level and record-level
    # ProtocolVersions, since we haven't negotiated anything else yet?
    body = ProtocolVersion.DTLS10 + bytes([len(cookie)]) + cookie

    # RFC says have to copy the client's record number
    # Errata says it should be handshake message number
    # Openssl copies back record sequence number, and always sets message seq
    # number 0. So I guess we'll follow openssl.
    hs = HandshakeFragment(
        msg_type=HandshakeType.hello_verify_request,
        msg_len=len(body),
        msg_seq=0,
        frag_offset=0,
        frag_len=len(body),
        frag=body,
    )
    payload = encode_handshake_fragment(hs)

    packet = encode_record(
        Record(ContentType.handshake, ProtocolVersion.DTLS10, epoch_seqno, payload)
    )
    return packet


_T = TypeVar("_T")


class _Queue(Generic[_T]):
    def __init__(self, incoming_packets_buffer: int | float):  # noqa: PYI041
        self.s, self.r = trio.open_memory_channel[_T](incoming_packets_buffer)


def _read_loop(read_fn: Callable[[int], bytes]) -> bytes:
    chunks = []
    while True:
        try:
            chunk = read_fn(2**14)  # max TLS record size
        except SSL.WantReadError:
            break
        chunks.append(chunk)
    return b"".join(chunks)


async def handle_client_hello_untrusted(
    endpoint: DTLSEndpoint, address: Any, packet: bytes
) -> None:
    # it's trivial to write a simple function that directly calls this to
    # get code coverage, but it should maybe:
    # 1. be removed
    # 2. be asserted
    # 3. Write a complicated test case where this happens "organically"
    if endpoint._listening_context is None:  # pragma: no cover
        return

    try:
        epoch_seqno, cookie, bits = decode_client_hello_untrusted(packet)
    except BadPacket:
        return

    if endpoint._listening_key is None:
        endpoint._listening_key = os.urandom(KEY_BYTES)

    if not valid_cookie(endpoint._listening_key, cookie, address, bits):
        challenge_packet = challenge_for(
            endpoint._listening_key, address, epoch_seqno, bits
        )
        try:
            async with endpoint._send_lock:
                await endpoint.socket.sendto(challenge_packet, address)
        except (OSError, trio.ClosedResourceError):
            pass
    else:
        # We got a real, valid ClientHello!
        stream = DTLSChannel._create(endpoint, address, endpoint._listening_context)
        # Our HelloRetryRequest had some sequence number. We need our future sequence
        # numbers to be larger than it, so our peer knows that our future records aren't
        # stale/duplicates. But, we don't know what this sequence number was. What we do
        # know is:
        # - the HelloRetryRequest seqno was copied it from the initial ClientHello
        # - the new ClientHello has a higher seqno than the initial ClientHello
        # So, if we copy the new ClientHello's seqno into our first real handshake
        # record and increment from there, that should work.
        stream._record_encoder.set_first_record_number(epoch_seqno)
        # Process the ClientHello
        try:
            stream._ssl.bio_write(packet)
            stream._ssl.DTLSv1_listen()
        except SSL.Error:  # pragma: no cover
            # ...OpenSSL didn't like it, so I guess we didn't have a valid ClientHello
            # after all.
            return

        # Some old versions of OpenSSL have a bug with memory BIOs, where DTLSv1_listen
        # consumes the ClientHello out of the BIO, but then do_handshake expects the
        # ClientHello to still be in there (but not the one that ships with Ubuntu
        # 20.04). In particular, this is known to affect the OpenSSL v1.1.1 that ships
        # with Ubuntu 18.04. To work around this, we deliver a second copy of the
        # ClientHello after DTLSv1_listen has completed. This is safe to do
        # unconditionally, because on newer versions of OpenSSL, the second ClientHello
        # is treated as a duplicate packet, which is a normal thing that can happen over
        # UDP. For more details, see:
        #
        #     https://github.com/pyca/pyopenssl/blob/e84e7b57d1838de70ab7a27089fbee78ce0d2106/tests/test_ssl.py#L4226-L4293
        #
        # This was fixed in v1.1.1a, and all later versions. So maybe in 2024 or so we
        # can delete this. The fix landed in OpenSSL master as 079ef6bd534d2, and then
        # was backported to the 1.1.1 branch as d1bfd8076e28.
        stream._ssl.bio_write(packet)

        # Check if we have an existing association
        old_stream = endpoint._streams.get(address)
        if old_stream is not None:
            if old_stream._client_hello == (cookie, bits):
                # ...This was just a duplicate of the last ClientHello, so never mind.
                return
            else:
                # Ok, this *really is* a new handshake; the old stream should go away.
                old_stream._set_replaced()
        stream._client_hello = (cookie, bits)
        endpoint._streams[address] = stream
        endpoint._incoming_connections_q.s.send_nowait(stream)


async def dtls_receive_loop(
    endpoint_ref: ReferenceType[DTLSEndpoint], sock: SocketType
) -> None:
    try:
        while True:
            try:
                packet, address = await sock.recvfrom(MAX_UDP_PACKET_SIZE)
            except OSError as exc:
                if exc.errno == errno.ECONNRESET:
                    # Windows only: "On a UDP-datagram socket [ECONNRESET]
                    # indicates a previous send operation resulted in an ICMP Port
                    # Unreachable message" -- https://docs.microsoft.com/en-us/windows/win32/api/winsock/nf-winsock-recvfrom
                    #
                    # This is totally useless -- there's nothing we can do with this
                    # information. So we just ignore it and retry the recv.
                    continue
                else:
                    raise
            endpoint = endpoint_ref()
            try:
                if endpoint is None:
                    return
                if is_client_hello_untrusted(packet):
                    await handle_client_hello_untrusted(endpoint, address, packet)
                elif address in endpoint._streams:
                    stream = endpoint._streams[address]
                    if stream._did_handshake and part_of_handshake_untrusted(packet):
                        # The peer just sent us more handshake messages, that aren't a
                        # ClientHello, and we thought the handshake was done. Some of
                        # the packets that we sent to finish the handshake must have
                        # gotten lost. So re-send them. We do this directly here instead
                        # of just putting it into the queue and letting the receiver do
                        # it, because there's no guarantee that anyone is reading from
                        # the queue, because we think the handshake is done!
                        await stream._resend_final_volley()
                    else:
                        try:
                            # mypy for some reason cannot determine type of _q
                            stream._q.s.send_nowait(packet)  # type:ignore[has-type]
                        except trio.WouldBlock:
                            stream._packets_dropped_in_trio += 1
                else:
                    # Drop packet
                    pass
            finally:
                del endpoint
    except trio.ClosedResourceError:
        # socket was closed
        return
    except OSError as exc:
        if exc.errno in (errno.EBADF, errno.ENOTSOCK):
            # socket was closed
            return
        else:  # pragma: no cover
            # ??? shouldn't happen
            raise


@attrs.frozen
class DTLSChannelStatistics:
    """Currently this has only one attribute:

    - ``incoming_packets_dropped_in_trio`` (``int``): Gives a count of the number of
      incoming packets from this peer that Trio successfully received from the
      network, but then got dropped because the internal channel buffer was full. If
      this is non-zero, then you might want to call ``receive`` more often, or use a
      larger ``incoming_packets_buffer``, or just not worry about it because your
      UDP-based protocol should be able to handle the occasional lost packet, right?

    """

    incoming_packets_dropped_in_trio: int


@final
class DTLSChannel(trio.abc.Channel[bytes], metaclass=NoPublicConstructor):
    """A DTLS connection.

    This class has no public constructor – you get instances by calling
    `DTLSEndpoint.serve` or `~DTLSEndpoint.connect`.

    .. attribute:: endpoint

       The `DTLSEndpoint` that this connection is using.

    .. attribute:: peer_address

       The IP/port of the remote peer that this connection is associated with.

    """

    def __init__(
        self,
        endpoint: DTLSEndpoint,
        peer_address: Any,
        ctx: SSL.Context,
    ) -> None:
        self.endpoint = endpoint
        self.peer_address = peer_address
        self._packets_dropped_in_trio = 0
        self._client_hello = None
        self._did_handshake = False
        # These are mandatory for all DTLS connections. OP_NO_QUERY_MTU is required to
        # stop openssl from trying to query the memory BIO's MTU and then breaking, and
        # OP_NO_RENEGOTIATION disables renegotiation, which is too complex for us to
        # support and isn't useful anyway -- especially for DTLS where it's equivalent
        # to just performing a new handshake.
        ctx.set_options(
            SSL.OP_NO_QUERY_MTU | SSL.OP_NO_RENEGOTIATION  # type: ignore[attr-defined]
        )
        self._ssl = SSL.Connection(ctx)
        self._handshake_mtu = 0
        # This calls self._ssl.set_ciphertext_mtu, which is important, because if you
        # don't call it then openssl doesn't work.
        self.set_ciphertext_mtu(best_guess_mtu(self.endpoint.socket))
        self._replaced = False
        self._closed = False
        self._q = _Queue[bytes](endpoint.incoming_packets_buffer)
        self._handshake_lock = trio.Lock()
        self._record_encoder: RecordEncoder = RecordEncoder()

        self._final_volley: list[_AnyHandshakeMessage] = []

    def _set_replaced(self) -> None:
        self._replaced = True
        # Any packets we already received could maybe possibly still be processed, but
        # there are no more coming. So we close this on the sender side.
        self._q.s.close()

    def _check_replaced(self) -> None:
        if self._replaced:
            raise trio.BrokenResourceError(
                "peer tore down this connection to start a new one"
            )

    # XX on systems where we can (maybe just Linux?) take advantage of the kernel's PMTU
    # estimate

    # XX should we send close-notify when closing? It seems particularly pointless for
    # DTLS where packets are all independent and can be lost anyway. We do at least need
    # to handle receiving it properly though, which might be easier if we send it...

    def close(self) -> None:
        """Close this connection.

        `DTLSChannel`\\s don't actually own any OS-level resources – the
        socket is owned by the `DTLSEndpoint`, not the individual connections. So
        you don't really *have* to call this. But it will interrupt any other tasks
        calling `receive` with a `ClosedResourceError`, and cause future attempts to use
        this connection to fail.

        You can also use this object as a synchronous or asynchronous context manager.

        """
        if self._closed:
            return
        self._closed = True
        if self.endpoint._streams.get(self.peer_address) is self:
            del self.endpoint._streams[self.peer_address]
        # Will wake any tasks waiting on self._q.get with a
        # ClosedResourceError
        self._q.r.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return self.close()

    async def aclose(self) -> None:
        """Close this connection, but asynchronously.

        This is included to satisfy the `trio.abc.Channel` contract. It's
        identical to `close`, but async.

        """
        self.close()
        await trio.lowlevel.checkpoint()

    async def _send_volley(self, volley_messages: list[_AnyHandshakeMessage]) -> None:
        packets = self._record_encoder.encode_volley(
            volley_messages, self._handshake_mtu
        )
        for packet in packets:
            async with self.endpoint._send_lock:
                await self.endpoint.socket.sendto(packet, self.peer_address)

    async def _resend_final_volley(self) -> None:
        await self._send_volley(self._final_volley)

    async def do_handshake(self, *, initial_retransmit_timeout: float = 1.0) -> None:
        """Perform the handshake.

        Calling this is optional – if you don't, then it will be automatically called
        the first time you call `send` or `receive`. But calling it explicitly can be
        useful in case you want to control the retransmit timeout, use a cancel scope to
        place an overall timeout on the handshake, or catch errors from the handshake
        specifically.

        It's safe to call this multiple times, or call it simultaneously from multiple
        tasks – the first call will perform the handshake, and the rest will be no-ops.

        Args:

          initial_retransmit_timeout (float): Since UDP is an unreliable protocol, it's
            possible that some of the packets we send during the handshake will get
            lost. To handle this, DTLS uses a timer to automatically retransmit
            handshake packets that don't receive a response. This lets you set the
            timeout we use to detect packet loss. Ideally, it should be set to ~1.5
            times the round-trip time to your peer, but 1 second is a reasonable
            default. There's `some useful guidance here
            <https://tlswg.org/dtls13-spec/draft-ietf-tls-dtls13.html#name-timer-values>`__.

            This is the *initial* timeout, because if packets keep being lost then Trio
            will automatically back off to longer values, to avoid overloading the
            network.

        """
        async with self._handshake_lock:
            if self._did_handshake:
                return

            timeout = initial_retransmit_timeout
            volley_messages: list[_AnyHandshakeMessage] = []
            volley_failed_sends = 0

            def read_volley() -> list[_AnyHandshakeMessage]:
                volley_bytes = _read_loop(self._ssl.bio_read)
                new_volley_messages = decode_volley_trusted(volley_bytes)
                if (
                    new_volley_messages
                    and volley_messages
                    and isinstance(new_volley_messages[0], HandshakeMessage)
                    and isinstance(volley_messages[0], HandshakeMessage)
                    and new_volley_messages[0].msg_seq == volley_messages[0].msg_seq
                ):
                    # openssl decided to retransmit; discard because we handle
                    # retransmits ourselves
                    return []
                else:
                    return new_volley_messages

            # If we're a client, we send the initial volley. If we're a server, then
            # the initial ClientHello has already been inserted into self._ssl's
            # read BIO. So either way, we start by generating a new volley.
            with contextlib.suppress(SSL.WantReadError):
                self._ssl.do_handshake()
            volley_messages = read_volley()
            # If we don't have messages to send in our initial volley, then something
            # has gone very wrong. (I'm not sure this can actually happen without an
            # error from OpenSSL, but we check just in case.)
            if not volley_messages:  # pragma: no cover
                raise SSL.Error("something wrong with peer's ClientHello")

            while True:
                # -- at this point, we need to either send or re-send a volley --
                assert volley_messages
                self._check_replaced()
                await self._send_volley(volley_messages)
                # -- then this is where we wait for a reply --
                self.endpoint._ensure_receive_loop()
                with trio.move_on_after(timeout) as cscope:
                    async for packet in self._q.r:
                        self._ssl.bio_write(packet)
                        try:
                            self._ssl.do_handshake()
                        # We ignore generic SSL.Error here, because you can get those
                        # from random invalid packets
                        except (SSL.WantReadError, SSL.Error):
                            pass
                        else:
                            # No exception -> the handshake is done, and we can
                            # switch into data transfer mode.
                            self._did_handshake = True
                            # Might be empty, but that's ok -- we'll just send no
                            # packets.
                            self._final_volley = read_volley()
                            await self._send_volley(self._final_volley)
                            return
                        maybe_volley = read_volley()
                        if maybe_volley:
                            if (
                                isinstance(maybe_volley[0], PseudoHandshakeMessage)
                                and maybe_volley[0].content_type == ContentType.alert
                            ):
                                # we're sending an alert (e.g. due to a corrupted
                                # packet). We want to send it once, but don't save it to
                                # retransmit -- keep the last volley as the current
                                # volley.
                                await self._send_volley(maybe_volley)
                            else:
                                # We managed to get all of the peer's volley and
                                # generate a new one ourselves! break out of the 'for'
                                # loop and restart the timer.
                                volley_messages = maybe_volley
                                # "Implementations SHOULD retain the current timer value
                                # until a transmission without loss occurs, at which
                                # time the value may be reset to the initial value."
                                if volley_failed_sends == 0:
                                    timeout = initial_retransmit_timeout
                                volley_failed_sends = 0
                                break
                    else:
                        assert self._replaced
                        self._check_replaced()
                if cscope.cancelled_caught:
                    # Timeout expired. Double timeout for backoff, with a limit of 60
                    # seconds (this matches what openssl does, and also the
                    # recommendation in draft-ietf-tls-dtls13).
                    timeout = min(2 * timeout, 60.0)
                    volley_failed_sends += 1
                    if volley_failed_sends == 2:
                        # We tried sending this twice and they both failed. Maybe our
                        # PMTU estimate is wrong? Let's try dropping it to the minimum
                        # and hope that helps.
                        self._handshake_mtu = min(
                            self._handshake_mtu, worst_case_mtu(self.endpoint.socket)
                        )

    async def send(self, data: bytes) -> None:
        """Send a packet of data, securely."""

        if self._closed:
            raise trio.ClosedResourceError
        if not data:
            raise ValueError("openssl doesn't support sending empty DTLS packets")
        if not self._did_handshake:
            await self.do_handshake()
        self._check_replaced()
        self._ssl.write(data)
        async with self.endpoint._send_lock:
            await self.endpoint.socket.sendto(
                _read_loop(self._ssl.bio_read), self.peer_address
            )

    async def receive(self) -> bytes:
        """Fetch the next packet of data from this connection's peer, waiting if
        necessary.

        This is safe to call from multiple tasks simultaneously, in case you have some
        reason to do that. And more importantly, it's cancellation-safe, meaning that
        cancelling a call to `receive` will never cause a packet to be lost or corrupt
        the underlying connection.

        """
        if not self._did_handshake:
            await self.do_handshake()
        # If the packet isn't really valid, then openssl can decode it to the empty
        # string (e.g. b/c it's a late-arriving handshake packet, or a duplicate copy of
        # a data packet). Skip over these instead of returning them.
        while True:
            try:
                packet = await self._q.r.receive()
            except trio.EndOfChannel:
                assert self._replaced
                self._check_replaced()
            self._ssl.bio_write(packet)
            cleartext = _read_loop(self._ssl.read)
            if cleartext:
                return cleartext

    def set_ciphertext_mtu(self, new_mtu: int) -> None:
        """Tells Trio the `largest amount of data that can be sent in a single packet to
        this peer <https://en.wikipedia.org/wiki/Maximum_transmission_unit>`__.

        Trio doesn't actually enforce this limit – if you pass a huge packet to `send`,
        then we'll dutifully encrypt it and attempt to send it. But calling this method
        does have two useful effects:

        - If called before the handshake is performed, then Trio will automatically
          fragment handshake messages to fit within the given MTU. It also might
          fragment them even smaller, if it detects signs of packet loss, so setting
          this should never be necessary to make a successful connection. But, the
          packet loss detection only happens after multiple timeouts have expired, so if
          you have reason to believe that a smaller MTU is required, then you can set
          this to skip those timeouts and establish the connection more quickly.

        - It changes the value returned from `get_cleartext_mtu`. So if you have some
          kind of estimate of the network-level MTU, then you can use this to figure out
          how much overhead DTLS will need for hashes/padding/etc., and how much space
          you have left for your application data.

        The MTU here is measuring the largest UDP *payload* you think can be sent, the
        amount of encrypted data that can be handed to the operating system in a single
        call to `send`. It should *not* include IP/UDP headers. Note that OS estimates
        of the MTU often are link-layer MTUs, so you have to subtract off 28 bytes on
        IPv4 and 48 bytes on IPv6 to get the ciphertext MTU.

        By default, Trio assumes an MTU of 1472 bytes on IPv4, and 1452 bytes on IPv6,
        which correspond to the common Ethernet MTU of 1500 bytes after accounting for
        IP/UDP overhead.

        """
        self._handshake_mtu = new_mtu
        self._ssl.set_ciphertext_mtu(new_mtu)

    def get_cleartext_mtu(self) -> int:
        """Returns the largest number of bytes that you can pass in a single call to
        `send` while still fitting within the network-level MTU.

        See `set_ciphertext_mtu` for more details.

        """
        if not self._did_handshake:
            raise trio.NeedHandshakeError
        return self._ssl.get_cleartext_mtu()  # type: ignore[no-any-return]

    def statistics(self) -> DTLSChannelStatistics:
        """Returns a `DTLSChannelStatistics` object with statistics about this connection."""
        return DTLSChannelStatistics(self._packets_dropped_in_trio)


@final
class DTLSEndpoint:
    """A DTLS endpoint.

    A single UDP socket can handle arbitrarily many DTLS connections simultaneously,
    acting as a client or server as needed. A `DTLSEndpoint` object holds a UDP socket
    and manages these connections, which are represented as `DTLSChannel` objects.

    Args:
      socket: (trio.socket.SocketType): A ``SOCK_DGRAM`` socket. If you want to accept
        incoming connections in server mode, then you should probably bind the socket to
        some known port.
      incoming_packets_buffer (int): Each `DTLSChannel` using this socket has its own
        buffer that holds incoming packets until you call `~DTLSChannel.receive` to read
        them. This lets you adjust the size of this buffer. `~DTLSChannel.statistics`
        lets you check if the buffer has overflowed.

    .. attribute:: socket
                   incoming_packets_buffer

       Both constructor arguments are also exposed as attributes, in case you need to
       access them later.

    """

    def __init__(
        self,
        socket: SocketType,
        *,
        incoming_packets_buffer: int = 10,
    ) -> None:
        # We do this lazily on first construction, so only people who actually use DTLS
        # have to install PyOpenSSL.
        global SSL
        from OpenSSL import SSL

        # for __del__, in case the next line raises
        self._initialized: bool = False
        if socket.type != trio.socket.SOCK_DGRAM:
            raise ValueError("DTLS requires a SOCK_DGRAM socket")
        self._initialized = True
        self.socket: SocketType = socket

        self.incoming_packets_buffer = incoming_packets_buffer
        self._token = trio.lowlevel.current_trio_token()
        # We don't need to track handshaking vs non-handshake connections
        # separately. We only keep one connection per remote address; as soon
        # as a peer provides a valid cookie, we can immediately tear down the
        # old connection.
        # {remote address: DTLSChannel}
        self._streams: WeakValueDictionary[Any, DTLSChannel] = WeakValueDictionary()
        self._listening_context: SSL.Context | None = None
        self._listening_key: bytes | None = None
        self._incoming_connections_q = _Queue[DTLSChannel](float("inf"))
        self._send_lock = trio.Lock()
        self._closed = False
        self._receive_loop_spawned = False

    def _ensure_receive_loop(self) -> None:
        # We have to spawn this lazily, because on Windows it will immediately error out
        # if the socket isn't already bound -- which for clients might not happen until
        # after we send our first packet.
        if not self._receive_loop_spawned:
            trio.lowlevel.spawn_system_task(
                dtls_receive_loop, weakref.ref(self), self.socket
            )
            self._receive_loop_spawned = True

    def __del__(self) -> None:
        # Do nothing if this object was never fully constructed
        if not self._initialized:
            return
        # Close the socket in Trio context (if our Trio context still exists), so that
        # the background task gets notified about the closure and can exit.
        if not self._closed:
            with contextlib.suppress(RuntimeError):
                self._token.run_sync_soon(self.close)
            # Do this last, because it might raise an exception
            warnings.warn(
                f"unclosed DTLS endpoint {self!r}",
                ResourceWarning,
                source=self,
                stacklevel=1,
            )

    def close(self) -> None:
        """Close this socket, and all associated DTLS connections.

        This object can also be used as a context manager.

        """
        self._closed = True
        self.socket.close()
        for stream in list(self._streams.values()):
            stream.close()
        self._incoming_connections_q.s.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return self.close()

    def _check_closed(self) -> None:
        if self._closed:
            raise trio.ClosedResourceError

    async def serve(
        self,
        ssl_context: SSL.Context,
        async_fn: Callable[[DTLSChannel, Unpack[PosArgsT]], Awaitable[object]],
        *args: Unpack[PosArgsT],
        task_status: trio.TaskStatus[None] = trio.TASK_STATUS_IGNORED,
    ) -> None:
        """Listen for incoming connections, and spawn a handler for each using an
        internal nursery.

        Similar to `~trio.serve_tcp`, this function never returns until cancelled, or
        the `DTLSEndpoint` is closed and all handlers have exited.

        Usage commonly looks like::

            async def handler(dtls_channel):
                ...

            async with trio.open_nursery() as nursery:
                await nursery.start(dtls_endpoint.serve, ssl_context, handler)
                # ... do other things here ...

        The ``dtls_channel`` passed into the handler function has already performed the
        "cookie exchange" part of the DTLS handshake, so the peer address is
        trustworthy. But the actual cryptographic handshake doesn't happen until you
        start using it, giving you a chance for any last minute configuration, and the
        option to catch and handle handshake errors.

        Args:
          ssl_context (OpenSSL.SSL.Context): The PyOpenSSL context object to use for
            incoming connections.
          async_fn: The handler function that will be invoked for each incoming
            connection.
          *args: Additional arguments to pass to the handler function.

        """
        self._check_closed()
        if self._listening_context is not None:
            raise trio.BusyResourceError("another task is already listening")
        try:
            self.socket.getsockname()
        except OSError:
            # TODO: Write test that triggers this
            raise RuntimeError(  # pragma: no cover
                "DTLS socket must be bound before it can serve"
            ) from None
        self._ensure_receive_loop()
        # We do cookie verification ourselves, so tell OpenSSL not to worry about it.
        # (See also _inject_client_hello_untrusted.)
        ssl_context.set_cookie_verify_callback(lambda *_: True)
        try:
            self._listening_context = ssl_context
            task_status.started()

            async def handler_wrapper(stream: DTLSChannel) -> None:
                with stream:
                    await async_fn(stream, *args)

            async with trio.open_nursery() as nursery:
                async for stream in self._incoming_connections_q.r:  # pragma: no branch
                    nursery.start_soon(handler_wrapper, stream)
        finally:
            self._listening_context = None

    def connect(
        self,
        address: tuple[str, int],
        ssl_context: SSL.Context,
    ) -> DTLSChannel:
        """Initiate an outgoing DTLS connection.

        Notice that this is a synchronous method. That's because it doesn't actually
        initiate any I/O – it just sets up a `DTLSChannel` object. The actual handshake
        doesn't occur until you start using the `DTLSChannel`. This gives you a chance
        to do further configuration first, like setting MTU etc.

        Args:
          address: The address to connect to. Usually a (host, port) tuple, like
            ``("127.0.0.1", 12345)``.
          ssl_context (OpenSSL.SSL.Context): The PyOpenSSL context object to use for
            this connection.

        Returns:
          DTLSChannel

        """
        # it would be nice if we could detect when 'address' is our own endpoint (a
        # loopback connection), because that can't work
        # but I don't see how to do it reliably
        self._check_closed()
        channel = DTLSChannel._create(self, address, ssl_context)
        channel._ssl.set_connect_state()
        old_channel = self._streams.get(address)
        if old_channel is not None:
            old_channel._set_replaced()
        self._streams[address] = channel
        return channel
