from types import SimpleNamespace
from typing import TYPE_CHECKING, Mapping, Optional, Type, TypeVar

import attr
from aiosignal import Signal
from multidict import CIMultiDict
from yarl import URL

from .client_reqrep import ClientResponse

if TYPE_CHECKING:
    from .client import ClientSession

    _ParamT_contra = TypeVar("_ParamT_contra", contravariant=True)
    _TracingSignal = Signal[ClientSession, SimpleNamespace, _ParamT_contra]


__all__ = (
    "TraceConfig",
    "TraceRequestStartParams",
    "TraceRequestEndParams",
    "TraceRequestExceptionParams",
    "TraceConnectionQueuedStartParams",
    "TraceConnectionQueuedEndParams",
    "TraceConnectionCreateStartParams",
    "TraceConnectionCreateEndParams",
    "TraceConnectionReuseconnParams",
    "TraceDnsResolveHostStartParams",
    "TraceDnsResolveHostEndParams",
    "TraceDnsCacheHitParams",
    "TraceDnsCacheMissParams",
    "TraceRequestRedirectParams",
    "TraceRequestChunkSentParams",
    "TraceResponseChunkReceivedParams",
    "TraceRequestHeadersSentParams",
)


class TraceConfig:
    """First-class used to trace requests launched via ClientSession objects."""

    def __init__(
        self, trace_config_ctx_factory: Type[SimpleNamespace] = SimpleNamespace
    ) -> None:
        self._on_request_start: _TracingSignal[TraceRequestStartParams] = Signal(self)
        self._on_request_chunk_sent: _TracingSignal[TraceRequestChunkSentParams] = (
            Signal(self)
        )
        self._on_response_chunk_received: _TracingSignal[
            TraceResponseChunkReceivedParams
        ] = Signal(self)
        self._on_request_end: _TracingSignal[TraceRequestEndParams] = Signal(self)
        self._on_request_exception: _TracingSignal[TraceRequestExceptionParams] = (
            Signal(self)
        )
        self._on_request_redirect: _TracingSignal[TraceRequestRedirectParams] = Signal(
            self
        )
        self._on_connection_queued_start: _TracingSignal[
            TraceConnectionQueuedStartParams
        ] = Signal(self)
        self._on_connection_queued_end: _TracingSignal[
            TraceConnectionQueuedEndParams
        ] = Signal(self)
        self._on_connection_create_start: _TracingSignal[
            TraceConnectionCreateStartParams
        ] = Signal(self)
        self._on_connection_create_end: _TracingSignal[
            TraceConnectionCreateEndParams
        ] = Signal(self)
        self._on_connection_reuseconn: _TracingSignal[
            TraceConnectionReuseconnParams
        ] = Signal(self)
        self._on_dns_resolvehost_start: _TracingSignal[
            TraceDnsResolveHostStartParams
        ] = Signal(self)
        self._on_dns_resolvehost_end: _TracingSignal[TraceDnsResolveHostEndParams] = (
            Signal(self)
        )
        self._on_dns_cache_hit: _TracingSignal[TraceDnsCacheHitParams] = Signal(self)
        self._on_dns_cache_miss: _TracingSignal[TraceDnsCacheMissParams] = Signal(self)
        self._on_request_headers_sent: _TracingSignal[TraceRequestHeadersSentParams] = (
            Signal(self)
        )

        self._trace_config_ctx_factory = trace_config_ctx_factory

    def trace_config_ctx(
        self, trace_request_ctx: Optional[Mapping[str, str]] = None
    ) -> SimpleNamespace:
        """Return a new trace_config_ctx instance"""
        return self._trace_config_ctx_factory(trace_request_ctx=trace_request_ctx)

    def freeze(self) -> None:
        self._on_request_start.freeze()
        self._on_request_chunk_sent.freeze()
        self._on_response_chunk_received.freeze()
        self._on_request_end.freeze()
        self._on_request_exception.freeze()
        self._on_request_redirect.freeze()
        self._on_connection_queued_start.freeze()
        self._on_connection_queued_end.freeze()
        self._on_connection_create_start.freeze()
        self._on_connection_create_end.freeze()
        self._on_connection_reuseconn.freeze()
        self._on_dns_resolvehost_start.freeze()
        self._on_dns_resolvehost_end.freeze()
        self._on_dns_cache_hit.freeze()
        self._on_dns_cache_miss.freeze()
        self._on_request_headers_sent.freeze()

    @property
    def on_request_start(self) -> "_TracingSignal[TraceRequestStartParams]":
        return self._on_request_start

    @property
    def on_request_chunk_sent(
        self,
    ) -> "_TracingSignal[TraceRequestChunkSentParams]":
        return self._on_request_chunk_sent

    @property
    def on_response_chunk_received(
        self,
    ) -> "_TracingSignal[TraceResponseChunkReceivedParams]":
        return self._on_response_chunk_received

    @property
    def on_request_end(self) -> "_TracingSignal[TraceRequestEndParams]":
        return self._on_request_end

    @property
    def on_request_exception(
        self,
    ) -> "_TracingSignal[TraceRequestExceptionParams]":
        return self._on_request_exception

    @property
    def on_request_redirect(
        self,
    ) -> "_TracingSignal[TraceRequestRedirectParams]":
        return self._on_request_redirect

    @property
    def on_connection_queued_start(
        self,
    ) -> "_TracingSignal[TraceConnectionQueuedStartParams]":
        return self._on_connection_queued_start

    @property
    def on_connection_queued_end(
        self,
    ) -> "_TracingSignal[TraceConnectionQueuedEndParams]":
        return self._on_connection_queued_end

    @property
    def on_connection_create_start(
        self,
    ) -> "_TracingSignal[TraceConnectionCreateStartParams]":
        return self._on_connection_create_start

    @property
    def on_connection_create_end(
        self,
    ) -> "_TracingSignal[TraceConnectionCreateEndParams]":
        return self._on_connection_create_end

    @property
    def on_connection_reuseconn(
        self,
    ) -> "_TracingSignal[TraceConnectionReuseconnParams]":
        return self._on_connection_reuseconn

    @property
    def on_dns_resolvehost_start(
        self,
    ) -> "_TracingSignal[TraceDnsResolveHostStartParams]":
        return self._on_dns_resolvehost_start

    @property
    def on_dns_resolvehost_end(
        self,
    ) -> "_TracingSignal[TraceDnsResolveHostEndParams]":
        return self._on_dns_resolvehost_end

    @property
    def on_dns_cache_hit(self) -> "_TracingSignal[TraceDnsCacheHitParams]":
        return self._on_dns_cache_hit

    @property
    def on_dns_cache_miss(self) -> "_TracingSignal[TraceDnsCacheMissParams]":
        return self._on_dns_cache_miss

    @property
    def on_request_headers_sent(
        self,
    ) -> "_TracingSignal[TraceRequestHeadersSentParams]":
        return self._on_request_headers_sent


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceRequestStartParams:
    """Parameters sent by the `on_request_start` signal"""

    method: str
    url: URL
    headers: "CIMultiDict[str]"


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceRequestChunkSentParams:
    """Parameters sent by the `on_request_chunk_sent` signal"""

    method: str
    url: URL
    chunk: bytes


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceResponseChunkReceivedParams:
    """Parameters sent by the `on_response_chunk_received` signal"""

    method: str
    url: URL
    chunk: bytes


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceRequestEndParams:
    """Parameters sent by the `on_request_end` signal"""

    method: str
    url: URL
    headers: "CIMultiDict[str]"
    response: ClientResponse


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceRequestExceptionParams:
    """Parameters sent by the `on_request_exception` signal"""

    method: str
    url: URL
    headers: "CIMultiDict[str]"
    exception: BaseException


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceRequestRedirectParams:
    """Parameters sent by the `on_request_redirect` signal"""

    method: str
    url: URL
    headers: "CIMultiDict[str]"
    response: ClientResponse


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceConnectionQueuedStartParams:
    """Parameters sent by the `on_connection_queued_start` signal"""


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceConnectionQueuedEndParams:
    """Parameters sent by the `on_connection_queued_end` signal"""


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceConnectionCreateStartParams:
    """Parameters sent by the `on_connection_create_start` signal"""


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceConnectionCreateEndParams:
    """Parameters sent by the `on_connection_create_end` signal"""


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceConnectionReuseconnParams:
    """Parameters sent by the `on_connection_reuseconn` signal"""


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceDnsResolveHostStartParams:
    """Parameters sent by the `on_dns_resolvehost_start` signal"""

    host: str


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceDnsResolveHostEndParams:
    """Parameters sent by the `on_dns_resolvehost_end` signal"""

    host: str


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceDnsCacheHitParams:
    """Parameters sent by the `on_dns_cache_hit` signal"""

    host: str


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceDnsCacheMissParams:
    """Parameters sent by the `on_dns_cache_miss` signal"""

    host: str


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceRequestHeadersSentParams:
    """Parameters sent by the `on_request_headers_sent` signal"""

    method: str
    url: URL
    headers: "CIMultiDict[str]"


class Trace:
    """Internal dependency holder class.

    Used to keep together the main dependencies used
    at the moment of send a signal.
    """

    def __init__(
        self,
        session: "ClientSession",
        trace_config: TraceConfig,
        trace_config_ctx: SimpleNamespace,
    ) -> None:
        self._trace_config = trace_config
        self._trace_config_ctx = trace_config_ctx
        self._session = session

    async def send_request_start(
        self, method: str, url: URL, headers: "CIMultiDict[str]"
    ) -> None:
        return await self._trace_config.on_request_start.send(
            self._session,
            self._trace_config_ctx,
            TraceRequestStartParams(method, url, headers),
        )

    async def send_request_chunk_sent(
        self, method: str, url: URL, chunk: bytes
    ) -> None:
        return await self._trace_config.on_request_chunk_sent.send(
            self._session,
            self._trace_config_ctx,
            TraceRequestChunkSentParams(method, url, chunk),
        )

    async def send_response_chunk_received(
        self, method: str, url: URL, chunk: bytes
    ) -> None:
        return await self._trace_config.on_response_chunk_received.send(
            self._session,
            self._trace_config_ctx,
            TraceResponseChunkReceivedParams(method, url, chunk),
        )

    async def send_request_end(
        self,
        method: str,
        url: URL,
        headers: "CIMultiDict[str]",
        response: ClientResponse,
    ) -> None:
        return await self._trace_config.on_request_end.send(
            self._session,
            self._trace_config_ctx,
            TraceRequestEndParams(method, url, headers, response),
        )

    async def send_request_exception(
        self,
        method: str,
        url: URL,
        headers: "CIMultiDict[str]",
        exception: BaseException,
    ) -> None:
        return await self._trace_config.on_request_exception.send(
            self._session,
            self._trace_config_ctx,
            TraceRequestExceptionParams(method, url, headers, exception),
        )

    async def send_request_redirect(
        self,
        method: str,
        url: URL,
        headers: "CIMultiDict[str]",
        response: ClientResponse,
    ) -> None:
        return await self._trace_config._on_request_redirect.send(
            self._session,
            self._trace_config_ctx,
            TraceRequestRedirectParams(method, url, headers, response),
        )

    async def send_connection_queued_start(self) -> None:
        return await self._trace_config.on_connection_queued_start.send(
            self._session, self._trace_config_ctx, TraceConnectionQueuedStartParams()
        )

    async def send_connection_queued_end(self) -> None:
        return await self._trace_config.on_connection_queued_end.send(
            self._session, self._trace_config_ctx, TraceConnectionQueuedEndParams()
        )

    async def send_connection_create_start(self) -> None:
        return await self._trace_config.on_connection_create_start.send(
            self._session, self._trace_config_ctx, TraceConnectionCreateStartParams()
        )

    async def send_connection_create_end(self) -> None:
        return await self._trace_config.on_connection_create_end.send(
            self._session, self._trace_config_ctx, TraceConnectionCreateEndParams()
        )

    async def send_connection_reuseconn(self) -> None:
        return await self._trace_config.on_connection_reuseconn.send(
            self._session, self._trace_config_ctx, TraceConnectionReuseconnParams()
        )

    async def send_dns_resolvehost_start(self, host: str) -> None:
        return await self._trace_config.on_dns_resolvehost_start.send(
            self._session, self._trace_config_ctx, TraceDnsResolveHostStartParams(host)
        )

    async def send_dns_resolvehost_end(self, host: str) -> None:
        return await self._trace_config.on_dns_resolvehost_end.send(
            self._session, self._trace_config_ctx, TraceDnsResolveHostEndParams(host)
        )

    async def send_dns_cache_hit(self, host: str) -> None:
        return await self._trace_config.on_dns_cache_hit.send(
            self._session, self._trace_config_ctx, TraceDnsCacheHitParams(host)
        )

    async def send_dns_cache_miss(self, host: str) -> None:
        return await self._trace_config.on_dns_cache_miss.send(
            self._session, self._trace_config_ctx, TraceDnsCacheMissParams(host)
        )

    async def send_request_headers(
        self, method: str, url: URL, headers: "CIMultiDict[str]"
    ) -> None:
        return await self._trace_config._on_request_headers_sent.send(
            self._session,
            self._trace_config_ctx,
            TraceRequestHeadersSentParams(method, url, headers),
        )
