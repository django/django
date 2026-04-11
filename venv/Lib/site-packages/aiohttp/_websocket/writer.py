"""WebSocket protocol versions 13 and 8."""

import asyncio
import random
import sys
from functools import partial
from typing import Final, Optional, Set, Union

from ..base_protocol import BaseProtocol
from ..client_exceptions import ClientConnectionResetError
from ..compression_utils import ZLibBackend, ZLibCompressor
from .helpers import (
    MASK_LEN,
    MSG_SIZE,
    PACK_CLOSE_CODE,
    PACK_LEN1,
    PACK_LEN2,
    PACK_LEN3,
    PACK_RANDBITS,
    websocket_mask,
)
from .models import WS_DEFLATE_TRAILING, WSMsgType

DEFAULT_LIMIT: Final[int] = 2**16

# WebSocket opcode boundary: opcodes 0-7 are data frames, 8-15 are control frames
# Control frames (ping, pong, close) are never compressed
WS_CONTROL_FRAME_OPCODE: Final[int] = 8

# For websockets, keeping latency low is extremely important as implementations
# generally expect to be able to send and receive messages quickly. We use a
# larger chunk size to reduce the number of executor calls and avoid task
# creation overhead, since both are significant sources of latency when chunks
# are small. A size of 16KiB was chosen as a balance between avoiding task
# overhead and not blocking the event loop too long with synchronous compression.

WEBSOCKET_MAX_SYNC_CHUNK_SIZE = 16 * 1024


class WebSocketWriter:
    """WebSocket writer.

    The writer is responsible for sending messages to the client. It is
    created by the protocol when a connection is established. The writer
    should avoid implementing any application logic and should only be
    concerned with the low-level details of the WebSocket protocol.
    """

    def __init__(
        self,
        protocol: BaseProtocol,
        transport: asyncio.Transport,
        *,
        use_mask: bool = False,
        limit: int = DEFAULT_LIMIT,
        random: random.Random = random.Random(),
        compress: int = 0,
        notakeover: bool = False,
    ) -> None:
        """Initialize a WebSocket writer."""
        self.protocol = protocol
        self.transport = transport
        self.use_mask = use_mask
        self.get_random_bits = partial(random.getrandbits, 32)
        self.compress = compress
        self.notakeover = notakeover
        self._closing = False
        self._limit = limit
        self._output_size = 0
        self._compressobj: Optional[ZLibCompressor] = None
        self._send_lock = asyncio.Lock()
        self._background_tasks: Set[asyncio.Task[None]] = set()

    async def send_frame(
        self, message: bytes, opcode: int, compress: Optional[int] = None
    ) -> None:
        """Send a frame over the websocket with message as its payload."""
        if self._closing and not (opcode & WSMsgType.CLOSE):
            raise ClientConnectionResetError("Cannot write to closing transport")

        if not (compress or self.compress) or opcode >= WS_CONTROL_FRAME_OPCODE:
            # Non-compressed frames don't need lock or shield
            self._write_websocket_frame(message, opcode, 0)
        elif len(message) <= WEBSOCKET_MAX_SYNC_CHUNK_SIZE:
            # Small compressed payloads - compress synchronously in event loop
            # We need the lock even though sync compression has no await points.
            # This prevents small frames from interleaving with large frames that
            # compress in the executor, avoiding compressor state corruption.
            async with self._send_lock:
                self._send_compressed_frame_sync(message, opcode, compress)
        else:
            # Large compressed frames need shield to prevent corruption
            # For large compressed frames, the entire compress+send
            # operation must be atomic. If cancelled after compression but
            # before send, the compressor state would be advanced but data
            # not sent, corrupting subsequent frames.
            # Create a task to shield from cancellation
            # The lock is acquired inside the shielded task so the entire
            # operation (lock + compress + send) completes atomically.
            # Use eager_start on Python 3.12+ to avoid scheduling overhead
            loop = asyncio.get_running_loop()
            coro = self._send_compressed_frame_async_locked(message, opcode, compress)
            if sys.version_info >= (3, 12):
                send_task = asyncio.Task(coro, loop=loop, eager_start=True)
            else:
                send_task = loop.create_task(coro)
            # Keep a strong reference to prevent garbage collection
            self._background_tasks.add(send_task)
            send_task.add_done_callback(self._background_tasks.discard)
            await asyncio.shield(send_task)

        # It is safe to return control to the event loop when using compression
        # after this point as we have already sent or buffered all the data.
        # Once we have written output_size up to the limit, we call the
        # drain helper which waits for the transport to be ready to accept
        # more data. This is a flow control mechanism to prevent the buffer
        # from growing too large. The drain helper will return right away
        # if the writer is not paused.
        if self._output_size > self._limit:
            self._output_size = 0
            if self.protocol._paused:
                await self.protocol._drain_helper()

    def _write_websocket_frame(self, message: bytes, opcode: int, rsv: int) -> None:
        """
        Write a websocket frame to the transport.

        This method handles frame header construction, masking, and writing to transport.
        It does not handle compression or flow control - those are the responsibility
        of the caller.
        """
        msg_length = len(message)

        use_mask = self.use_mask
        mask_bit = 0x80 if use_mask else 0

        # Depending on the message length, the header is assembled differently.
        # The first byte is reserved for the opcode and the RSV bits.
        first_byte = 0x80 | rsv | opcode
        if msg_length < 126:
            header = PACK_LEN1(first_byte, msg_length | mask_bit)
            header_len = 2
        elif msg_length < 65536:
            header = PACK_LEN2(first_byte, 126 | mask_bit, msg_length)
            header_len = 4
        else:
            header = PACK_LEN3(first_byte, 127 | mask_bit, msg_length)
            header_len = 10

        if self.transport.is_closing():
            raise ClientConnectionResetError("Cannot write to closing transport")

        # https://datatracker.ietf.org/doc/html/rfc6455#section-5.3
        # If we are using a mask, we need to generate it randomly
        # and apply it to the message before sending it. A mask is
        # a 32-bit value that is applied to the message using a
        # bitwise XOR operation. It is used to prevent certain types
        # of attacks on the websocket protocol. The mask is only used
        # when aiohttp is acting as a client. Servers do not use a mask.
        if use_mask:
            mask = PACK_RANDBITS(self.get_random_bits())
            message = bytearray(message)
            websocket_mask(mask, message)
            self.transport.write(header + mask + message)
            self._output_size += MASK_LEN
        elif msg_length > MSG_SIZE:
            self.transport.write(header)
            self.transport.write(message)
        else:
            self.transport.write(header + message)

        self._output_size += header_len + msg_length

    def _get_compressor(self, compress: Optional[int]) -> ZLibCompressor:
        """Get or create a compressor object for the given compression level."""
        if compress:
            # Do not set self._compress if compressing is for this frame
            return ZLibCompressor(
                level=ZLibBackend.Z_BEST_SPEED,
                wbits=-compress,
                max_sync_chunk_size=WEBSOCKET_MAX_SYNC_CHUNK_SIZE,
            )
        if not self._compressobj:
            self._compressobj = ZLibCompressor(
                level=ZLibBackend.Z_BEST_SPEED,
                wbits=-self.compress,
                max_sync_chunk_size=WEBSOCKET_MAX_SYNC_CHUNK_SIZE,
            )
        return self._compressobj

    def _send_compressed_frame_sync(
        self, message: bytes, opcode: int, compress: Optional[int]
    ) -> None:
        """
        Synchronous send for small compressed frames.

        This is used for small compressed payloads that compress synchronously in the event loop.
        Since there are no await points, this is inherently cancellation-safe.
        """
        # RSV are the reserved bits in the frame header. They are used to
        # indicate that the frame is using an extension.
        # https://datatracker.ietf.org/doc/html/rfc6455#section-5.2
        compressobj = self._get_compressor(compress)
        # (0x40) RSV1 is set for compressed frames
        # https://datatracker.ietf.org/doc/html/rfc7692#section-7.2.3.1
        self._write_websocket_frame(
            (
                compressobj.compress_sync(message)
                + compressobj.flush(
                    ZLibBackend.Z_FULL_FLUSH
                    if self.notakeover
                    else ZLibBackend.Z_SYNC_FLUSH
                )
            ).removesuffix(WS_DEFLATE_TRAILING),
            opcode,
            0x40,
        )

    async def _send_compressed_frame_async_locked(
        self, message: bytes, opcode: int, compress: Optional[int]
    ) -> None:
        """
        Async send for large compressed frames with lock.

        Acquires the lock and compresses large payloads asynchronously in
        the executor. The lock is held for the entire operation to ensure
        the compressor state is not corrupted by concurrent sends.

        MUST be run shielded from cancellation. If cancelled after
        compression but before sending, the compressor state would be
        advanced but data not sent, corrupting subsequent frames.
        """
        async with self._send_lock:
            # RSV are the reserved bits in the frame header. They are used to
            # indicate that the frame is using an extension.
            # https://datatracker.ietf.org/doc/html/rfc6455#section-5.2
            compressobj = self._get_compressor(compress)
            # (0x40) RSV1 is set for compressed frames
            # https://datatracker.ietf.org/doc/html/rfc7692#section-7.2.3.1
            self._write_websocket_frame(
                (
                    await compressobj.compress(message)
                    + compressobj.flush(
                        ZLibBackend.Z_FULL_FLUSH
                        if self.notakeover
                        else ZLibBackend.Z_SYNC_FLUSH
                    )
                ).removesuffix(WS_DEFLATE_TRAILING),
                opcode,
                0x40,
            )

    async def close(self, code: int = 1000, message: Union[bytes, str] = b"") -> None:
        """Close the websocket, sending the specified code and message."""
        if isinstance(message, str):
            message = message.encode("utf-8")
        try:
            await self.send_frame(
                PACK_CLOSE_CODE(code) + message, opcode=WSMsgType.CLOSE
            )
        finally:
            self._closing = True
