import asyncio
import codecs
import contextlib
import functools
import io
import re
import sys
import traceback
import warnings
from collections.abc import Mapping
from hashlib import md5, sha1, sha256
from http.cookies import Morsel, SimpleCookie
from types import MappingProxyType, TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Literal,
    NamedTuple,
    Optional,
    Tuple,
    Type,
    Union,
)

import attr
from multidict import CIMultiDict, CIMultiDictProxy, MultiDict, MultiDictProxy
from yarl import URL

from . import hdrs, helpers, http, multipart, payload
from ._cookie_helpers import (
    parse_cookie_header,
    parse_set_cookie_headers,
    preserve_morsel_with_coded_value,
)
from .abc import AbstractStreamWriter
from .client_exceptions import (
    ClientConnectionError,
    ClientOSError,
    ClientResponseError,
    ContentTypeError,
    InvalidURL,
    ServerFingerprintMismatch,
)
from .compression_utils import HAS_BROTLI, HAS_ZSTD
from .formdata import FormData
from .helpers import (
    _SENTINEL,
    BaseTimerContext,
    BasicAuth,
    HeadersMixin,
    TimerNoop,
    noop,
    reify,
    sentinel,
    set_exception,
    set_result,
)
from .http import (
    SERVER_SOFTWARE,
    HttpVersion,
    HttpVersion10,
    HttpVersion11,
    StreamWriter,
)
from .streams import StreamReader
from .typedefs import (
    DEFAULT_JSON_DECODER,
    JSONDecoder,
    LooseCookies,
    LooseHeaders,
    Query,
    RawHeaders,
)

if TYPE_CHECKING:
    import ssl
    from ssl import SSLContext
else:
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


_CONNECTION_CLOSED_EXCEPTION = ClientConnectionError("Connection closed")
_CONTAINS_CONTROL_CHAR_RE = re.compile(r"[^-!#$%&'*+.^_`|~0-9a-zA-Z]")
json_re = re.compile(r"^application/(?:[\w.+-]+?\+)?json")


def _gen_default_accept_encoding() -> str:
    encodings = [
        "gzip",
        "deflate",
    ]
    if HAS_BROTLI:
        encodings.append("br")
    if HAS_ZSTD:
        encodings.append("zstd")
    return ", ".join(encodings)


@attr.s(auto_attribs=True, frozen=True, slots=True)
class ContentDisposition:
    type: Optional[str]
    parameters: "MappingProxyType[str, str]"
    filename: Optional[str]


class _RequestInfo(NamedTuple):
    url: URL
    method: str
    headers: "CIMultiDictProxy[str]"
    real_url: URL


class RequestInfo(_RequestInfo):

    def __new__(
        cls,
        url: URL,
        method: str,
        headers: "CIMultiDictProxy[str]",
        real_url: Union[URL, _SENTINEL] = sentinel,
    ) -> "RequestInfo":
        """Create a new RequestInfo instance.

        For backwards compatibility, the real_url parameter is optional.
        """
        return tuple.__new__(
            cls, (url, method, headers, url if real_url is sentinel else real_url)
        )


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
            raise ValueError("md5 and sha1 are insecure and not supported. Use sha256.")
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
            "fingerprint is deprecated, use ssl=Fingerprint(fingerprint) instead",
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


_SSL_SCHEMES = frozenset(("https", "wss"))


# ConnectionKey is a NamedTuple because it is used as a key in a dict
# and a set in the connector. Since a NamedTuple is a tuple it uses
# the fast native tuple __hash__ and __eq__ implementation in CPython.
class ConnectionKey(NamedTuple):
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


def _warn_if_unclosed_payload(payload: payload.Payload, stacklevel: int = 2) -> None:
    """Warn if the payload is not closed.

    Callers must check that the body is a Payload before calling this method.

    Args:
        payload: The payload to check
        stacklevel: Stack level for the warning (default 2 for direct callers)
    """
    if not payload.autoclose and not payload.consumed:
        warnings.warn(
            "The previous request body contains unclosed resources. "
            "Use await request.update_body() instead of setting request.body "
            "directly to properly close resources and avoid leaks.",
            ResourceWarning,
            stacklevel=stacklevel,
        )


class ClientResponse(HeadersMixin):

    # Some of these attributes are None when created,
    # but will be set by the start() method.
    # As the end user will likely never see the None values, we cheat the types below.
    # from the Status-Line of the response
    version: Optional[HttpVersion] = None  # HTTP-Version
    status: int = None  # type: ignore[assignment] # Status-Code
    reason: Optional[str] = None  # Reason-Phrase

    content: StreamReader = None  # type: ignore[assignment] # Payload stream
    _body: Optional[bytes] = None
    _headers: CIMultiDictProxy[str] = None  # type: ignore[assignment]
    _history: Tuple["ClientResponse", ...] = ()
    _raw_headers: RawHeaders = None  # type: ignore[assignment]

    _connection: Optional["Connection"] = None  # current connection
    _cookies: Optional[SimpleCookie] = None
    _raw_cookie_headers: Optional[Tuple[str, ...]] = None
    _continue: Optional["asyncio.Future[bool]"] = None
    _source_traceback: Optional[traceback.StackSummary] = None
    _session: Optional["ClientSession"] = None
    # set up by ClientRequest after ClientResponse object creation
    # post-init stage allows to not change ctor signature
    _closed = True  # to allow __del__ for non-initialized properly response
    _released = False
    _in_context = False

    _resolve_charset: Callable[["ClientResponse", bytes], str] = lambda *_: "utf-8"

    __writer: Optional["asyncio.Task[None]"] = None

    def __init__(
        self,
        method: str,
        url: URL,
        *,
        writer: "Optional[asyncio.Task[None]]",
        continue100: Optional["asyncio.Future[bool]"],
        timer: BaseTimerContext,
        request_info: RequestInfo,
        traces: List["Trace"],
        loop: asyncio.AbstractEventLoop,
        session: "ClientSession",
    ) -> None:
        # URL forbids subclasses, so a simple type check is enough.
        assert type(url) is URL

        self.method = method

        self._real_url = url
        self._url = url.with_fragment(None) if url.raw_fragment else url
        if writer is not None:
            self._writer = writer
        if continue100 is not None:
            self._continue = continue100
        self._request_info = request_info
        self._timer = timer if timer is not None else TimerNoop()
        self._cache: Dict[str, Any] = {}
        self._traces = traces
        self._loop = loop
        # Save reference to _resolve_charset, so that get_encoding() will still
        # work after the response has finished reading the body.
        # TODO: Fix session=None in tests (see ClientRequest.__init__).
        if session is not None:
            # store a reference to session #1985
            self._session = session
            self._resolve_charset = session._resolve_charset
        if loop.get_debug():
            self._source_traceback = traceback.extract_stack(sys._getframe(1))

    def __reset_writer(self, _: object = None) -> None:
        self.__writer = None

    @property
    def _writer(self) -> Optional["asyncio.Task[None]"]:
        """The writer task for streaming data.

        _writer is only provided for backwards compatibility
        for subclasses that may need to access it.
        """
        return self.__writer

    @_writer.setter
    def _writer(self, writer: Optional["asyncio.Task[None]"]) -> None:
        """Set the writer task for streaming data."""
        if self.__writer is not None:
            self.__writer.remove_done_callback(self.__reset_writer)
        self.__writer = writer
        if writer is None:
            return
        if writer.done():
            # The writer is already done, so we can clear it immediately.
            self.__writer = None
        else:
            writer.add_done_callback(self.__reset_writer)

    @property
    def cookies(self) -> SimpleCookie:
        if self._cookies is None:
            if self._raw_cookie_headers is not None:
                # Parse cookies for response.cookies (SimpleCookie for backward compatibility)
                cookies = SimpleCookie()
                # Use parse_set_cookie_headers for more lenient parsing that handles
                # malformed cookies better than SimpleCookie.load
                cookies.update(parse_set_cookie_headers(self._raw_cookie_headers))
                self._cookies = cookies
            else:
                self._cookies = SimpleCookie()
        return self._cookies

    @cookies.setter
    def cookies(self, cookies: SimpleCookie) -> None:
        self._cookies = cookies
        # Generate raw cookie headers from the SimpleCookie
        if cookies:
            self._raw_cookie_headers = tuple(
                morsel.OutputString() for morsel in cookies.values()
            )
        else:
            self._raw_cookie_headers = None

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
        if cookie_hdrs := self.headers.getall(hdrs.SET_COOKIE, ()):
            # Store raw cookie headers for CookieJar
            self._raw_cookie_headers = tuple(cookie_hdrs)
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

            # If we're in a context we can rely on __aexit__() to release as the
            # exception propagates.
            if not self._in_context:
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
            if self.__writer is None:
                self._connection.release()
                self._connection = None
            else:
                self.__writer.add_done_callback(lambda f: self._release_connection())

    async def _wait_released(self) -> None:
        if self.__writer is not None:
            try:
                await self.__writer
            except asyncio.CancelledError:
                if (
                    sys.version_info >= (3, 11)
                    and (task := asyncio.current_task())
                    and task.cancelling()
                ):
                    raise
        self._release_connection()

    def _cleanup_writer(self) -> None:
        if self.__writer is not None:
            self.__writer.cancel()
        self._session = None

    def _notify_content(self) -> None:
        content = self.content
        if content and content.exception() is None:
            set_exception(content, _CONNECTION_CLOSED_EXCEPTION)
        self._released = True

    async def wait_for_close(self) -> None:
        if self.__writer is not None:
            try:
                await self.__writer
            except asyncio.CancelledError:
                if (
                    sys.version_info >= (3, 11)
                    and (task := asyncio.current_task())
                    and task.cancelling()
                ):
                    raise
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
        return self._body

    def get_encoding(self) -> str:
        ctype = self.headers.get(hdrs.CONTENT_TYPE, "").lower()
        mimetype = helpers.parse_mimetype(ctype)

        encoding = mimetype.parameters.get("charset")
        if encoding:
            with contextlib.suppress(LookupError, ValueError):
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

        return self._body.decode(encoding, errors=errors)  # type: ignore[union-attr]

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
                    status=self.status,
                    message=(
                        "Attempt to decode JSON with unexpected mimetype: %s" % ctype
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
        self._in_context = True
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self._in_context = False
        # similar to _RequestContextManager, we do not need to check
        # for exceptions, response object can close connection
        # if state is broken
        self.release()
        await self.wait_for_close()


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

    # Type of body depends on PAYLOAD_REGISTRY, which is dynamic.
    _body: Union[None, payload.Payload] = None
    auth = None
    response = None

    __writer: Optional["asyncio.Task[None]"] = None  # async task for streaming data

    # These class defaults help create_autospec() work correctly.
    # If autospec is improved in future, maybe these can be removed.
    url = URL()
    method = "GET"

    _continue = None  # waiter future for '100 Continue' response

    _skip_auto_headers: Optional["CIMultiDict[None]"] = None

    # N.B.
    # Adding __del__ method with self._writer closing doesn't make sense
    # because _writer is instance method, thus it keeps a reference to self.
    # Until writer has finished finalizer will not be called.

    def __init__(
        self,
        method: str,
        url: URL,
        *,
        params: Query = None,
        headers: Optional[LooseHeaders] = None,
        skip_auto_headers: Optional[Iterable[str]] = None,
        data: Any = None,
        cookies: Optional[LooseCookies] = None,
        auth: Optional[BasicAuth] = None,
        version: http.HttpVersion = http.HttpVersion11,
        compress: Union[str, bool, None] = None,
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
        if match := _CONTAINS_CONTROL_CHAR_RE.search(method):
            raise ValueError(
                f"Method cannot contain non-token characters {method!r} "
                f"(found at least {match.group()!r})"
            )
        # URL forbids subclasses, so a simple type check is enough.
        assert type(url) is URL, url
        if proxy is not None:
            assert type(proxy) is URL, proxy
        # FIXME: session is None in tests only, need to fix tests
        # assert session is not None
        if TYPE_CHECKING:
            assert session is not None
        self._session = session
        if params:
            url = url.extend_query(params)
        self.original_url = url
        self.url = url.with_fragment(None) if url.raw_fragment else url
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
        self._traces = [] if traces is None else traces

    def __reset_writer(self, _: object = None) -> None:
        self.__writer = None

    def _get_content_length(self) -> Optional[int]:
        """Extract and validate Content-Length header value.

        Returns parsed Content-Length value or None if not set.
        Raises ValueError if header exists but cannot be parsed as an integer.
        """
        if hdrs.CONTENT_LENGTH not in self.headers:
            return None

        content_length_hdr = self.headers[hdrs.CONTENT_LENGTH]
        try:
            return int(content_length_hdr)
        except ValueError:
            raise ValueError(
                f"Invalid Content-Length header: {content_length_hdr}"
            ) from None

    @property
    def skip_auto_headers(self) -> CIMultiDict[None]:
        return self._skip_auto_headers or CIMultiDict()

    @property
    def _writer(self) -> Optional["asyncio.Task[None]"]:
        return self.__writer

    @_writer.setter
    def _writer(self, writer: "asyncio.Task[None]") -> None:
        if self.__writer is not None:
            self.__writer.remove_done_callback(self.__reset_writer)
        self.__writer = writer
        writer.add_done_callback(self.__reset_writer)

    def is_ssl(self) -> bool:
        return self.url.scheme in _SSL_SCHEMES

    @property
    def ssl(self) -> Union["SSLContext", bool, Fingerprint]:
        return self._ssl

    @property
    def connection_key(self) -> ConnectionKey:
        if proxy_headers := self.proxy_headers:
            h: Optional[int] = hash(tuple(proxy_headers.items()))
        else:
            h = None
        url = self.url
        return tuple.__new__(
            ConnectionKey,
            (
                url.raw_host or "",
                url.port,
                url.scheme in _SSL_SCHEMES,
                self._ssl,
                self.proxy,
                self.proxy_auth,
                h,
            ),
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
    def body(self) -> Union[payload.Payload, Literal[b""]]:
        """Request body."""
        # empty body is represented as bytes for backwards compatibility
        return self._body or b""

    @body.setter
    def body(self, value: Any) -> None:
        """Set request body with warning for non-autoclose payloads.

        WARNING: This setter must be called from within an event loop and is not
        thread-safe. Setting body outside of an event loop may raise RuntimeError
        when closing file-based payloads.

        DEPRECATED: Direct assignment to body is deprecated and will be removed
        in a future version. Use await update_body() instead for proper resource
        management.
        """
        # Close existing payload if present
        if self._body is not None:
            # Warn if the payload needs manual closing
            # stacklevel=3: user code -> body setter -> _warn_if_unclosed_payload
            _warn_if_unclosed_payload(self._body, stacklevel=3)
            # NOTE: In the future, when we remove sync close support,
            # this setter will need to be removed and only the async
            # update_body() method will be available. For now, we call
            # _close() for backwards compatibility.
            self._body._close()
        self._update_body(value)

    @property
    def request_info(self) -> RequestInfo:
        headers: CIMultiDictProxy[str] = CIMultiDictProxy(self.headers)
        # These are created on every request, so we use a NamedTuple
        # for performance reasons. We don't use the RequestInfo.__new__
        # method because it has a different signature which is provided
        # for backwards compatibility only.
        return tuple.__new__(
            RequestInfo, (self.url, self.method, headers, self.original_url)
        )

    @property
    def session(self) -> "ClientSession":
        """Return the ClientSession instance.

        This property provides access to the ClientSession that initiated
        this request, allowing middleware to make additional requests
        using the same session.
        """
        return self._session

    def update_host(self, url: URL) -> None:
        """Update destination host, port and connection type (ssl)."""
        # get host/port
        if not url.raw_host:
            raise InvalidURL(url)

        # basic auth info
        if url.raw_user or url.raw_password:
            self.auth = helpers.BasicAuth(url.user or "", url.password or "")

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

        # Build the host header
        host = self.url.host_port_subcomponent

        # host_port_subcomponent is None when the URL is a relative URL.
        # but we know we do not have a relative URL here.
        assert host is not None
        self.headers[hdrs.HOST] = host

        if not headers:
            return

        if isinstance(headers, (dict, MultiDictProxy, MultiDict)):
            headers = headers.items()

        for key, value in headers:  # type: ignore[misc]
            # A special case for Host header
            if key in hdrs.HOST_ALL:
                self.headers[key] = value
            else:
                self.headers.add(key, value)

    def update_auto_headers(self, skip_auto_headers: Optional[Iterable[str]]) -> None:
        if skip_auto_headers is not None:
            self._skip_auto_headers = CIMultiDict(
                (hdr, None) for hdr in sorted(skip_auto_headers)
            )
            used_headers = self.headers.copy()
            used_headers.extend(self._skip_auto_headers)  # type: ignore[arg-type]
        else:
            # Fast path when there are no headers to skip
            # which is the most common case.
            used_headers = self.headers

        for hdr, val in self.DEFAULT_HEADERS.items():
            if hdr not in used_headers:
                self.headers[hdr] = val

        if hdrs.USER_AGENT not in used_headers:
            self.headers[hdrs.USER_AGENT] = SERVER_SOFTWARE

    def update_cookies(self, cookies: Optional[LooseCookies]) -> None:
        """Update request cookies header."""
        if not cookies:
            return

        c = SimpleCookie()
        if hdrs.COOKIE in self.headers:
            # parse_cookie_header for RFC 6265 compliant Cookie header parsing
            c.update(parse_cookie_header(self.headers.get(hdrs.COOKIE, "")))
            del self.headers[hdrs.COOKIE]

        if isinstance(cookies, Mapping):
            iter_cookies = cookies.items()
        else:
            iter_cookies = cookies  # type: ignore[assignment]
        for name, value in iter_cookies:
            if isinstance(value, Morsel):
                # Use helper to preserve coded_value exactly as sent by server
                c[name] = preserve_morsel_with_coded_value(value)
            else:
                c[name] = value  # type: ignore[assignment]

        self.headers[hdrs.COOKIE] = c.output(header="", sep=";").strip()

    def update_content_encoding(self, data: Any) -> None:
        """Set request content encoding."""
        if not data:
            # Don't compress an empty body.
            self.compress = None
            return

        if self.headers.get(hdrs.CONTENT_ENCODING):
            if self.compress:
                raise ValueError(
                    "compress can not be set if Content-Encoding header is set"
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
                    "chunked can not be set if Content-Length header is set"
                )

            self.headers[hdrs.TRANSFER_ENCODING] = "chunked"

    def update_auth(self, auth: Optional[BasicAuth], trust_env: bool = False) -> None:
        """Set basic auth."""
        if auth is None:
            auth = self.auth
        if auth is None:
            return

        if not isinstance(auth, helpers.BasicAuth):
            raise TypeError("BasicAuth() tuple is required instead")

        self.headers[hdrs.AUTHORIZATION] = auth.encode()

    def update_body_from_data(self, body: Any, _stacklevel: int = 3) -> None:
        """Update request body from data."""
        if self._body is not None:
            _warn_if_unclosed_payload(self._body, stacklevel=_stacklevel)

        if body is None:
            self._body = None
            # Set Content-Length to 0 when body is None for methods that expect a body
            if (
                self.method not in self.GET_METHODS
                and not self.chunked
                and hdrs.CONTENT_LENGTH not in self.headers
            ):
                self.headers[hdrs.CONTENT_LENGTH] = "0"
            return

        # FormData
        maybe_payload = body() if isinstance(body, FormData) else body

        try:
            body_payload = payload.PAYLOAD_REGISTRY.get(maybe_payload, disposition=None)
        except payload.LookupError:
            body_payload = FormData(maybe_payload)()  # type: ignore[arg-type]

        self._body = body_payload
        # enable chunked encoding if needed
        if not self.chunked and hdrs.CONTENT_LENGTH not in self.headers:
            if (size := body_payload.size) is not None:
                self.headers[hdrs.CONTENT_LENGTH] = str(size)
            else:
                self.chunked = True

        # copy payload headers
        assert body_payload.headers
        headers = self.headers
        skip_headers = self._skip_auto_headers
        for key, value in body_payload.headers.items():
            if key in headers or (skip_headers is not None and key in skip_headers):
                continue
            headers[key] = value

    def _update_body(self, body: Any) -> None:
        """Update request body after its already been set."""
        # Remove existing Content-Length header since body is changing
        if hdrs.CONTENT_LENGTH in self.headers:
            del self.headers[hdrs.CONTENT_LENGTH]

        # Remove existing Transfer-Encoding header to avoid conflicts
        if self.chunked and hdrs.TRANSFER_ENCODING in self.headers:
            del self.headers[hdrs.TRANSFER_ENCODING]

        # Now update the body using the existing method
        # Called from _update_body, add 1 to stacklevel from caller
        self.update_body_from_data(body, _stacklevel=4)

        # Update transfer encoding headers if needed (same logic as __init__)
        if body is not None or self.method not in self.GET_METHODS:
            self.update_transfer_encoding()

    async def update_body(self, body: Any) -> None:
        """
        Update request body and close previous payload if needed.

        This method safely updates the request body by first closing any existing
        payload to prevent resource leaks, then setting the new body.

        IMPORTANT: Always use this method instead of setting request.body directly.
        Direct assignment to request.body will leak resources if the previous body
        contains file handles, streams, or other resources that need cleanup.

        Args:
            body: The new body content. Can be:
                - bytes/bytearray: Raw binary data
                - str: Text data (will be encoded using charset from Content-Type)
                - FormData: Form data that will be encoded as multipart/form-data
                - Payload: A pre-configured payload object
                - AsyncIterable: An async iterable of bytes chunks
                - File-like object: Will be read and sent as binary data
                - None: Clears the body

        Usage:
            # CORRECT: Use update_body
            await request.update_body(b"new request data")

            # WRONG: Don't set body directly
            # request.body = b"new request data"  # This will leak resources!

            # Update with form data
            form_data = FormData()
            form_data.add_field('field', 'value')
            await request.update_body(form_data)

            # Clear body
            await request.update_body(None)

        Note:
            This method is async because it may need to close file handles or
            other resources associated with the previous payload. Always await
            this method to ensure proper cleanup.

        Warning:
            Setting request.body directly is highly discouraged and can lead to:
            - Resource leaks (unclosed file handles, streams)
            - Memory leaks (unreleased buffers)
            - Unexpected behavior with streaming payloads

            It is not recommended to change the payload type in middleware. If the
            body was already set (e.g., as bytes), it's best to keep the same type
            rather than converting it (e.g., to str) as this may result in unexpected
            behavior.

        See Also:
            - update_body_from_data: Synchronous body update without cleanup
            - body property: Direct body access (STRONGLY DISCOURAGED)

        """
        # Close existing payload if it exists and needs closing
        if self._body is not None:
            await self._body.close()
        self._update_body(body)

    def update_expect_continue(self, expect: bool = False) -> None:
        if expect:
            self.headers[hdrs.EXPECT] = "100-continue"
        elif (
            hdrs.EXPECT in self.headers
            and self.headers[hdrs.EXPECT].lower() == "100-continue"
        ):
            expect = True

        if expect:
            self._continue = self.loop.create_future()

    def update_proxy(
        self,
        proxy: Optional[URL],
        proxy_auth: Optional[BasicAuth],
        proxy_headers: Optional[LooseHeaders],
    ) -> None:
        self.proxy = proxy
        if proxy is None:
            self.proxy_auth = None
            self.proxy_headers = None
            return

        if proxy_auth and not isinstance(proxy_auth, helpers.BasicAuth):
            raise ValueError("proxy_auth must be None or BasicAuth() tuple")
        self.proxy_auth = proxy_auth

        if proxy_headers is not None and not isinstance(
            proxy_headers, (MultiDict, MultiDictProxy)
        ):
            proxy_headers = CIMultiDict(proxy_headers)
        self.proxy_headers = proxy_headers

    async def write_bytes(
        self,
        writer: AbstractStreamWriter,
        conn: "Connection",
        content_length: Optional[int] = None,
    ) -> None:
        """
        Write the request body to the connection stream.

        This method handles writing different types of request bodies:
        1. Payload objects (using their specialized write_with_length method)
        2. Bytes/bytearray objects
        3. Iterable body content

        Args:
            writer: The stream writer to write the body to
            conn: The connection being used for this request
            content_length: Optional maximum number of bytes to write from the body
                            (None means write the entire body)

        The method properly handles:
        - Waiting for 100-Continue responses if required
        - Content length constraints for chunked encoding
        - Error handling for network issues, cancellation, and other exceptions
        - Signaling EOF and timeout management

        Raises:
            ClientOSError: When there's an OS-level error writing the body
            ClientConnectionError: When there's a general connection error
            asyncio.CancelledError: When the operation is cancelled

        """
        # 100 response
        if self._continue is not None:
            # Force headers to be sent before waiting for 100-continue
            writer.send_headers()
            await writer.drain()
            await self._continue

        protocol = conn.protocol
        assert protocol is not None
        try:
            # This should be a rare case but the
            # self._body can be set to None while
            # the task is being started or we wait above
            # for the 100-continue response.
            # The more likely case is we have an empty
            # payload, but 100-continue is still expected.
            if self._body is not None:
                await self._body.write_with_length(writer, content_length)
        except OSError as underlying_exc:
            reraised_exc = underlying_exc

            # Distinguish between timeout and other OS errors for better error reporting
            exc_is_not_timeout = underlying_exc.errno is not None or not isinstance(
                underlying_exc, asyncio.TimeoutError
            )
            if exc_is_not_timeout:
                reraised_exc = ClientOSError(
                    underlying_exc.errno,
                    f"Can not write request body for {self.url !s}",
                )

            set_exception(protocol, reraised_exc, underlying_exc)
        except asyncio.CancelledError:
            # Body hasn't been fully sent, so connection can't be reused
            conn.close()
            raise
        except Exception as underlying_exc:
            set_exception(
                protocol,
                ClientConnectionError(
                    "Failed to send bytes into the underlying connection "
                    f"{conn !s}: {underlying_exc!r}",
                ),
                underlying_exc,
            )
        else:
            # Successfully wrote the body, signal EOF and start response timeout
            await writer.write_eof()
            protocol.start_timeout()

    async def send(self, conn: "Connection") -> "ClientResponse":
        # Specify request target:
        # - CONNECT request must send authority form URI
        # - not CONNECT proxy must send absolute form URI
        # - most common is origin form URI
        if self.method == hdrs.METH_CONNECT:
            connect_host = self.url.host_subcomponent
            assert connect_host is not None
            path = f"{connect_host}:{self.url.port}"
        elif self.proxy and not self.is_ssl():
            path = str(self.url)
        else:
            path = self.url.raw_path_qs

        protocol = conn.protocol
        assert protocol is not None
        writer = StreamWriter(
            protocol,
            self.loop,
            on_chunk_sent=(
                functools.partial(self._on_chunk_request_sent, self.method, self.url)
                if self._traces
                else None
            ),
            on_headers_sent=(
                functools.partial(self._on_headers_request_sent, self.method, self.url)
                if self._traces
                else None
            ),
        )

        if self.compress:
            writer.enable_compression(self.compress)  # type: ignore[arg-type]

        if self.chunked is not None:
            writer.enable_chunking()

        # set default content-type
        if (
            self.method in self.POST_METHODS
            and (
                self._skip_auto_headers is None
                or hdrs.CONTENT_TYPE not in self._skip_auto_headers
            )
            and hdrs.CONTENT_TYPE not in self.headers
        ):
            self.headers[hdrs.CONTENT_TYPE] = "application/octet-stream"

        v = self.version
        if hdrs.CONNECTION not in self.headers:
            if conn._connector.force_close:
                if v == HttpVersion11:
                    self.headers[hdrs.CONNECTION] = "close"
            elif v == HttpVersion10:
                self.headers[hdrs.CONNECTION] = "keep-alive"

        # status + headers
        status_line = f"{self.method} {path} HTTP/{v.major}.{v.minor}"

        # Buffer headers for potential coalescing with body
        await writer.write_headers(status_line, self.headers)

        task: Optional["asyncio.Task[None]"]
        if self._body or self._continue is not None or protocol.writing_paused:
            coro = self.write_bytes(writer, conn, self._get_content_length())
            if sys.version_info >= (3, 12):
                # Optimization for Python 3.12, try to write
                # bytes immediately to avoid having to schedule
                # the task on the event loop.
                task = asyncio.Task(coro, loop=self.loop, eager_start=True)
            else:
                task = self.loop.create_task(coro)
            if task.done():
                task = None
            else:
                self._writer = task
        else:
            # We have nothing to write because
            # - there is no body
            # - the protocol does not have writing paused
            # - we are not waiting for a 100-continue response
            protocol.start_timeout()
            writer.set_eof()
            task = None
        response_class = self.response_class
        assert response_class is not None
        self.response = response_class(
            self.method,
            self.original_url,
            writer=task,
            continue100=self._continue,
            timer=self._timer,
            request_info=self.request_info,
            traces=self._traces,
            loop=self.loop,
            session=self._session,
        )
        return self.response

    async def close(self) -> None:
        if self.__writer is not None:
            try:
                await self.__writer
            except asyncio.CancelledError:
                if (
                    sys.version_info >= (3, 11)
                    and (task := asyncio.current_task())
                    and task.cancelling()
                ):
                    raise

    def terminate(self) -> None:
        if self.__writer is not None:
            if not self.loop.is_closed():
                self.__writer.cancel()
            self.__writer.remove_done_callback(self.__reset_writer)
            self.__writer = None

    async def _on_chunk_request_sent(self, method: str, url: URL, chunk: bytes) -> None:
        for trace in self._traces:
            await trace.send_request_chunk_sent(method, url, chunk)

    async def _on_headers_request_sent(
        self, method: str, url: URL, headers: "CIMultiDict[str]"
    ) -> None:
        for trace in self._traces:
            await trace.send_request_headers(method, url, headers)
