import asyncio
import codecs
import contextlib
import functools
import io
import re
import sys
import traceback
import warnings
from hashlib import md5, sha1, sha256
from http.cookies import CookieError, Morsel, SimpleCookie
from types import MappingProxyType, TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)

import attr
from multidict import CIMultiDict, CIMultiDictProxy, MultiDict, MultiDictProxy
from yarl import URL

from . import hdrs, helpers, http, multipart, payload
from .abc import AbstractStreamWriter
from .client_exceptions import (
    ClientConnectionError,
    ClientOSError,
    ClientResponseError,
    ContentTypeError,
    InvalidURL,
    ServerFingerprintMismatch,
)
from .compression_utils import HAS_BROTLI
from .formdata import FormData
from .helpers import (
    BaseTimerContext,
    BasicAuth,
    HeadersMixin,
    TimerNoop,
    basicauth_from_netrc,
    netrc_from_env,
    noop,
    reify,
    set_result,
)
from .http import (
    SERVER_SOFTWARE,
    HttpVersion,
    HttpVersion10,
    HttpVersion11,
    StreamWriter,
)
from .log import client_logger
from .streams import StreamReader
from .typedefs import (
    DEFAULT_JSON_DECODER,
    JSONDecoder,
    LooseCookies,
    LooseHeaders,
    RawHeaders,
)

try:
    import ssl
    from ssl import SSLContext
except ImportError:  # pragma: no cover
    ssl = None  # type: ignore[assignment]
    SSLContext = object  # type: ignore[misc,assignment]


__all__ = ("ClientRequest", "ClientResponse", "RequestInfo", "Fingerprint")


if TYPE_CHECKING:
    from .client import ClientSession
    from .connector import Connection
    from .tracing import Trace


_CONTAINS_CONTROL_CHAR_RE = re.compile(r"[^-!#$%&'*+.^_`|~0-9a-zA-Z]")
json_re = re.compile(r"^application/(?:[\w.+-]+?\+)?json")


def _gen_default_accept_encoding() -> str:
    return "gzip, deflate, br" if HAS_BROTLI else "gzip, deflate"


@attr.s(auto_attribs=True, frozen=True, slots=True)
class ContentDisposition:
    type: Optional[str]
    parameters: "MappingProxyType[str, str]"
    filename: Optional[str]


@attr.s(auto_attribs=True, frozen=True, slots=True)
class RequestInfo:
    url: URL
    method: str
    headers: "CIMultiDictProxy[str]"
    real_url: URL = attr.ib()

    @real_url.default
    def real_url_default(self) -> URL:
        return self.url


class Fingerprint:
    HASHFUNC_BY_DIGESTLEN = {
        16: md5,
        20: sha1,
        32: sha256,
    }

    def __init__(self, fingerprint: bytes) -> None:
        digestlen = len(fingerprint)
        hashfunc = self.HASHFUNC_BY_DIGESTLEN.get(digestlen)
        if not hashfunc:
            raise ValueError("fingerprint has invalid length")
        elif hashfunc is md5 or hashfunc is sha1:
            raise ValueError(
                "md5 and sha1 are insecure and " "not supported. Use sha256."
            )
        self._hashfunc = hashfunc
        self._fingerprint = fingerprint

    @property
    def fingerprint(self) -> bytes:
        return self._fingerprint

    def check(self, transport: asyncio.Transport) -> None:
        if not transport.get_extra_info("sslcontext"):
            return
        sslobj = transport.get_extra_info("ssl_object")
        cert = sslobj.getpeercert(binary_form=True)
        got = self._hashfunc(cert).digest()
        if got != self._fingerprint:
            host, port, *_ = transport.get_extra_info("peername")
            raise ServerFingerprintMismatch(self._fingerprint, got, host, port)


if ssl is not None:
    SSL_ALLOWED_TYPES = (ssl.SSLContext, bool, Fingerprint, type(None))
else:  # pragma: no cover
    SSL_ALLOWED_TYPES = (bool, type(None))


def _merge_ssl_params(
    ssl: Union["SSLContext", bool, Fingerprint],
    verify_ssl: Optional[bool],
    ssl_context: Optional["SSLContext"],
    fingerprint: Optional[bytes],
) -> Union["SSLContext", bool, Fingerprint]:
    if ssl is None:
        ssl = True  # Double check for backwards compatibility
    if verify_ssl is not None and not verify_ssl:
        warnings.warn(
            "verify_ssl is deprecated, use ssl=False instead",
            DeprecationWarning,
            stacklevel=3,
        )
        if ssl is not True:
            raise ValueError(
                "verify_ssl, ssl_context, fingerprint and ssl "
                "parameters are mutually exclusive"
            )
        else:
            ssl = False
    if ssl_context is not None:
        warnings.warn(
            "ssl_context is deprecated, use ssl=context instead",
            DeprecationWarning,
            stacklevel=3,
        )
        if ssl is not True:
            raise ValueError(
                "verify_ssl, ssl_context, fingerprint and ssl "
                "parameters are mutually exclusive"
            )
        else:
            ssl = ssl_context
    if fingerprint is not None:
        warnings.warn(
            "fingerprint is deprecated, " "use ssl=Fingerprint(fingerprint) instead",
            DeprecationWarning,
            stacklevel=3,
        )
        if ssl is not True:
            raise ValueError(
                "verify_ssl, ssl_context, fingerprint and ssl "
                "parameters are mutually exclusive"
            )
        else:
            ssl = Fingerprint(fingerprint)
    if not isinstance(ssl, SSL_ALLOWED_TYPES):
        raise TypeError(
            "ssl should be SSLContext, bool, Fingerprint or None, "
            "got {!r} instead.".format(ssl)
        )
    return ssl


@attr.s(auto_attribs=True, slots=True, frozen=True)
class ConnectionKey:
    # the key should contain an information about used proxy / TLS
    # to prevent reusing wrong connections from a pool
    host: str
    port: Optional[int]
    is_ssl: bool
    ssl: Union[SSLContext, bool, Fingerprint]
    proxy: Optional[URL]
    proxy_auth: Optional[BasicAuth]
    proxy_headers_hash: Optional[int]  # hash(CIMultiDict)


def _is_expected_content_type(
    response_content_type: str, expected_content_type: str
) -> bool:
    if expected_content_type == "application/json":
        return json_re.match(response_content_type) is not None
    return expected_content_type in response_content_type


class ClientRequest:
    GET_METHODS = {
        hdrs.METH_GET,
        hdrs.METH_HEAD,
        hdrs.METH_OPTIONS,
        hdrs.METH_TRACE,
    }
    POST_METHODS = {hdrs.METH_PATCH, hdrs.METH_POST, hdrs.METH_PUT}
    ALL_METHODS = GET_METHODS.union(POST_METHODS).union({hdrs.METH_DELETE})

    DEFAULT_HEADERS = {
        hdrs.ACCEPT: "*/*",
        hdrs.ACCEPT_ENCODING: _gen_default_accept_encoding(),
    }

    body = b""
    auth = None
    response = None

    __writer = None  # async task for streaming data
    _continue = None  # waiter future for '100 Continue' response

    # N.B.
    # Adding __del__ method with self._writer closing doesn't make sense
    # because _writer is instance method, thus it keeps a reference to self.
    # Until writer has finished finalizer will not be called.

    def __init__(
        self,
        method: str,
        url: URL,
        *,
        params: Optional[Mapping[str, str]] = None,
        headers: Optional[LooseHeaders] = None,
        skip_auto_headers: Iterable[str] = frozenset(),
        data: Any = None,
        cookies: Optional[LooseCookies] = None,
        auth: Optional[BasicAuth] = None,
        version: http.HttpVersion = http.HttpVersion11,
        compress: Optional[str] = None,
        chunked: Optional[bool] = None,
        expect100: bool = False,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        response_class: Optional[Type["ClientResponse"]] = None,
        proxy: Optional[URL] = None,
        proxy_auth: Optional[BasicAuth] = None,
        timer: Optional[BaseTimerContext] = None,
        session: Optional["ClientSession"] = None,
        ssl: Union[SSLContext, bool, Fingerprint] = True,
        proxy_headers: Optional[LooseHeaders] = None,
        traces: Optional[List["Trace"]] = None,
        trust_env: bool = False,
        server_hostname: Optional[str] = None,
    ):
        if loop is None:
            loop = asyncio.get_event_loop()

        match = _CONTAINS_CONTROL_CHAR_RE.search(method)
        if match:
            raise ValueError(
                f"Method cannot contain non-token characters {method!r} "
                "(found at least {match.group()!r})"
            )

        assert isinstance(url, URL), url
        assert isinstance(proxy, (URL, type(None))), proxy
        # FIXME: session is None in tests only, need to fix tests
        # assert session is not None
        self._session = cast("ClientSession", session)
        if params:
            q = MultiDict(url.query)
            url2 = url.with_query(params)
            q.extend(url2.query)
            url = url.with_query(q)
        self.original_url = url
        self.url = url.with_fragment(None)
        self.method = method.upper()
        self.chunked = chunked
        self.compress = compress
        self.loop = loop
        self.length = None
        if response_class is None:
            real_response_class = ClientResponse
        else:
            real_response_class = response_class
        self.response_class: Type[ClientResponse] = real_response_class
        self._timer = timer if timer is not None else TimerNoop()
        self._ssl = ssl if ssl is not None else True
        self.server_hostname = server_hostname

        if loop.get_debug():
            self._source_traceback = traceback.extract_stack(sys._getframe(1))

        self.update_version(version)
        self.update_host(url)
        self.update_headers(headers)
        self.update_auto_headers(skip_auto_headers)
        self.update_cookies(cookies)
        self.update_content_encoding(data)
        self.update_auth(auth, trust_env)
        self.update_proxy(proxy, proxy_auth, proxy_headers)

        self.update_body_from_data(data)
        if data is not None or self.method not in self.GET_METHODS:
            self.update_transfer_encoding()
        self.update_expect_continue(expect100)
        if traces is None:
            traces = []
        self._traces = traces

    def __reset_writer(self, _: object = None) -> None:
        self.__writer = None

    @property
    def _writer(self) -> Optional["asyncio.Task[None]"]:
        return self.__writer

    @_writer.setter
    def _writer(self, writer: Optional["asyncio.Task[None]"]) -> None:
        if self.__writer is not None:
            self.__writer.remove_done_callback(self.__reset_writer)
        self.__writer = writer
        if writer is not None:
            writer.add_done_callback(self.__reset_writer)

    def is_ssl(self) -> bool:
        return self.url.scheme in ("https", "wss")

    @property
    def ssl(self) -> Union["SSLContext", bool, Fingerprint]:
        return self._ssl

    @property
    def connection_key(self) -> ConnectionKey:
        proxy_headers = self.proxy_headers
        if proxy_headers:
            h: Optional[int] = hash(tuple((k, v) for k, v in proxy_headers.items()))
        else:
            h = None
        return ConnectionKey(
            self.host,
            self.port,
            self.is_ssl(),
            self.ssl,
            self.proxy,
            self.proxy_auth,
            h,
        )

    @property
    def host(self) -> str:
        ret = self.url.raw_host
        assert ret is not None
        return ret

    @property
    def port(self) -> Optional[int]:
        return self.url.port

    @property
    def request_info(self) -> RequestInfo:
        headers: CIMultiDictProxy[str] = CIMultiDictProxy(self.headers)
        return RequestInfo(self.url, self.method, headers, self.original_url)

    def update_host(self, url: URL) -> None:
        """Update destination host, port and connection type (ssl)."""
        # get host/port
        if not url.raw_host:
            raise InvalidURL(url)

        # basic auth info
        username, password = url.user, url.password
        if username:
            self.auth = helpers.BasicAuth(username, password or "")

    def update_version(self, version: Union[http.HttpVersion, str]) -> None:
        """Convert request version to two elements tuple.

        parser HTTP version '1.1' => (1, 1)
        """
        if isinstance(version, str):
            v = [part.strip() for part in version.split(".", 1)]
            try:
                version = http.HttpVersion(int(v[0]), int(v[1]))
            except ValueError:
                raise ValueError(
                    f"Can not parse http version number: {version}"
                ) from None
        self.version = version

    def update_headers(self, headers: Optional[LooseHeaders]) -> None:
        """Update request headers."""
        self.headers: CIMultiDict[str] = CIMultiDict()

        # add host
        netloc = cast(str, self.url.raw_host)
        if helpers.is_ipv6_address(netloc):
            netloc = f"[{netloc}]"
        # See https://github.com/aio-libs/aiohttp/issues/3636.
        netloc = netloc.rstrip(".")
        if self.url.port is not None and not self.url.is_default_port():
            netloc += ":" + str(self.url.port)
        self.headers[hdrs.HOST] = netloc

        if headers:
            if isinstance(headers, (dict, MultiDictProxy, MultiDict)):
                headers = headers.items()  # type: ignore[assignment]

            for key, value in headers:  # type: ignore[misc]
                # A special case for Host header
                if key.lower() == "host":
                    self.headers[key] = value
                else:
                    self.headers.add(key, value)

    def update_auto_headers(self, skip_auto_headers: Iterable[str]) -> None:
        self.skip_auto_headers = CIMultiDict(
            (hdr, None) for hdr in sorted(skip_auto_headers)
        )
        used_headers = self.headers.copy()
        used_headers.extend(self.skip_auto_headers)  # type: ignore[arg-type]

        for hdr, val in self.DEFAULT_HEADERS.items():
            if hdr not in used_headers:
                self.headers.add(hdr, val)

        if hdrs.USER_AGENT not in used_headers:
            self.headers[hdrs.USER_AGENT] = SERVER_SOFTWARE

    def update_cookies(self, cookies: Optional[LooseCookies]) -> None:
        """Update request cookies header."""
        if not cookies:
            return

        c = SimpleCookie()
        if hdrs.COOKIE in self.headers:
            c.load(self.headers.get(hdrs.COOKIE, ""))
            del self.headers[hdrs.COOKIE]

        if isinstance(cookies, Mapping):
            iter_cookies = cookies.items()
        else:
            iter_cookies = cookies  # type: ignore[assignment]
        for name, value in iter_cookies:
            if isinstance(value, Morsel):
                # Preserve coded_value
                mrsl_val = value.get(value.key, Morsel())
                mrsl_val.set(value.key, value.value, value.coded_value)
                c[name] = mrsl_val
            else:
                c[name] = value  # type: ignore[assignment]

        self.headers[hdrs.COOKIE] = c.output(header="", sep=";").strip()

    def update_content_encoding(self, data: Any) -> None:
        """Set request content encoding."""
        if data is None:
            return

        enc = self.headers.get(hdrs.CONTENT_ENCODING, "").lower()
        if enc:
            if self.compress:
                raise ValueError(
                    "compress can not be set " "if Content-Encoding header is set"
                )
        elif self.compress:
            if not isinstance(self.compress, str):
                self.compress = "deflate"
            self.headers[hdrs.CONTENT_ENCODING] = self.compress
            self.chunked = True  # enable chunked, no need to deal with length

    def update_transfer_encoding(self) -> None:
        """Analyze transfer-encoding header."""
        te = self.headers.get(hdrs.TRANSFER_ENCODING, "").lower()

        if "chunked" in te:
            if self.chunked:
                raise ValueError(
                    "chunked can not be set "
                    'if "Transfer-Encoding: chunked" header is set'
                )

        elif self.chunked:
            if hdrs.CONTENT_LENGTH in self.headers:
                raise ValueError(
                    "chunked can not be set " "if Content-Length header is set"
                )

            self.headers[hdrs.TRANSFER_ENCODING] = "chunked"
        else:
            if hdrs.CONTENT_LENGTH not in self.headers:
                self.headers[hdrs.CONTENT_LENGTH] = str(len(self.body))

    def update_auth(self, auth: Optional[BasicAuth], trust_env: bool = False) -> None:
        """Set basic auth."""
        if auth is None:
            auth = self.auth
        if auth is None and trust_env and self.url.host is not None:
            netrc_obj = netrc_from_env()
            with contextlib.suppress(LookupError):
                auth = basicauth_from_netrc(netrc_obj, self.url.host)
        if auth is None:
            return

        if not isinstance(auth, helpers.BasicAuth):
            raise TypeError("BasicAuth() tuple is required instead")

        self.headers[hdrs.AUTHORIZATION] = auth.encode()

    def update_body_from_data(self, body: Any) -> None:
        if body is None:
            return

        # FormData
        if isinstance(body, FormData):
            body = body()

        try:
            body = payload.PAYLOAD_REGISTRY.get(body, disposition=None)
        except payload.LookupError:
            body = FormData(body)()

        self.body = body

        # enable chunked encoding if needed
        if not self.chunked:
            if hdrs.CONTENT_LENGTH not in self.headers:
                size = body.size
                if size is None:
                    self.chunked = True
                else:
                    if hdrs.CONTENT_LENGTH not in self.headers:
                        self.headers[hdrs.CONTENT_LENGTH] = str(size)

        # copy payload headers
        assert body.headers
        for (key, value) in body.headers.items():
            if key in self.headers:
                continue
            if key in self.skip_auto_headers:
                continue
            self.headers[key] = value

    def update_expect_continue(self, expect: bool = False) -> None:
        if expect:
            self.headers[hdrs.EXPECT] = "100-continue"
        elif self.headers.get(hdrs.EXPECT, "").lower() == "100-continue":
            expect = True

        if expect:
            self._continue = self.loop.create_future()

    def update_proxy(
        self,
        proxy: Optional[URL],
        proxy_auth: Optional[BasicAuth],
        proxy_headers: Optional[LooseHeaders],
    ) -> None:
        if proxy_auth and not isinstance(proxy_auth, helpers.BasicAuth):
            raise ValueError("proxy_auth must be None or BasicAuth() tuple")
        self.proxy = proxy
        self.proxy_auth = proxy_auth
        self.proxy_headers = proxy_headers

    def keep_alive(self) -> bool:
        if self.version < HttpVersion10:
            # keep alive not supported at all
            return False
        if self.version == HttpVersion10:
            if self.headers.get(hdrs.CONNECTION) == "keep-alive":
                return True
            else:  # no headers means we close for Http 1.0
                return False
        elif self.headers.get(hdrs.CONNECTION) == "close":
            return False

        return True

    async def write_bytes(
        self, writer: AbstractStreamWriter, conn: "Connection"
    ) -> None:
        """Support coroutines that yields bytes objects."""
        # 100 response
        if self._continue is not None:
            try:
                await writer.drain()
                await self._continue
            except asyncio.CancelledError:
                return

        protocol = conn.protocol
        assert protocol is not None
        try:
            if isinstance(self.body, payload.Payload):
                await self.body.write(writer)
            else:
                if isinstance(self.body, (bytes, bytearray)):
                    self.body = (self.body,)  # type: ignore[assignment]

                for chunk in self.body:
                    await writer.write(chunk)  # type: ignore[arg-type]
        except OSError as exc:
            if exc.errno is None and isinstance(exc, asyncio.TimeoutError):
                protocol.set_exception(exc)
            else:
                new_exc = ClientOSError(
                    exc.errno, "Can not write request body for %s" % self.url
                )
                new_exc.__context__ = exc
                new_exc.__cause__ = exc
                protocol.set_exception(new_exc)
        except asyncio.CancelledError:
            await writer.write_eof()
        except Exception as exc:
            protocol.set_exception(exc)
        else:
            await writer.write_eof()
            protocol.start_timeout()

    async def send(self, conn: "Connection") -> "ClientResponse":
        # Specify request target:
        # - CONNECT request must send authority form URI
        # - not CONNECT proxy must send absolute form URI
        # - most common is origin form URI
        if self.method == hdrs.METH_CONNECT:
            connect_host = self.url.raw_host
            assert connect_host is not None
            if helpers.is_ipv6_address(connect_host):
                connect_host = f"[{connect_host}]"
            path = f"{connect_host}:{self.url.port}"
        elif self.proxy and not self.is_ssl():
            path = str(self.url)
        else:
            path = self.url.raw_path
            if self.url.raw_query_string:
                path += "?" + self.url.raw_query_string

        protocol = conn.protocol
        assert protocol is not None
        writer = StreamWriter(
            protocol,
            self.loop,
            on_chunk_sent=functools.partial(
                self._on_chunk_request_sent, self.method, self.url
            ),
            on_headers_sent=functools.partial(
                self._on_headers_request_sent, self.method, self.url
            ),
        )

        if self.compress:
            writer.enable_compression(self.compress)

        if self.chunked is not None:
            writer.enable_chunking()

        # set default content-type
        if (
            self.method in self.POST_METHODS
            and hdrs.CONTENT_TYPE not in self.skip_auto_headers
            and hdrs.CONTENT_TYPE not in self.headers
        ):
            self.headers[hdrs.CONTENT_TYPE] = "application/octet-stream"

        # set the connection header
        connection = self.headers.get(hdrs.CONNECTION)
        if not connection:
            if self.keep_alive():
                if self.version == HttpVersion10:
                    connection = "keep-alive"
            else:
                if self.version == HttpVersion11:
                    connection = "close"

        if connection is not None:
            self.headers[hdrs.CONNECTION] = connection

        # status + headers
        status_line = "{0} {1} HTTP/{v.major}.{v.minor}".format(
            self.method, path, v=self.version
        )
        await writer.write_headers(status_line, self.headers)

        self._writer = self.loop.create_task(self.write_bytes(writer, conn))

        response_class = self.response_class
        assert response_class is not None
        self.response = response_class(
            self.method,
            self.original_url,
            writer=self._writer,
            continue100=self._continue,
            timer=self._timer,
            request_info=self.request_info,
            traces=self._traces,
            loop=self.loop,
            session=self._session,
        )
        return self.response

    async def close(self) -> None:
        if self._writer is not None:
            with contextlib.suppress(asyncio.CancelledError):
                await self._writer

    def terminate(self) -> None:
        if self._writer is not None:
            if not self.loop.is_closed():
                self._writer.cancel()
            self._writer.remove_done_callback(self.__reset_writer)
            self._writer = None

    async def _on_chunk_request_sent(self, method: str, url: URL, chunk: bytes) -> None:
        for trace in self._traces:
            await trace.send_request_chunk_sent(method, url, chunk)

    async def _on_headers_request_sent(
        self, method: str, url: URL, headers: "CIMultiDict[str]"
    ) -> None:
        for trace in self._traces:
            await trace.send_request_headers(method, url, headers)


class ClientResponse(HeadersMixin):

    # Some of these attributes are None when created,
    # but will be set by the start() method.
    # As the end user will likely never see the None values, we cheat the types below.
    # from the Status-Line of the response
    version: Optional[HttpVersion] = None  # HTTP-Version
    status: int = None  # type: ignore[assignment] # Status-Code
    reason: Optional[str] = None  # Reason-Phrase

    content: StreamReader = None  # type: ignore[assignment]  # Payload stream
    _headers: CIMultiDictProxy[str] = None  # type: ignore[assignment]
    _raw_headers: RawHeaders = None  # type: ignore[assignment]

    _connection = None  # current connection
    _source_traceback: Optional[traceback.StackSummary] = None
    # set up by ClientRequest after ClientResponse object creation
    # post-init stage allows to not change ctor signature
    _closed = True  # to allow __del__ for non-initialized properly response
    _released = False
    __writer = None

    def __init__(
        self,
        method: str,
        url: URL,
        *,
        writer: "asyncio.Task[None]",
        continue100: Optional["asyncio.Future[bool]"],
        timer: BaseTimerContext,
        request_info: RequestInfo,
        traces: List["Trace"],
        loop: asyncio.AbstractEventLoop,
        session: "ClientSession",
    ) -> None:
        assert isinstance(url, URL)

        self.method = method
        self.cookies = SimpleCookie()

        self._real_url = url
        self._url = url.with_fragment(None)
        self._body: Any = None
        self._writer: Optional[asyncio.Task[None]] = writer
        self._continue = continue100  # None by default
        self._closed = True
        self._history: Tuple[ClientResponse, ...] = ()
        self._request_info = request_info
        self._timer = timer if timer is not None else TimerNoop()
        self._cache: Dict[str, Any] = {}
        self._traces = traces
        self._loop = loop
        # store a reference to session #1985
        self._session: Optional[ClientSession] = session
        # Save reference to _resolve_charset, so that get_encoding() will still
        # work after the response has finished reading the body.
        if session is None:
            # TODO: Fix session=None in tests (see ClientRequest.__init__).
            self._resolve_charset: Callable[
                ["ClientResponse", bytes], str
            ] = lambda *_: "utf-8"
        else:
            self._resolve_charset = session._resolve_charset
        if loop.get_debug():
            self._source_traceback = traceback.extract_stack(sys._getframe(1))

    def __reset_writer(self, _: object = None) -> None:
        self.__writer = None

    @property
    def _writer(self) -> Optional["asyncio.Task[None]"]:
        return self.__writer

    @_writer.setter
    def _writer(self, writer: Optional["asyncio.Task[None]"]) -> None:
        if self.__writer is not None:
            self.__writer.remove_done_callback(self.__reset_writer)
        self.__writer = writer
        if writer is not None:
            writer.add_done_callback(self.__reset_writer)

    @reify
    def url(self) -> URL:
        return self._url

    @reify
    def url_obj(self) -> URL:
        warnings.warn("Deprecated, use .url #1654", DeprecationWarning, stacklevel=2)
        return self._url

    @reify
    def real_url(self) -> URL:
        return self._real_url

    @reify
    def host(self) -> str:
        assert self._url.host is not None
        return self._url.host

    @reify
    def headers(self) -> "CIMultiDictProxy[str]":
        return self._headers

    @reify
    def raw_headers(self) -> RawHeaders:
        return self._raw_headers

    @reify
    def request_info(self) -> RequestInfo:
        return self._request_info

    @reify
    def content_disposition(self) -> Optional[ContentDisposition]:
        raw = self._headers.get(hdrs.CONTENT_DISPOSITION)
        if raw is None:
            return None
        disposition_type, params_dct = multipart.parse_content_disposition(raw)
        params = MappingProxyType(params_dct)
        filename = multipart.content_disposition_filename(params)
        return ContentDisposition(disposition_type, params, filename)

    def __del__(self, _warnings: Any = warnings) -> None:
        if self._closed:
            return

        if self._connection is not None:
            self._connection.release()
            self._cleanup_writer()

            if self._loop.get_debug():
                kwargs = {"source": self}
                _warnings.warn(f"Unclosed response {self!r}", ResourceWarning, **kwargs)
                context = {"client_response": self, "message": "Unclosed response"}
                if self._source_traceback:
                    context["source_traceback"] = self._source_traceback
                self._loop.call_exception_handler(context)

    def __repr__(self) -> str:
        out = io.StringIO()
        ascii_encodable_url = str(self.url)
        if self.reason:
            ascii_encodable_reason = self.reason.encode(
                "ascii", "backslashreplace"
            ).decode("ascii")
        else:
            ascii_encodable_reason = "None"
        print(
            "<ClientResponse({}) [{} {}]>".format(
                ascii_encodable_url, self.status, ascii_encodable_reason
            ),
            file=out,
        )
        print(self.headers, file=out)
        return out.getvalue()

    @property
    def connection(self) -> Optional["Connection"]:
        return self._connection

    @reify
    def history(self) -> Tuple["ClientResponse", ...]:
        """A sequence of of responses, if redirects occurred."""
        return self._history

    @reify
    def links(self) -> "MultiDictProxy[MultiDictProxy[Union[str, URL]]]":
        links_str = ", ".join(self.headers.getall("link", []))

        if not links_str:
            return MultiDictProxy(MultiDict())

        links: MultiDict[MultiDictProxy[Union[str, URL]]] = MultiDict()

        for val in re.split(r",(?=\s*<)", links_str):
            match = re.match(r"\s*<(.*)>(.*)", val)
            if match is None:  # pragma: no cover
                # the check exists to suppress mypy error
                continue
            url, params_str = match.groups()
            params = params_str.split(";")[1:]

            link: MultiDict[Union[str, URL]] = MultiDict()

            for param in params:
                match = re.match(r"^\s*(\S*)\s*=\s*(['\"]?)(.*?)(\2)\s*$", param, re.M)
                if match is None:  # pragma: no cover
                    # the check exists to suppress mypy error
                    continue
                key, _, value, _ = match.groups()

                link.add(key, value)

            key = link.get("rel", url)

            link.add("url", self.url.join(URL(url)))

            links.add(str(key), MultiDictProxy(link))

        return MultiDictProxy(links)

    async def start(self, connection: "Connection") -> "ClientResponse":
        """Start response processing."""
        self._closed = False
        self._protocol = connection.protocol
        self._connection = connection

        with self._timer:
            while True:
                # read response
                try:
                    protocol = self._protocol
                    message, payload = await protocol.read()  # type: ignore[union-attr]
                except http.HttpProcessingError as exc:
                    raise ClientResponseError(
                        self.request_info,
                        self.history,
                        status=exc.code,
                        message=exc.message,
                        headers=exc.headers,
                    ) from exc

                if message.code < 100 or message.code > 199 or message.code == 101:
                    break

                if self._continue is not None:
                    set_result(self._continue, True)
                    self._continue = None

        # payload eof handler
        payload.on_eof(self._response_eof)

        # response status
        self.version = message.version
        self.status = message.code
        self.reason = message.reason

        # headers
        self._headers = message.headers  # type is CIMultiDictProxy
        self._raw_headers = message.raw_headers  # type is Tuple[bytes, bytes]

        # payload
        self.content = payload

        # cookies
        for hdr in self.headers.getall(hdrs.SET_COOKIE, ()):
            try:
                self.cookies.load(hdr)
            except CookieError as exc:
                client_logger.warning("Can not load response cookies: %s", exc)
        return self

    def _response_eof(self) -> None:
        if self._closed:
            return

        # protocol could be None because connection could be detached
        protocol = self._connection and self._connection.protocol
        if protocol is not None and protocol.upgraded:
            return

        self._closed = True
        self._cleanup_writer()
        self._release_connection()

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        if not self._released:
            self._notify_content()

        self._closed = True
        if self._loop is None or self._loop.is_closed():
            return

        self._cleanup_writer()
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def release(self) -> Any:
        if not self._released:
            self._notify_content()

        self._closed = True

        self._cleanup_writer()
        self._release_connection()
        return noop()

    @property
    def ok(self) -> bool:
        """Returns ``True`` if ``status`` is less than ``400``, ``False`` if not.

        This is **not** a check for ``200 OK`` but a check that the response
        status is under 400.
        """
        return 400 > self.status

    def raise_for_status(self) -> None:
        if not self.ok:
            # reason should always be not None for a started response
            assert self.reason is not None
            self.release()
            raise ClientResponseError(
                self.request_info,
                self.history,
                status=self.status,
                message=self.reason,
                headers=self.headers,
            )

    def _release_connection(self) -> None:
        if self._connection is not None:
            if self._writer is None:
                self._connection.release()
                self._connection = None
            else:
                self._writer.add_done_callback(lambda f: self._release_connection())

    async def _wait_released(self) -> None:
        if self._writer is not None:
            await self._writer
        self._release_connection()

    def _cleanup_writer(self) -> None:
        if self._writer is not None:
            self._writer.cancel()
        self._session = None

    def _notify_content(self) -> None:
        content = self.content
        if content and content.exception() is None:
            content.set_exception(ClientConnectionError("Connection closed"))
        self._released = True

    async def wait_for_close(self) -> None:
        if self._writer is not None:
            await self._writer
        self.release()

    async def read(self) -> bytes:
        """Read response payload."""
        if self._body is None:
            try:
                self._body = await self.content.read()
                for trace in self._traces:
                    await trace.send_response_chunk_received(
                        self.method, self.url, self._body
                    )
            except BaseException:
                self.close()
                raise
        elif self._released:  # Response explicitly released
            raise ClientConnectionError("Connection closed")

        protocol = self._connection and self._connection.protocol
        if protocol is None or not protocol.upgraded:
            await self._wait_released()  # Underlying connection released
        return self._body  # type: ignore[no-any-return]

    def get_encoding(self) -> str:
        ctype = self.headers.get(hdrs.CONTENT_TYPE, "").lower()
        mimetype = helpers.parse_mimetype(ctype)

        encoding = mimetype.parameters.get("charset")
        if encoding:
            with contextlib.suppress(LookupError):
                return codecs.lookup(encoding).name

        if mimetype.type == "application" and (
            mimetype.subtype == "json" or mimetype.subtype == "rdap"
        ):
            # RFC 7159 states that the default encoding is UTF-8.
            # RFC 7483 defines application/rdap+json
            return "utf-8"

        if self._body is None:
            raise RuntimeError(
                "Cannot compute fallback encoding of a not yet read body"
            )

        return self._resolve_charset(self, self._body)

    async def text(self, encoding: Optional[str] = None, errors: str = "strict") -> str:
        """Read response payload and decode."""
        if self._body is None:
            await self.read()

        if encoding is None:
            encoding = self.get_encoding()

        return self._body.decode(  # type: ignore[no-any-return,union-attr]
            encoding, errors=errors
        )

    async def json(
        self,
        *,
        encoding: Optional[str] = None,
        loads: JSONDecoder = DEFAULT_JSON_DECODER,
        content_type: Optional[str] = "application/json",
    ) -> Any:
        """Read and decodes JSON response."""
        if self._body is None:
            await self.read()

        if content_type:
            ctype = self.headers.get(hdrs.CONTENT_TYPE, "").lower()
            if not _is_expected_content_type(ctype, content_type):
                raise ContentTypeError(
                    self.request_info,
                    self.history,
                    message=(
                        "Attempt to decode JSON with " "unexpected mimetype: %s" % ctype
                    ),
                    headers=self.headers,
                )

        stripped = self._body.strip()  # type: ignore[union-attr]
        if not stripped:
            return None

        if encoding is None:
            encoding = self.get_encoding()

        return loads(stripped.decode(encoding))

    async def __aenter__(self) -> "ClientResponse":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        # similar to _RequestContextManager, we do not need to check
        # for exceptions, response object can close connection
        # if state is broken
        self.release()
        await self.wait_for_close()
