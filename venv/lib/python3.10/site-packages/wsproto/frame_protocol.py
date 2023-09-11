"""
wsproto/frame_protocol
~~~~~~~~~~~~~~~~~~~~~~

WebSocket frame protocol implementation.
"""

import os
import struct
from codecs import getincrementaldecoder, IncrementalDecoder
from enum import IntEnum
from typing import Generator, List, NamedTuple, Optional, Tuple, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from .extensions import Extension  # pragma: no cover


_XOR_TABLE = [bytes(a ^ b for a in range(256)) for b in range(256)]


class XorMaskerSimple:
    def __init__(self, masking_key: bytes) -> None:
        self._masking_key = masking_key

    def process(self, data: bytes) -> bytes:
        if data:
            data_array = bytearray(data)
            a, b, c, d = (_XOR_TABLE[n] for n in self._masking_key)
            data_array[::4] = data_array[::4].translate(a)
            data_array[1::4] = data_array[1::4].translate(b)
            data_array[2::4] = data_array[2::4].translate(c)
            data_array[3::4] = data_array[3::4].translate(d)

            # Rotate the masking key so that the next usage continues
            # with the next key element, rather than restarting.
            key_rotation = len(data) % 4
            self._masking_key = (
                self._masking_key[key_rotation:] + self._masking_key[:key_rotation]
            )

            return bytes(data_array)
        return data


class XorMaskerNull:
    def process(self, data: bytes) -> bytes:
        return data


# RFC6455, Section 5.2 - Base Framing Protocol

# Payload length constants
PAYLOAD_LENGTH_TWO_BYTE = 126
PAYLOAD_LENGTH_EIGHT_BYTE = 127
MAX_PAYLOAD_NORMAL = 125
MAX_PAYLOAD_TWO_BYTE = 2**16 - 1
MAX_PAYLOAD_EIGHT_BYTE = 2**64 - 1
MAX_FRAME_PAYLOAD = MAX_PAYLOAD_EIGHT_BYTE

# MASK and PAYLOAD LEN are packed into a byte
MASK_MASK = 0x80
PAYLOAD_LEN_MASK = 0x7F

# FIN, RSV[123] and OPCODE are packed into a single byte
FIN_MASK = 0x80
RSV1_MASK = 0x40
RSV2_MASK = 0x20
RSV3_MASK = 0x10
OPCODE_MASK = 0x0F


class Opcode(IntEnum):
    """
    RFC 6455, Section 5.2 - Base Framing Protocol
    """

    #: Continuation frame
    CONTINUATION = 0x0

    #: Text message
    TEXT = 0x1

    #: Binary message
    BINARY = 0x2

    #: Close frame
    CLOSE = 0x8

    #: Ping frame
    PING = 0x9

    #: Pong frame
    PONG = 0xA

    def iscontrol(self) -> bool:
        return bool(self & 0x08)


class CloseReason(IntEnum):
    """
    RFC 6455, Section 7.4.1 - Defined Status Codes
    """

    #: indicates a normal closure, meaning that the purpose for
    #: which the connection was established has been fulfilled.
    NORMAL_CLOSURE = 1000

    #: indicates that an endpoint is "going away", such as a server
    #: going down or a browser having navigated away from a page.
    GOING_AWAY = 1001

    #: indicates that an endpoint is terminating the connection due
    #: to a protocol error.
    PROTOCOL_ERROR = 1002

    #: indicates that an endpoint is terminating the connection
    #: because it has received a type of data it cannot accept (e.g., an
    #: endpoint that understands only text data MAY send this if it
    #: receives a binary message).
    UNSUPPORTED_DATA = 1003

    #: Reserved.  The specific meaning might be defined in the future.
    # DON'T DEFINE THIS: RESERVED_1004 = 1004

    #: is a reserved value and MUST NOT be set as a status code in a
    #: Close control frame by an endpoint.  It is designated for use in
    #: applications expecting a status code to indicate that no status
    #: code was actually present.
    NO_STATUS_RCVD = 1005

    #: is a reserved value and MUST NOT be set as a status code in a
    #: Close control frame by an endpoint.  It is designated for use in
    #: applications expecting a status code to indicate that the
    #: connection was closed abnormally, e.g., without sending or
    #: receiving a Close control frame.
    ABNORMAL_CLOSURE = 1006

    #: indicates that an endpoint is terminating the connection
    #: because it has received data within a message that was not
    #: consistent with the type of the message (e.g., non-UTF-8 [RFC3629]
    #: data within a text message).
    INVALID_FRAME_PAYLOAD_DATA = 1007

    #: indicates that an endpoint is terminating the connection
    #: because it has received a message that violates its policy.  This
    #: is a generic status code that can be returned when there is no
    #: other more suitable status code (e.g., 1003 or 1009) or if there
    #: is a need to hide specific details about the policy.
    POLICY_VIOLATION = 1008

    #: indicates that an endpoint is terminating the connection
    #: because it has received a message that is too big for it to
    #: process.
    MESSAGE_TOO_BIG = 1009

    #: indicates that an endpoint (client) is terminating the
    #: connection because it has expected the server to negotiate one or
    #: more extension, but the server didn't return them in the response
    #: message of the WebSocket handshake.  The list of extensions that
    #: are needed SHOULD appear in the /reason/ part of the Close frame.
    #: Note that this status code is not used by the server, because it
    #: can fail the WebSocket handshake instead.
    MANDATORY_EXT = 1010

    #: indicates that a server is terminating the connection because
    #: it encountered an unexpected condition that prevented it from
    #: fulfilling the request.
    INTERNAL_ERROR = 1011

    #: Server/service is restarting
    #: (not part of RFC6455)
    SERVICE_RESTART = 1012

    #: Temporary server condition forced blocking client's request
    #: (not part of RFC6455)
    TRY_AGAIN_LATER = 1013

    #: is a reserved value and MUST NOT be set as a status code in a
    #: Close control frame by an endpoint.  It is designated for use in
    #: applications expecting a status code to indicate that the
    #: connection was closed due to a failure to perform a TLS handshake
    #: (e.g., the server certificate can't be verified).
    TLS_HANDSHAKE_FAILED = 1015


# RFC 6455, Section 7.4.1 - Defined Status Codes
LOCAL_ONLY_CLOSE_REASONS = (
    CloseReason.NO_STATUS_RCVD,
    CloseReason.ABNORMAL_CLOSURE,
    CloseReason.TLS_HANDSHAKE_FAILED,
)


# RFC 6455, Section 7.4.2 - Status Code Ranges
MIN_CLOSE_REASON = 1000
MIN_PROTOCOL_CLOSE_REASON = 1000
MAX_PROTOCOL_CLOSE_REASON = 2999
MIN_LIBRARY_CLOSE_REASON = 3000
MAX_LIBRARY_CLOSE_REASON = 3999
MIN_PRIVATE_CLOSE_REASON = 4000
MAX_PRIVATE_CLOSE_REASON = 4999
MAX_CLOSE_REASON = 4999


NULL_MASK = struct.pack("!I", 0)


class ParseFailed(Exception):
    def __init__(
        self, msg: str, code: CloseReason = CloseReason.PROTOCOL_ERROR
    ) -> None:
        super().__init__(msg)
        self.code = code


class RsvBits(NamedTuple):
    rsv1: bool
    rsv2: bool
    rsv3: bool


class Header(NamedTuple):
    fin: bool
    rsv: RsvBits
    opcode: Opcode
    payload_len: int
    masking_key: Optional[bytes]


class Frame(NamedTuple):
    opcode: Opcode
    payload: Union[bytes, str, Tuple[int, str]]
    frame_finished: bool
    message_finished: bool


def _truncate_utf8(data: bytes, nbytes: int) -> bytes:
    if len(data) <= nbytes:
        return data

    # Truncate
    data = data[:nbytes]
    # But we might have cut a codepoint in half, in which case we want to
    # discard the partial character so the data is at least
    # well-formed. This is a little inefficient since it processes the
    # whole message twice when in theory we could just peek at the last
    # few characters, but since this is only used for close messages (max
    # length = 125 bytes) it really doesn't matter.
    data = data.decode("utf-8", errors="ignore").encode("utf-8")
    return data


class Buffer:
    def __init__(self, initial_bytes: Optional[bytes] = None) -> None:
        self.buffer = bytearray()
        self.bytes_used = 0
        if initial_bytes:
            self.feed(initial_bytes)

    def feed(self, new_bytes: bytes) -> None:
        self.buffer += new_bytes

    def consume_at_most(self, nbytes: int) -> bytes:
        if not nbytes:
            return bytearray()

        data = self.buffer[self.bytes_used : self.bytes_used + nbytes]
        self.bytes_used += len(data)
        return data

    def consume_exactly(self, nbytes: int) -> Optional[bytes]:
        if len(self.buffer) - self.bytes_used < nbytes:
            return None

        return self.consume_at_most(nbytes)

    def commit(self) -> None:
        # In CPython 3.4+, del[:n] is amortized O(n), *not* quadratic
        del self.buffer[: self.bytes_used]
        self.bytes_used = 0

    def rollback(self) -> None:
        self.bytes_used = 0

    def __len__(self) -> int:
        return len(self.buffer)


class MessageDecoder:
    def __init__(self) -> None:
        self.opcode: Optional[Opcode] = None
        self.decoder: Optional[IncrementalDecoder] = None

    def process_frame(self, frame: Frame) -> Frame:
        assert not frame.opcode.iscontrol()

        if self.opcode is None:
            if frame.opcode is Opcode.CONTINUATION:
                raise ParseFailed("unexpected CONTINUATION")
            self.opcode = frame.opcode
        elif frame.opcode is not Opcode.CONTINUATION:
            raise ParseFailed("expected CONTINUATION, got %r" % frame.opcode)

        if frame.opcode is Opcode.TEXT:
            self.decoder = getincrementaldecoder("utf-8")()

        finished = frame.frame_finished and frame.message_finished

        if self.decoder is None:
            data = frame.payload
        else:
            assert isinstance(frame.payload, (bytes, bytearray))
            try:
                data = self.decoder.decode(frame.payload, finished)
            except UnicodeDecodeError as exc:
                raise ParseFailed(str(exc), CloseReason.INVALID_FRAME_PAYLOAD_DATA)

        frame = Frame(self.opcode, data, frame.frame_finished, finished)

        if finished:
            self.opcode = None
            self.decoder = None

        return frame


class FrameDecoder:
    def __init__(
        self, client: bool, extensions: Optional[List["Extension"]] = None
    ) -> None:
        self.client = client
        self.extensions = extensions or []

        self.buffer = Buffer()

        self.header: Optional[Header] = None
        self.effective_opcode: Optional[Opcode] = None
        self.masker: Union[None, XorMaskerNull, XorMaskerSimple] = None
        self.payload_required = 0
        self.payload_consumed = 0

    def receive_bytes(self, data: bytes) -> None:
        self.buffer.feed(data)

    def process_buffer(self) -> Optional[Frame]:
        if not self.header:
            if not self.parse_header():
                return None
        # parse_header() sets these.
        assert self.header is not None
        assert self.masker is not None
        assert self.effective_opcode is not None

        if len(self.buffer) < self.payload_required:
            return None

        payload_remaining = self.header.payload_len - self.payload_consumed
        payload = self.buffer.consume_at_most(payload_remaining)
        if not payload and self.header.payload_len > 0:
            return None
        self.buffer.commit()

        self.payload_consumed += len(payload)
        finished = self.payload_consumed == self.header.payload_len

        payload = self.masker.process(payload)

        for extension in self.extensions:
            payload_ = extension.frame_inbound_payload_data(self, payload)
            if isinstance(payload_, CloseReason):
                raise ParseFailed("error in extension", payload_)
            payload = payload_

        if finished:
            final = bytearray()
            for extension in self.extensions:
                result = extension.frame_inbound_complete(self, self.header.fin)
                if isinstance(result, CloseReason):
                    raise ParseFailed("error in extension", result)
                if result is not None:
                    final += result
            payload += final

        frame = Frame(self.effective_opcode, payload, finished, self.header.fin)

        if finished:
            self.header = None
            self.effective_opcode = None
            self.masker = None
        else:
            self.effective_opcode = Opcode.CONTINUATION

        return frame

    def parse_header(self) -> bool:
        data = self.buffer.consume_exactly(2)
        if data is None:
            self.buffer.rollback()
            return False

        fin = bool(data[0] & FIN_MASK)
        rsv = RsvBits(
            bool(data[0] & RSV1_MASK),
            bool(data[0] & RSV2_MASK),
            bool(data[0] & RSV3_MASK),
        )
        opcode = data[0] & OPCODE_MASK
        try:
            opcode = Opcode(opcode)
        except ValueError:
            raise ParseFailed(f"Invalid opcode {opcode:#x}")

        if opcode.iscontrol() and not fin:
            raise ParseFailed("Invalid attempt to fragment control frame")

        has_mask = bool(data[1] & MASK_MASK)
        payload_len_short = data[1] & PAYLOAD_LEN_MASK
        payload_len = self.parse_extended_payload_length(opcode, payload_len_short)
        if payload_len is None:
            self.buffer.rollback()
            return False

        self.extension_processing(opcode, rsv, payload_len)

        if has_mask and self.client:
            raise ParseFailed("client received unexpected masked frame")
        if not has_mask and not self.client:
            raise ParseFailed("server received unexpected unmasked frame")
        if has_mask:
            masking_key = self.buffer.consume_exactly(4)
            if masking_key is None:
                self.buffer.rollback()
                return False
            self.masker = XorMaskerSimple(masking_key)
        else:
            self.masker = XorMaskerNull()

        self.buffer.commit()
        self.header = Header(fin, rsv, opcode, payload_len, None)
        self.effective_opcode = self.header.opcode
        if self.header.opcode.iscontrol():
            self.payload_required = payload_len
        else:
            self.payload_required = 0
        self.payload_consumed = 0
        return True

    def parse_extended_payload_length(
        self, opcode: Opcode, payload_len: int
    ) -> Optional[int]:
        if opcode.iscontrol() and payload_len > MAX_PAYLOAD_NORMAL:
            raise ParseFailed("Control frame with payload len > 125")
        if payload_len == PAYLOAD_LENGTH_TWO_BYTE:
            data = self.buffer.consume_exactly(2)
            if data is None:
                return None
            (payload_len,) = struct.unpack("!H", data)
            if payload_len <= MAX_PAYLOAD_NORMAL:
                raise ParseFailed(
                    "Payload length used 2 bytes when 1 would have sufficed"
                )
        elif payload_len == PAYLOAD_LENGTH_EIGHT_BYTE:
            data = self.buffer.consume_exactly(8)
            if data is None:
                return None
            (payload_len,) = struct.unpack("!Q", data)
            if payload_len <= MAX_PAYLOAD_TWO_BYTE:
                raise ParseFailed(
                    "Payload length used 8 bytes when 2 would have sufficed"
                )
            if payload_len >> 63:
                # I'm not sure why this is illegal, but that's what the RFC
                # says, so...
                raise ParseFailed("8-byte payload length with non-zero MSB")

        return payload_len

    def extension_processing(
        self, opcode: Opcode, rsv: RsvBits, payload_len: int
    ) -> None:
        rsv_used = [False, False, False]
        for extension in self.extensions:
            result = extension.frame_inbound_header(self, opcode, rsv, payload_len)
            if isinstance(result, CloseReason):
                raise ParseFailed("error in extension", result)
            for bit, used in enumerate(result):
                if used:
                    rsv_used[bit] = True
        for expected, found in zip(rsv_used, rsv):
            if found and not expected:
                raise ParseFailed("Reserved bit set unexpectedly")


class FrameProtocol:
    def __init__(self, client: bool, extensions: List["Extension"]) -> None:
        self.client = client
        self.extensions = [ext for ext in extensions if ext.enabled()]

        # Global state
        self._frame_decoder = FrameDecoder(self.client, self.extensions)
        self._message_decoder = MessageDecoder()
        self._parse_more = self._parse_more_gen()

        self._outbound_opcode: Optional[Opcode] = None

    def _process_close(self, frame: Frame) -> Frame:
        data = frame.payload
        assert isinstance(data, (bytes, bytearray))

        if not data:
            # "If this Close control frame contains no status code, _The
            # WebSocket Connection Close Code_ is considered to be 1005"
            data = (CloseReason.NO_STATUS_RCVD, "")
        elif len(data) == 1:
            raise ParseFailed("CLOSE with 1 byte payload")
        else:
            (code,) = struct.unpack("!H", data[:2])
            if code < MIN_CLOSE_REASON or code > MAX_CLOSE_REASON:
                raise ParseFailed("CLOSE with invalid code")
            try:
                code = CloseReason(code)
            except ValueError:
                pass
            if code in LOCAL_ONLY_CLOSE_REASONS:
                raise ParseFailed("remote CLOSE with local-only reason")
            if not isinstance(code, CloseReason) and code <= MAX_PROTOCOL_CLOSE_REASON:
                raise ParseFailed("CLOSE with unknown reserved code")
            try:
                reason = data[2:].decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ParseFailed(
                    "Error decoding CLOSE reason: " + str(exc),
                    CloseReason.INVALID_FRAME_PAYLOAD_DATA,
                )
            data = (code, reason)

        return Frame(frame.opcode, data, frame.frame_finished, frame.message_finished)

    def _parse_more_gen(self) -> Generator[Optional[Frame], None, None]:
        # Consume as much as we can from self._buffer, yielding events, and
        # then yield None when we need more data. Or raise ParseFailed.

        # XX FIXME this should probably be refactored so that we never see
        # disabled extensions in the first place...
        self.extensions = [ext for ext in self.extensions if ext.enabled()]
        closed = False

        while not closed:
            frame = self._frame_decoder.process_buffer()

            if frame is not None:
                if not frame.opcode.iscontrol():
                    frame = self._message_decoder.process_frame(frame)
                elif frame.opcode == Opcode.CLOSE:
                    frame = self._process_close(frame)
                    closed = True

            yield frame

    def receive_bytes(self, data: bytes) -> None:
        self._frame_decoder.receive_bytes(data)

    def received_frames(self) -> Generator[Frame, None, None]:
        for event in self._parse_more:
            if event is None:
                break
            else:
                yield event

    def close(self, code: Optional[int] = None, reason: Optional[str] = None) -> bytes:
        payload = bytearray()
        if code is CloseReason.NO_STATUS_RCVD:
            code = None
        if code is None and reason:
            raise TypeError("cannot specify a reason without a code")
        if code in LOCAL_ONLY_CLOSE_REASONS:
            code = CloseReason.NORMAL_CLOSURE
        if code is not None:
            payload += bytearray(struct.pack("!H", code))
            if reason is not None:
                payload += _truncate_utf8(
                    reason.encode("utf-8"), MAX_PAYLOAD_NORMAL - 2
                )

        return self._serialize_frame(Opcode.CLOSE, payload)

    def ping(self, payload: bytes = b"") -> bytes:
        return self._serialize_frame(Opcode.PING, payload)

    def pong(self, payload: bytes = b"") -> bytes:
        return self._serialize_frame(Opcode.PONG, payload)

    def send_data(
        self, payload: Union[bytes, bytearray, str] = b"", fin: bool = True
    ) -> bytes:
        if isinstance(payload, (bytes, bytearray, memoryview)):
            opcode = Opcode.BINARY
        elif isinstance(payload, str):
            opcode = Opcode.TEXT
            payload = payload.encode("utf-8")
        else:
            raise ValueError("Must provide bytes or text")

        if self._outbound_opcode is None:
            self._outbound_opcode = opcode
        elif self._outbound_opcode is not opcode:
            raise TypeError("Data type mismatch inside message")
        else:
            opcode = Opcode.CONTINUATION

        if fin:
            self._outbound_opcode = None

        return self._serialize_frame(opcode, payload, fin)

    def _make_fin_rsv_opcode(self, fin: bool, rsv: RsvBits, opcode: Opcode) -> int:
        fin_bits = int(fin) << 7
        rsv_bits = (int(rsv.rsv1) << 6) + (int(rsv.rsv2) << 5) + (int(rsv.rsv3) << 4)
        opcode_bits = int(opcode)

        return fin_bits | rsv_bits | opcode_bits

    def _serialize_frame(
        self, opcode: Opcode, payload: bytes = b"", fin: bool = True
    ) -> bytes:
        rsv = RsvBits(False, False, False)
        for extension in reversed(self.extensions):
            rsv, payload = extension.frame_outbound(self, opcode, rsv, payload, fin)

        fin_rsv_opcode = self._make_fin_rsv_opcode(fin, rsv, opcode)

        payload_length = len(payload)
        quad_payload = False
        if payload_length <= MAX_PAYLOAD_NORMAL:
            first_payload = payload_length
            second_payload = None
        elif payload_length <= MAX_PAYLOAD_TWO_BYTE:
            first_payload = PAYLOAD_LENGTH_TWO_BYTE
            second_payload = payload_length
        else:
            first_payload = PAYLOAD_LENGTH_EIGHT_BYTE
            second_payload = payload_length
            quad_payload = True

        if self.client:
            first_payload |= 1 << 7

        header = bytearray([fin_rsv_opcode, first_payload])
        if second_payload is not None:
            if opcode.iscontrol():
                raise ValueError("payload too long for control frame")
            if quad_payload:
                header += bytearray(struct.pack("!Q", second_payload))
            else:
                header += bytearray(struct.pack("!H", second_payload))

        if self.client:
            # "The masking key is a 32-bit value chosen at random by the
            # client.  When preparing a masked frame, the client MUST pick a
            # fresh masking key from the set of allowed 32-bit values.  The
            # masking key needs to be unpredictable; thus, the masking key
            # MUST be derived from a strong source of entropy, and the masking
            # key for a given frame MUST NOT make it simple for a server/proxy
            # to predict the masking key for a subsequent frame.  The
            # unpredictability of the masking key is essential to prevent
            # authors of malicious applications from selecting the bytes that
            # appear on the wire."
            #   -- https://tools.ietf.org/html/rfc6455#section-5.3
            masking_key = os.urandom(4)
            masker = XorMaskerSimple(masking_key)
            return header + masking_key + masker.process(payload)

        return header + payload
