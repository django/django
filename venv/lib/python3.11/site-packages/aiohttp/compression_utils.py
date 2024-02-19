import asyncio
import zlib
from concurrent.futures import Executor
from typing import Optional, cast

try:
    try:
        import brotlicffi as brotli
    except ImportError:
        import brotli

    HAS_BROTLI = True
except ImportError:  # pragma: no cover
    HAS_BROTLI = False

MAX_SYNC_CHUNK_SIZE = 1024


def encoding_to_mode(
    encoding: Optional[str] = None,
    suppress_deflate_header: bool = False,
) -> int:
    if encoding == "gzip":
        return 16 + zlib.MAX_WBITS

    return -zlib.MAX_WBITS if suppress_deflate_header else zlib.MAX_WBITS


class ZlibBaseHandler:
    def __init__(
        self,
        mode: int,
        executor: Optional[Executor] = None,
        max_sync_chunk_size: Optional[int] = MAX_SYNC_CHUNK_SIZE,
    ):
        self._mode = mode
        self._executor = executor
        self._max_sync_chunk_size = max_sync_chunk_size


class ZLibCompressor(ZlibBaseHandler):
    def __init__(
        self,
        encoding: Optional[str] = None,
        suppress_deflate_header: bool = False,
        level: Optional[int] = None,
        wbits: Optional[int] = None,
        strategy: int = zlib.Z_DEFAULT_STRATEGY,
        executor: Optional[Executor] = None,
        max_sync_chunk_size: Optional[int] = MAX_SYNC_CHUNK_SIZE,
    ):
        super().__init__(
            mode=encoding_to_mode(encoding, suppress_deflate_header)
            if wbits is None
            else wbits,
            executor=executor,
            max_sync_chunk_size=max_sync_chunk_size,
        )
        if level is None:
            self._compressor = zlib.compressobj(wbits=self._mode, strategy=strategy)
        else:
            self._compressor = zlib.compressobj(
                wbits=self._mode, strategy=strategy, level=level
            )
        self._compress_lock = asyncio.Lock()

    def compress_sync(self, data: bytes) -> bytes:
        return self._compressor.compress(data)

    async def compress(self, data: bytes) -> bytes:
        async with self._compress_lock:
            # To ensure the stream is consistent in the event
            # there are multiple writers, we need to lock
            # the compressor so that only one writer can
            # compress at a time.
            if (
                self._max_sync_chunk_size is not None
                and len(data) > self._max_sync_chunk_size
            ):
                return await asyncio.get_event_loop().run_in_executor(
                    self._executor, self.compress_sync, data
                )
            return self.compress_sync(data)

    def flush(self, mode: int = zlib.Z_FINISH) -> bytes:
        return self._compressor.flush(mode)


class ZLibDecompressor(ZlibBaseHandler):
    def __init__(
        self,
        encoding: Optional[str] = None,
        suppress_deflate_header: bool = False,
        executor: Optional[Executor] = None,
        max_sync_chunk_size: Optional[int] = MAX_SYNC_CHUNK_SIZE,
    ):
        super().__init__(
            mode=encoding_to_mode(encoding, suppress_deflate_header),
            executor=executor,
            max_sync_chunk_size=max_sync_chunk_size,
        )
        self._decompressor = zlib.decompressobj(wbits=self._mode)

    def decompress_sync(self, data: bytes, max_length: int = 0) -> bytes:
        return self._decompressor.decompress(data, max_length)

    async def decompress(self, data: bytes, max_length: int = 0) -> bytes:
        if (
            self._max_sync_chunk_size is not None
            and len(data) > self._max_sync_chunk_size
        ):
            return await asyncio.get_event_loop().run_in_executor(
                self._executor, self.decompress_sync, data, max_length
            )
        return self.decompress_sync(data, max_length)

    def flush(self, length: int = 0) -> bytes:
        return (
            self._decompressor.flush(length)
            if length > 0
            else self._decompressor.flush()
        )

    @property
    def eof(self) -> bool:
        return self._decompressor.eof

    @property
    def unconsumed_tail(self) -> bytes:
        return self._decompressor.unconsumed_tail

    @property
    def unused_data(self) -> bytes:
        return self._decompressor.unused_data


class BrotliDecompressor:
    # Supports both 'brotlipy' and 'Brotli' packages
    # since they share an import name. The top branches
    # are for 'brotlipy' and bottom branches for 'Brotli'
    def __init__(self) -> None:
        if not HAS_BROTLI:
            raise RuntimeError(
                "The brotli decompression is not available. "
                "Please install `Brotli` module"
            )
        self._obj = brotli.Decompressor()

    def decompress_sync(self, data: bytes) -> bytes:
        if hasattr(self._obj, "decompress"):
            return cast(bytes, self._obj.decompress(data))
        return cast(bytes, self._obj.process(data))

    def flush(self) -> bytes:
        if hasattr(self._obj, "flush"):
            return cast(bytes, self._obj.flush())
        return b""
