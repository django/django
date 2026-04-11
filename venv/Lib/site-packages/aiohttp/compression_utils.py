import asyncio
import sys
import zlib
from abc import ABC, abstractmethod
from concurrent.futures import Executor
from typing import Any, Final, Optional, Protocol, TypedDict, cast

if sys.version_info >= (3, 12):
    from collections.abc import Buffer
else:
    from typing import Union

    Buffer = Union[bytes, bytearray, "memoryview[int]", "memoryview[bytes]"]

try:
    try:
        import brotlicffi as brotli
    except ImportError:
        import brotli

    HAS_BROTLI = True
except ImportError:  # pragma: no cover
    HAS_BROTLI = False

try:
    if sys.version_info >= (3, 14):
        from compression.zstd import ZstdDecompressor  # noqa: I900
    else:  # TODO(PY314): Remove mentions of backports.zstd across codebase
        from backports.zstd import ZstdDecompressor

    HAS_ZSTD = True
except ImportError:
    HAS_ZSTD = False


MAX_SYNC_CHUNK_SIZE = 4096
DEFAULT_MAX_DECOMPRESS_SIZE = 2**25  # 32MiB

# Unlimited decompression constants - different libraries use different conventions
ZLIB_MAX_LENGTH_UNLIMITED = 0  # zlib uses 0 to mean unlimited
ZSTD_MAX_LENGTH_UNLIMITED = -1  # zstd uses -1 to mean unlimited


class ZLibCompressObjProtocol(Protocol):
    def compress(self, data: Buffer) -> bytes: ...
    def flush(self, mode: int = ..., /) -> bytes: ...


class ZLibDecompressObjProtocol(Protocol):
    def decompress(self, data: Buffer, max_length: int = ...) -> bytes: ...
    def flush(self, length: int = ..., /) -> bytes: ...

    @property
    def eof(self) -> bool: ...


class ZLibBackendProtocol(Protocol):
    MAX_WBITS: int
    Z_FULL_FLUSH: int
    Z_SYNC_FLUSH: int
    Z_BEST_SPEED: int
    Z_FINISH: int

    def compressobj(
        self,
        level: int = ...,
        method: int = ...,
        wbits: int = ...,
        memLevel: int = ...,
        strategy: int = ...,
        zdict: Optional[Buffer] = ...,
    ) -> ZLibCompressObjProtocol: ...
    def decompressobj(
        self, wbits: int = ..., zdict: Buffer = ...
    ) -> ZLibDecompressObjProtocol: ...

    def compress(
        self, data: Buffer, /, level: int = ..., wbits: int = ...
    ) -> bytes: ...
    def decompress(
        self, data: Buffer, /, wbits: int = ..., bufsize: int = ...
    ) -> bytes: ...


class CompressObjArgs(TypedDict, total=False):
    wbits: int
    strategy: int
    level: int


class ZLibBackendWrapper:
    def __init__(self, _zlib_backend: ZLibBackendProtocol):
        self._zlib_backend: ZLibBackendProtocol = _zlib_backend

    @property
    def name(self) -> str:
        return getattr(self._zlib_backend, "__name__", "undefined")

    @property
    def MAX_WBITS(self) -> int:
        return self._zlib_backend.MAX_WBITS

    @property
    def Z_FULL_FLUSH(self) -> int:
        return self._zlib_backend.Z_FULL_FLUSH

    @property
    def Z_SYNC_FLUSH(self) -> int:
        return self._zlib_backend.Z_SYNC_FLUSH

    @property
    def Z_BEST_SPEED(self) -> int:
        return self._zlib_backend.Z_BEST_SPEED

    @property
    def Z_FINISH(self) -> int:
        return self._zlib_backend.Z_FINISH

    def compressobj(self, *args: Any, **kwargs: Any) -> ZLibCompressObjProtocol:
        return self._zlib_backend.compressobj(*args, **kwargs)

    def decompressobj(self, *args: Any, **kwargs: Any) -> ZLibDecompressObjProtocol:
        return self._zlib_backend.decompressobj(*args, **kwargs)

    def compress(self, data: Buffer, *args: Any, **kwargs: Any) -> bytes:
        return self._zlib_backend.compress(data, *args, **kwargs)

    def decompress(self, data: Buffer, *args: Any, **kwargs: Any) -> bytes:
        return self._zlib_backend.decompress(data, *args, **kwargs)

    # Everything not explicitly listed in the Protocol we just pass through
    def __getattr__(self, attrname: str) -> Any:
        return getattr(self._zlib_backend, attrname)


ZLibBackend: ZLibBackendWrapper = ZLibBackendWrapper(zlib)


def set_zlib_backend(new_zlib_backend: ZLibBackendProtocol) -> None:
    ZLibBackend._zlib_backend = new_zlib_backend


def encoding_to_mode(
    encoding: Optional[str] = None,
    suppress_deflate_header: bool = False,
) -> int:
    if encoding == "gzip":
        return 16 + ZLibBackend.MAX_WBITS

    return -ZLibBackend.MAX_WBITS if suppress_deflate_header else ZLibBackend.MAX_WBITS


class DecompressionBaseHandler(ABC):
    def __init__(
        self,
        executor: Optional[Executor] = None,
        max_sync_chunk_size: Optional[int] = MAX_SYNC_CHUNK_SIZE,
    ):
        """Base class for decompression handlers."""
        self._executor = executor
        self._max_sync_chunk_size = max_sync_chunk_size

    @abstractmethod
    def decompress_sync(
        self, data: bytes, max_length: int = ZLIB_MAX_LENGTH_UNLIMITED
    ) -> bytes:
        """Decompress the given data."""

    async def decompress(
        self, data: bytes, max_length: int = ZLIB_MAX_LENGTH_UNLIMITED
    ) -> bytes:
        """Decompress the given data."""
        if (
            self._max_sync_chunk_size is not None
            and len(data) > self._max_sync_chunk_size
        ):
            return await asyncio.get_event_loop().run_in_executor(
                self._executor, self.decompress_sync, data, max_length
            )
        return self.decompress_sync(data, max_length)


class ZLibCompressor:
    def __init__(
        self,
        encoding: Optional[str] = None,
        suppress_deflate_header: bool = False,
        level: Optional[int] = None,
        wbits: Optional[int] = None,
        strategy: Optional[int] = None,
        executor: Optional[Executor] = None,
        max_sync_chunk_size: Optional[int] = MAX_SYNC_CHUNK_SIZE,
    ):
        self._executor = executor
        self._max_sync_chunk_size = max_sync_chunk_size
        self._mode = (
            encoding_to_mode(encoding, suppress_deflate_header)
            if wbits is None
            else wbits
        )
        self._zlib_backend: Final = ZLibBackendWrapper(ZLibBackend._zlib_backend)

        kwargs: CompressObjArgs = {}
        kwargs["wbits"] = self._mode
        if strategy is not None:
            kwargs["strategy"] = strategy
        if level is not None:
            kwargs["level"] = level
        self._compressor = self._zlib_backend.compressobj(**kwargs)

    def compress_sync(self, data: bytes) -> bytes:
        return self._compressor.compress(data)

    async def compress(self, data: bytes) -> bytes:
        """Compress the data and returned the compressed bytes.

        Note that flush() must be called after the last call to compress()

        If the data size is large than the max_sync_chunk_size, the compression
        will be done in the executor. Otherwise, the compression will be done
        in the event loop.

        **WARNING: This method is NOT cancellation-safe when used with flush().**
        If this operation is cancelled, the compressor state may be corrupted.
        The connection MUST be closed after cancellation to avoid data corruption
        in subsequent compress operations.

        For cancellation-safe compression (e.g., WebSocket), the caller MUST wrap
        compress() + flush() + send operations in a shield and lock to ensure atomicity.
        """
        # For large payloads, offload compression to executor to avoid blocking event loop
        should_use_executor = (
            self._max_sync_chunk_size is not None
            and len(data) > self._max_sync_chunk_size
        )
        if should_use_executor:
            return await asyncio.get_running_loop().run_in_executor(
                self._executor, self._compressor.compress, data
            )
        return self.compress_sync(data)

    def flush(self, mode: Optional[int] = None) -> bytes:
        """Flush the compressor synchronously.

        **WARNING: This method is NOT cancellation-safe when called after compress().**
        The flush() operation accesses shared compressor state. If compress() was
        cancelled, calling flush() may result in corrupted data. The connection MUST
        be closed after compress() cancellation.

        For cancellation-safe compression (e.g., WebSocket), the caller MUST wrap
        compress() + flush() + send operations in a shield and lock to ensure atomicity.
        """
        return self._compressor.flush(
            mode if mode is not None else self._zlib_backend.Z_FINISH
        )


class ZLibDecompressor(DecompressionBaseHandler):
    def __init__(
        self,
        encoding: Optional[str] = None,
        suppress_deflate_header: bool = False,
        executor: Optional[Executor] = None,
        max_sync_chunk_size: Optional[int] = MAX_SYNC_CHUNK_SIZE,
    ):
        super().__init__(executor=executor, max_sync_chunk_size=max_sync_chunk_size)
        self._mode = encoding_to_mode(encoding, suppress_deflate_header)
        self._zlib_backend: Final = ZLibBackendWrapper(ZLibBackend._zlib_backend)
        self._decompressor = self._zlib_backend.decompressobj(wbits=self._mode)

    def decompress_sync(
        self, data: Buffer, max_length: int = ZLIB_MAX_LENGTH_UNLIMITED
    ) -> bytes:
        return self._decompressor.decompress(data, max_length)

    def flush(self, length: int = 0) -> bytes:
        return (
            self._decompressor.flush(length)
            if length > 0
            else self._decompressor.flush()
        )

    @property
    def eof(self) -> bool:
        return self._decompressor.eof


class BrotliDecompressor(DecompressionBaseHandler):
    # Supports both 'brotlipy' and 'Brotli' packages
    # since they share an import name. The top branches
    # are for 'brotlipy' and bottom branches for 'Brotli'
    def __init__(
        self,
        executor: Optional[Executor] = None,
        max_sync_chunk_size: Optional[int] = MAX_SYNC_CHUNK_SIZE,
    ) -> None:
        """Decompress data using the Brotli library."""
        if not HAS_BROTLI:
            raise RuntimeError(
                "The brotli decompression is not available. "
                "Please install `Brotli` module"
            )
        self._obj = brotli.Decompressor()
        super().__init__(executor=executor, max_sync_chunk_size=max_sync_chunk_size)

    def decompress_sync(
        self, data: Buffer, max_length: int = ZLIB_MAX_LENGTH_UNLIMITED
    ) -> bytes:
        """Decompress the given data."""
        if hasattr(self._obj, "decompress"):
            return cast(bytes, self._obj.decompress(data, max_length))
        return cast(bytes, self._obj.process(data, max_length))

    def flush(self) -> bytes:
        """Flush the decompressor."""
        if hasattr(self._obj, "flush"):
            return cast(bytes, self._obj.flush())
        return b""


class ZSTDDecompressor(DecompressionBaseHandler):
    def __init__(
        self,
        executor: Optional[Executor] = None,
        max_sync_chunk_size: Optional[int] = MAX_SYNC_CHUNK_SIZE,
    ) -> None:
        if not HAS_ZSTD:
            raise RuntimeError(
                "The zstd decompression is not available. "
                "Please install `backports.zstd` module"
            )
        self._obj = ZstdDecompressor()
        super().__init__(executor=executor, max_sync_chunk_size=max_sync_chunk_size)

    def decompress_sync(
        self, data: bytes, max_length: int = ZLIB_MAX_LENGTH_UNLIMITED
    ) -> bytes:
        # zstd uses -1 for unlimited, while zlib uses 0 for unlimited
        # Convert the zlib convention (0=unlimited) to zstd convention (-1=unlimited)
        zstd_max_length = (
            ZSTD_MAX_LENGTH_UNLIMITED
            if max_length == ZLIB_MAX_LENGTH_UNLIMITED
            else max_length
        )
        return self._obj.decompress(data, zstd_max_length)

    def flush(self) -> bytes:
        return b""
