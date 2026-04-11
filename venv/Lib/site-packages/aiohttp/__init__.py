__version__ = "3.13.3"

from typing import TYPE_CHECKING, Tuple

from . import hdrs as hdrs
from .client import (
    BaseConnector,
    ClientConnectionError,
    ClientConnectionResetError,
    ClientConnectorCertificateError,
    ClientConnectorDNSError,
    ClientConnectorError,
    ClientConnectorSSLError,
    ClientError,
    ClientHttpProxyError,
    ClientOSError,
    ClientPayloadError,
    ClientProxyConnectionError,
    ClientRequest,
    ClientResponse,
    ClientResponseError,
    ClientSession,
    ClientSSLError,
    ClientTimeout,
    ClientWebSocketResponse,
    ClientWSTimeout,
    ConnectionTimeoutError,
    ContentTypeError,
    Fingerprint,
    InvalidURL,
    InvalidUrlClientError,
    InvalidUrlRedirectClientError,
    NamedPipeConnector,
    NonHttpUrlClientError,
    NonHttpUrlRedirectClientError,
    RedirectClientError,
    RequestInfo,
    ServerConnectionError,
    ServerDisconnectedError,
    ServerFingerprintMismatch,
    ServerTimeoutError,
    SocketTimeoutError,
    TCPConnector,
    TooManyRedirects,
    UnixConnector,
    WSMessageTypeError,
    WSServerHandshakeError,
    request,
)
from .client_middleware_digest_auth import DigestAuthMiddleware
from .client_middlewares import ClientHandlerType, ClientMiddlewareType
from .compression_utils import set_zlib_backend
from .connector import (
    AddrInfoType as AddrInfoType,
    SocketFactoryType as SocketFactoryType,
)
from .cookiejar import CookieJar as CookieJar, DummyCookieJar as DummyCookieJar
from .formdata import FormData as FormData
from .helpers import BasicAuth, ChainMapProxy, ETag
from .http import (
    HttpVersion as HttpVersion,
    HttpVersion10 as HttpVersion10,
    HttpVersion11 as HttpVersion11,
    WebSocketError as WebSocketError,
    WSCloseCode as WSCloseCode,
    WSMessage as WSMessage,
    WSMsgType as WSMsgType,
)
from .multipart import (
    BadContentDispositionHeader as BadContentDispositionHeader,
    BadContentDispositionParam as BadContentDispositionParam,
    BodyPartReader as BodyPartReader,
    MultipartReader as MultipartReader,
    MultipartWriter as MultipartWriter,
    content_disposition_filename as content_disposition_filename,
    parse_content_disposition as parse_content_disposition,
)
from .payload import (
    PAYLOAD_REGISTRY as PAYLOAD_REGISTRY,
    AsyncIterablePayload as AsyncIterablePayload,
    BufferedReaderPayload as BufferedReaderPayload,
    BytesIOPayload as BytesIOPayload,
    BytesPayload as BytesPayload,
    IOBasePayload as IOBasePayload,
    JsonPayload as JsonPayload,
    Payload as Payload,
    StringIOPayload as StringIOPayload,
    StringPayload as StringPayload,
    TextIOPayload as TextIOPayload,
    get_payload as get_payload,
    payload_type as payload_type,
)
from .payload_streamer import streamer as streamer
from .resolver import (
    AsyncResolver as AsyncResolver,
    DefaultResolver as DefaultResolver,
    ThreadedResolver as ThreadedResolver,
)
from .streams import (
    EMPTY_PAYLOAD as EMPTY_PAYLOAD,
    DataQueue as DataQueue,
    EofStream as EofStream,
    FlowControlDataQueue as FlowControlDataQueue,
    StreamReader as StreamReader,
)
from .tracing import (
    TraceConfig as TraceConfig,
    TraceConnectionCreateEndParams as TraceConnectionCreateEndParams,
    TraceConnectionCreateStartParams as TraceConnectionCreateStartParams,
    TraceConnectionQueuedEndParams as TraceConnectionQueuedEndParams,
    TraceConnectionQueuedStartParams as TraceConnectionQueuedStartParams,
    TraceConnectionReuseconnParams as TraceConnectionReuseconnParams,
    TraceDnsCacheHitParams as TraceDnsCacheHitParams,
    TraceDnsCacheMissParams as TraceDnsCacheMissParams,
    TraceDnsResolveHostEndParams as TraceDnsResolveHostEndParams,
    TraceDnsResolveHostStartParams as TraceDnsResolveHostStartParams,
    TraceRequestChunkSentParams as TraceRequestChunkSentParams,
    TraceRequestEndParams as TraceRequestEndParams,
    TraceRequestExceptionParams as TraceRequestExceptionParams,
    TraceRequestHeadersSentParams as TraceRequestHeadersSentParams,
    TraceRequestRedirectParams as TraceRequestRedirectParams,
    TraceRequestStartParams as TraceRequestStartParams,
    TraceResponseChunkReceivedParams as TraceResponseChunkReceivedParams,
)

if TYPE_CHECKING:
    # At runtime these are lazy-loaded at the bottom of the file.
    from .worker import (
        GunicornUVLoopWebWorker as GunicornUVLoopWebWorker,
        GunicornWebWorker as GunicornWebWorker,
    )

__all__: Tuple[str, ...] = (
    "hdrs",
    # client
    "AddrInfoType",
    "BaseConnector",
    "ClientConnectionError",
    "ClientConnectionResetError",
    "ClientConnectorCertificateError",
    "ClientConnectorDNSError",
    "ClientConnectorError",
    "ClientConnectorSSLError",
    "ClientError",
    "ClientHttpProxyError",
    "ClientOSError",
    "ClientPayloadError",
    "ClientProxyConnectionError",
    "ClientResponse",
    "ClientRequest",
    "ClientResponseError",
    "ClientSSLError",
    "ClientSession",
    "ClientTimeout",
    "ClientWebSocketResponse",
    "ClientWSTimeout",
    "ConnectionTimeoutError",
    "ContentTypeError",
    "Fingerprint",
    "FlowControlDataQueue",
    "InvalidURL",
    "InvalidUrlClientError",
    "InvalidUrlRedirectClientError",
    "NonHttpUrlClientError",
    "NonHttpUrlRedirectClientError",
    "RedirectClientError",
    "RequestInfo",
    "ServerConnectionError",
    "ServerDisconnectedError",
    "ServerFingerprintMismatch",
    "ServerTimeoutError",
    "SocketFactoryType",
    "SocketTimeoutError",
    "TCPConnector",
    "TooManyRedirects",
    "UnixConnector",
    "NamedPipeConnector",
    "WSServerHandshakeError",
    "request",
    # client_middleware
    "ClientMiddlewareType",
    "ClientHandlerType",
    # cookiejar
    "CookieJar",
    "DummyCookieJar",
    # formdata
    "FormData",
    # helpers
    "BasicAuth",
    "ChainMapProxy",
    "DigestAuthMiddleware",
    "ETag",
    "set_zlib_backend",
    # http
    "HttpVersion",
    "HttpVersion10",
    "HttpVersion11",
    "WSMsgType",
    "WSCloseCode",
    "WSMessage",
    "WebSocketError",
    # multipart
    "BadContentDispositionHeader",
    "BadContentDispositionParam",
    "BodyPartReader",
    "MultipartReader",
    "MultipartWriter",
    "content_disposition_filename",
    "parse_content_disposition",
    # payload
    "AsyncIterablePayload",
    "BufferedReaderPayload",
    "BytesIOPayload",
    "BytesPayload",
    "IOBasePayload",
    "JsonPayload",
    "PAYLOAD_REGISTRY",
    "Payload",
    "StringIOPayload",
    "StringPayload",
    "TextIOPayload",
    "get_payload",
    "payload_type",
    # payload_streamer
    "streamer",
    # resolver
    "AsyncResolver",
    "DefaultResolver",
    "ThreadedResolver",
    # streams
    "DataQueue",
    "EMPTY_PAYLOAD",
    "EofStream",
    "StreamReader",
    # tracing
    "TraceConfig",
    "TraceConnectionCreateEndParams",
    "TraceConnectionCreateStartParams",
    "TraceConnectionQueuedEndParams",
    "TraceConnectionQueuedStartParams",
    "TraceConnectionReuseconnParams",
    "TraceDnsCacheHitParams",
    "TraceDnsCacheMissParams",
    "TraceDnsResolveHostEndParams",
    "TraceDnsResolveHostStartParams",
    "TraceRequestChunkSentParams",
    "TraceRequestEndParams",
    "TraceRequestExceptionParams",
    "TraceRequestHeadersSentParams",
    "TraceRequestRedirectParams",
    "TraceRequestStartParams",
    "TraceResponseChunkReceivedParams",
    # workers (imported lazily with __getattr__)
    "GunicornUVLoopWebWorker",
    "GunicornWebWorker",
    "WSMessageTypeError",
)


def __dir__() -> Tuple[str, ...]:
    return __all__ + ("__doc__",)


def __getattr__(name: str) -> object:
    global GunicornUVLoopWebWorker, GunicornWebWorker

    # Importing gunicorn takes a long time (>100ms), so only import if actually needed.
    if name in ("GunicornUVLoopWebWorker", "GunicornWebWorker"):
        try:
            from .worker import GunicornUVLoopWebWorker as guv, GunicornWebWorker as gw
        except ImportError:
            return None

        GunicornUVLoopWebWorker = guv  # type: ignore[misc]
        GunicornWebWorker = gw  # type: ignore[misc]
        return guv if name == "GunicornUVLoopWebWorker" else gw

    raise AttributeError(f"module {__name__} has no attribute {name}")
