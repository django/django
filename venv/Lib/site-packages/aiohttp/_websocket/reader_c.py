"""Reader for WebSocket protocol versions 13 and 8."""

import asyncio
import builtins
from collections import deque
from typing import Deque, Final, Optional, Set, Tuple, Union

from ..base_protocol import BaseProtocol
from ..compression_utils import ZLibDecompressor
from ..helpers import _EXC_SENTINEL, set_exception
from ..streams import EofStream
from .helpers import UNPACK_CLOSE_CODE, UNPACK_LEN3, websocket_mask
from .models import (
    WS_DEFLATE_TRAILING,
    WebSocketError,
    WSCloseCode,
    WSMessage,
    WSMsgType,
)

ALLOWED_CLOSE_CODES: Final[Set[int]] = {int(i) for i in WSCloseCode}

# States for the reader, used to parse the WebSocket frame
# integer values are used so they can be cythonized
READ_HEADER = 1
READ_PAYLOAD_LENGTH = 2
READ_PAYLOAD_MASK = 3
READ_PAYLOAD = 4

WS_MSG_TYPE_BINARY = WSMsgType.BINARY
WS_MSG_TYPE_TEXT = WSMsgType.TEXT

# WSMsgType values unpacked so they can by cythonized to ints
OP_CODE_NOT_SET = -1
OP_CODE_CONTINUATION = WSMsgType.CONTINUATION.value
OP_CODE_TEXT = WSMsgType.TEXT.value
OP_CODE_BINARY = WSMsgType.BINARY.value
OP_CODE_CLOSE = WSMsgType.CLOSE.value
OP_CODE_PING = WSMsgType.PING.value
OP_CODE_PONG = WSMsgType.PONG.value

EMPTY_FRAME_ERROR = (True, b"")
EMPTY_FRAME = (False, b"")

COMPRESSED_NOT_SET = -1
COMPRESSED_FALSE = 0
COMPRESSED_TRUE = 1

TUPLE_NEW = tuple.__new__

cython_int = int  # Typed to int in Python, but cython with use a signed int in the pxd


class WebSocketDataQueue:
    """WebSocketDataQueue resumes and pauses an underlying stream.

    It is a destination for WebSocket data.
    """

    def __init__(
        self, protocol: BaseProtocol, limit: int, *, loop: asyncio.AbstractEventLoop
    ) -> None:
        self._size = 0
        self._protocol = protocol
        self._limit = limit * 2
        self._loop = loop
        self._eof = False
        self._waiter: Optional[asyncio.Future[None]] = None
        self._exception: Union[BaseException, None] = None
        self._buffer: Deque[Tuple[WSMessage, int]] = deque()
        self._get_buffer = self._buffer.popleft
        self._put_buffer = self._buffer.append

    def is_eof(self) -> bool:
        return self._eof

    def exception(self) -> Optional[BaseException]:
        return self._exception

    def set_exception(
        self,
        exc: BaseException,
        exc_cause: builtins.BaseException = _EXC_SENTINEL,
    ) -> None:
        self._eof = True
        self._exception = exc
        if (waiter := self._waiter) is not None:
            self._waiter = None
            set_exception(waiter, exc, exc_cause)

    def _release_waiter(self) -> None:
        if (waiter := self._waiter) is None:
            return
        self._waiter = None
        if not waiter.done():
            waiter.set_result(None)

    def feed_eof(self) -> None:
        self._eof = True
        self._release_waiter()
        self._exception = None  # Break cyclic references

    def feed_data(self, data: "WSMessage", size: "cython_int") -> None:
        self._size += size
        self._put_buffer((data, size))
        self._release_waiter()
        if self._size > self._limit and not self._protocol._reading_paused:
            self._protocol.pause_reading()

    async def read(self) -> WSMessage:
        if not self._buffer and not self._eof:
            assert not self._waiter
            self._waiter = self._loop.create_future()
            try:
                await self._waiter
            except (asyncio.CancelledError, asyncio.TimeoutError):
                self._waiter = None
                raise
        return self._read_from_buffer()

    def _read_from_buffer(self) -> WSMessage:
        if self._buffer:
            data, size = self._get_buffer()
            self._size -= size
            if self._size < self._limit and self._protocol._reading_paused:
                self._protocol.resume_reading()
            return data
        if self._exception is not None:
            raise self._exception
        raise EofStream


class WebSocketReader:
    def __init__(
        self, queue: WebSocketDataQueue, max_msg_size: int, compress: bool = True
    ) -> None:
        self.queue = queue
        self._max_msg_size = max_msg_size

        self._exc: Optional[Exception] = None
        self._partial = bytearray()
        self._state = READ_HEADER

        self._opcode: int = OP_CODE_NOT_SET
        self._frame_fin = False
        self._frame_opcode: int = OP_CODE_NOT_SET
        self._payload_fragments: list[bytes] = []
        self._frame_payload_len = 0

        self._tail: bytes = b""
        self._has_mask = False
        self._frame_mask: Optional[bytes] = None
        self._payload_bytes_to_read = 0
        self._payload_len_flag = 0
        self._compressed: int = COMPRESSED_NOT_SET
        self._decompressobj: Optional[ZLibDecompressor] = None
        self._compress = compress

    def feed_eof(self) -> None:
        self.queue.feed_eof()

    # data can be bytearray on Windows because proactor event loop uses bytearray
    # and asyncio types this to Union[bytes, bytearray, memoryview] so we need
    # coerce data to bytes if it is not
    def feed_data(
        self, data: Union[bytes, bytearray, memoryview]
    ) -> Tuple[bool, bytes]:
        if type(data) is not bytes:
            data = bytes(data)

        if self._exc is not None:
            return True, data

        try:
            self._feed_data(data)
        except Exception as exc:
            self._exc = exc
            set_exception(self.queue, exc)
            return EMPTY_FRAME_ERROR

        return EMPTY_FRAME

    def _handle_frame(
        self,
        fin: bool,
        opcode: Union[int, cython_int],  # Union intended: Cython pxd uses C int
        payload: Union[bytes, bytearray],
        compressed: Union[int, cython_int],  # Union intended: Cython pxd uses C int
    ) -> None:
        msg: WSMessage
        if opcode in {OP_CODE_TEXT, OP_CODE_BINARY, OP_CODE_CONTINUATION}:
            # Validate continuation frames before processing
            if opcode == OP_CODE_CONTINUATION and self._opcode == OP_CODE_NOT_SET:
                raise WebSocketError(
                    WSCloseCode.PROTOCOL_ERROR,
                    "Continuation frame for non started message",
                )

            # load text/binary
            if not fin:
                # got partial frame payload
                if opcode != OP_CODE_CONTINUATION:
                    self._opcode = opcode
                self._partial += payload
                if self._max_msg_size and len(self._partial) >= self._max_msg_size:
                    raise WebSocketError(
                        WSCloseCode.MESSAGE_TOO_BIG,
                        f"Message size {len(self._partial)} "
                        f"exceeds limit {self._max_msg_size}",
                    )
                return

            has_partial = bool(self._partial)
            if opcode == OP_CODE_CONTINUATION:
                opcode = self._opcode
                self._opcode = OP_CODE_NOT_SET
            # previous frame was non finished
            # we should get continuation opcode
            elif has_partial:
                raise WebSocketError(
                    WSCloseCode.PROTOCOL_ERROR,
                    "The opcode in non-fin frame is expected "
                    f"to be zero, got {opcode!r}",
                )

            assembled_payload: Union[bytes, bytearray]
            if has_partial:
                assembled_payload = self._partial + payload
                self._partial.clear()
            else:
                assembled_payload = payload

            if self._max_msg_size and len(assembled_payload) >= self._max_msg_size:
                raise WebSocketError(
                    WSCloseCode.MESSAGE_TOO_BIG,
                    f"Message size {len(assembled_payload)} "
                    f"exceeds limit {self._max_msg_size}",
                )

            # Decompress process must to be done after all packets
            # received.
            if compressed:
                if not self._decompressobj:
                    self._decompressobj = ZLibDecompressor(suppress_deflate_header=True)
                # XXX: It's possible that the zlib backend (isal is known to
                # do this, maybe others too?) will return max_length bytes,
                # but internally buffer more data such that the payload is
                # >max_length, so we return one extra byte and if we're able
                # to do that, then the message is too big.
                payload_merged = self._decompressobj.decompress_sync(
                    assembled_payload + WS_DEFLATE_TRAILING,
                    (
                        self._max_msg_size + 1
                        if self._max_msg_size
                        else self._max_msg_size
                    ),
                )
                if self._max_msg_size and len(payload_merged) > self._max_msg_size:
                    raise WebSocketError(
                        WSCloseCode.MESSAGE_TOO_BIG,
                        f"Decompressed message exceeds size limit {self._max_msg_size}",
                    )
            elif type(assembled_payload) is bytes:
                payload_merged = assembled_payload
            else:
                payload_merged = bytes(assembled_payload)

            if opcode == OP_CODE_TEXT:
                try:
                    text = payload_merged.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise WebSocketError(
                        WSCloseCode.INVALID_TEXT, "Invalid UTF-8 text message"
                    ) from exc

                # XXX: The Text and Binary messages here can be a performance
                # bottleneck, so we use tuple.__new__ to improve performance.
                # This is not type safe, but many tests should fail in
                # test_client_ws_functional.py if this is wrong.
                self.queue.feed_data(
                    TUPLE_NEW(WSMessage, (WS_MSG_TYPE_TEXT, text, "")),
                    len(payload_merged),
                )
            else:
                self.queue.feed_data(
                    TUPLE_NEW(WSMessage, (WS_MSG_TYPE_BINARY, payload_merged, "")),
                    len(payload_merged),
                )
        elif opcode == OP_CODE_CLOSE:
            if len(payload) >= 2:
                close_code = UNPACK_CLOSE_CODE(payload[:2])[0]
                if close_code < 3000 and close_code not in ALLOWED_CLOSE_CODES:
                    raise WebSocketError(
                        WSCloseCode.PROTOCOL_ERROR,
                        f"Invalid close code: {close_code}",
                    )
                try:
                    close_message = payload[2:].decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise WebSocketError(
                        WSCloseCode.INVALID_TEXT, "Invalid UTF-8 text message"
                    ) from exc
                msg = TUPLE_NEW(WSMessage, (WSMsgType.CLOSE, close_code, close_message))
            elif payload:
                raise WebSocketError(
                    WSCloseCode.PROTOCOL_ERROR,
                    f"Invalid close frame: {fin} {opcode} {payload!r}",
                )
            else:
                msg = TUPLE_NEW(WSMessage, (WSMsgType.CLOSE, 0, ""))

            self.queue.feed_data(msg, 0)
        elif opcode == OP_CODE_PING:
            msg = TUPLE_NEW(WSMessage, (WSMsgType.PING, payload, ""))
            self.queue.feed_data(msg, len(payload))
        elif opcode == OP_CODE_PONG:
            msg = TUPLE_NEW(WSMessage, (WSMsgType.PONG, payload, ""))
            self.queue.feed_data(msg, len(payload))
        else:
            raise WebSocketError(
                WSCloseCode.PROTOCOL_ERROR, f"Unexpected opcode={opcode!r}"
            )

    def _feed_data(self, data: bytes) -> None:
        """Return the next frame from the socket."""
        if self._tail:
            data, self._tail = self._tail + data, b""

        start_pos: int = 0
        data_len = len(data)
        data_cstr = data

        while True:
            # read header
            if self._state == READ_HEADER:
                if data_len - start_pos < 2:
                    break
                first_byte = data_cstr[start_pos]
                second_byte = data_cstr[start_pos + 1]
                start_pos += 2

                fin = (first_byte >> 7) & 1
                rsv1 = (first_byte >> 6) & 1
                rsv2 = (first_byte >> 5) & 1
                rsv3 = (first_byte >> 4) & 1
                opcode = first_byte & 0xF

                # frame-fin = %x0 ; more frames of this message follow
                #           / %x1 ; final frame of this message
                # frame-rsv1 = %x0 ;
                #    1 bit, MUST be 0 unless negotiated otherwise
                # frame-rsv2 = %x0 ;
                #    1 bit, MUST be 0 unless negotiated otherwise
                # frame-rsv3 = %x0 ;
                #    1 bit, MUST be 0 unless negotiated otherwise
                #
                # Remove rsv1 from this test for deflate development
                if rsv2 or rsv3 or (rsv1 and not self._compress):
                    raise WebSocketError(
                        WSCloseCode.PROTOCOL_ERROR,
                        "Received frame with non-zero reserved bits",
                    )

                if opcode > 0x7 and fin == 0:
                    raise WebSocketError(
                        WSCloseCode.PROTOCOL_ERROR,
                        "Received fragmented control frame",
                    )

                has_mask = (second_byte >> 7) & 1
                length = second_byte & 0x7F

                # Control frames MUST have a payload
                # length of 125 bytes or less
                if opcode > 0x7 and length > 125:
                    raise WebSocketError(
                        WSCloseCode.PROTOCOL_ERROR,
                        "Control frame payload cannot be larger than 125 bytes",
                    )

                # Set compress status if last package is FIN
                # OR set compress status if this is first fragment
                # Raise error if not first fragment with rsv1 = 0x1
                if self._frame_fin or self._compressed == COMPRESSED_NOT_SET:
                    self._compressed = COMPRESSED_TRUE if rsv1 else COMPRESSED_FALSE
                elif rsv1:
                    raise WebSocketError(
                        WSCloseCode.PROTOCOL_ERROR,
                        "Received frame with non-zero reserved bits",
                    )

                self._frame_fin = bool(fin)
                self._frame_opcode = opcode
                self._has_mask = bool(has_mask)
                self._payload_len_flag = length
                self._state = READ_PAYLOAD_LENGTH

            # read payload length
            if self._state == READ_PAYLOAD_LENGTH:
                len_flag = self._payload_len_flag
                if len_flag == 126:
                    if data_len - start_pos < 2:
                        break
                    first_byte = data_cstr[start_pos]
                    second_byte = data_cstr[start_pos + 1]
                    start_pos += 2
                    self._payload_bytes_to_read = first_byte << 8 | second_byte
                elif len_flag > 126:
                    if data_len - start_pos < 8:
                        break
                    self._payload_bytes_to_read = UNPACK_LEN3(data, start_pos)[0]
                    start_pos += 8
                else:
                    self._payload_bytes_to_read = len_flag

                self._state = READ_PAYLOAD_MASK if self._has_mask else READ_PAYLOAD

            # read payload mask
            if self._state == READ_PAYLOAD_MASK:
                if data_len - start_pos < 4:
                    break
                self._frame_mask = data_cstr[start_pos : start_pos + 4]
                start_pos += 4
                self._state = READ_PAYLOAD

            if self._state == READ_PAYLOAD:
                chunk_len = data_len - start_pos
                if self._payload_bytes_to_read >= chunk_len:
                    f_end_pos = data_len
                    self._payload_bytes_to_read -= chunk_len
                else:
                    f_end_pos = start_pos + self._payload_bytes_to_read
                    self._payload_bytes_to_read = 0

                had_fragments = self._frame_payload_len
                self._frame_payload_len += f_end_pos - start_pos
                f_start_pos = start_pos
                start_pos = f_end_pos

                if self._payload_bytes_to_read != 0:
                    # If we don't have a complete frame, we need to save the
                    # data for the next call to feed_data.
                    self._payload_fragments.append(data_cstr[f_start_pos:f_end_pos])
                    break

                payload: Union[bytes, bytearray]
                if had_fragments:
                    # We have to join the payload fragments get the payload
                    self._payload_fragments.append(data_cstr[f_start_pos:f_end_pos])
                    if self._has_mask:
                        assert self._frame_mask is not None
                        payload_bytearray = bytearray(b"".join(self._payload_fragments))
                        websocket_mask(self._frame_mask, payload_bytearray)
                        payload = payload_bytearray
                    else:
                        payload = b"".join(self._payload_fragments)
                    self._payload_fragments.clear()
                elif self._has_mask:
                    assert self._frame_mask is not None
                    payload_bytearray = data_cstr[f_start_pos:f_end_pos]  # type: ignore[assignment]
                    if type(payload_bytearray) is not bytearray:  # pragma: no branch
                        # Cython will do the conversion for us
                        # but we need to do it for Python and we
                        # will always get here in Python
                        payload_bytearray = bytearray(payload_bytearray)
                    websocket_mask(self._frame_mask, payload_bytearray)
                    payload = payload_bytearray
                else:
                    payload = data_cstr[f_start_pos:f_end_pos]

                self._handle_frame(
                    self._frame_fin, self._frame_opcode, payload, self._compressed
                )
                self._frame_payload_len = 0
                self._state = READ_HEADER

        # XXX: Cython needs slices to be bounded, so we can't omit the slice end here.
        self._tail = data_cstr[start_pos:data_len] if start_pos < data_len else b""
