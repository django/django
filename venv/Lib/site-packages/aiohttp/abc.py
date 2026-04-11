import asyncio
import logging
import socket
from abc import ABC, abstractmethod
from collections.abc import Sized
from http.cookies import BaseCookie, Morsel
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    Generator,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    TypedDict,
    Union,
)

from multidict import CIMultiDict
from yarl import URL

from ._cookie_helpers import parse_set_cookie_headers
from .typedefs import LooseCookies

if TYPE_CHECKING:
    from .web_app import Application
    from .web_exceptions import HTTPException
    from .web_request import BaseRequest, Request
    from .web_response import StreamResponse
else:
    BaseRequest = Request = Application = StreamResponse = None
    HTTPException = None


class AbstractRouter(ABC):
    def __init__(self) -> None:
        self._frozen = False

    def post_init(self, app: Application) -> None:
        """Post init stage.

        Not an abstract method for sake of backward compatibility,
        but if the router wants to be aware of the application
        it can override this.
        """

    @property
    def frozen(self) -> bool:
        return self._frozen

    def freeze(self) -> None:
        """Freeze router."""
        self._frozen = True

    @abstractmethod
    async def resolve(self, request: Request) -> "AbstractMatchInfo":
        """Return MATCH_INFO for given request"""


class AbstractMatchInfo(ABC):

    __slots__ = ()

    @property  # pragma: no branch
    @abstractmethod
    def handler(self) -> Callable[[Request], Awaitable[StreamResponse]]:
        """Execute matched request handler"""

    @property
    @abstractmethod
    def expect_handler(
        self,
    ) -> Callable[[Request], Awaitable[Optional[StreamResponse]]]:
        """Expect handler for 100-continue processing"""

    @property  # pragma: no branch
    @abstractmethod
    def http_exception(self) -> Optional[HTTPException]:
        """HTTPException instance raised on router's resolving, or None"""

    @abstractmethod  # pragma: no branch
    def get_info(self) -> Dict[str, Any]:
        """Return a dict with additional info useful for introspection"""

    @property  # pragma: no branch
    @abstractmethod
    def apps(self) -> Tuple[Application, ...]:
        """Stack of nested applications.

        Top level application is left-most element.

        """

    @abstractmethod
    def add_app(self, app: Application) -> None:
        """Add application to the nested apps stack."""

    @abstractmethod
    def freeze(self) -> None:
        """Freeze the match info.

        The method is called after route resolution.

        After the call .add_app() is forbidden.

        """


class AbstractView(ABC):
    """Abstract class based view."""

    def __init__(self, request: Request) -> None:
        self._request = request

    @property
    def request(self) -> Request:
        """Request instance."""
        return self._request

    @abstractmethod
    def __await__(self) -> Generator[None, None, StreamResponse]:
        """Execute the view handler."""


class ResolveResult(TypedDict):
    """Resolve result.

    This is the result returned from an AbstractResolver's
    resolve method.

    :param hostname: The hostname that was provided.
    :param host: The IP address that was resolved.
    :param port: The port that was resolved.
    :param family: The address family that was resolved.
    :param proto: The protocol that was resolved.
    :param flags: The flags that were resolved.
    """

    hostname: str
    host: str
    port: int
    family: int
    proto: int
    flags: int


class AbstractResolver(ABC):
    """Abstract DNS resolver."""

    @abstractmethod
    async def resolve(
        self, host: str, port: int = 0, family: socket.AddressFamily = socket.AF_INET
    ) -> List[ResolveResult]:
        """Return IP address for given hostname"""

    @abstractmethod
    async def close(self) -> None:
        """Release resolver"""


if TYPE_CHECKING:
    IterableBase = Iterable[Morsel[str]]
else:
    IterableBase = Iterable


ClearCookiePredicate = Callable[["Morsel[str]"], bool]


class AbstractCookieJar(Sized, IterableBase):
    """Abstract Cookie Jar."""

    def __init__(self, *, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self._loop = loop or asyncio.get_running_loop()

    @property
    @abstractmethod
    def quote_cookie(self) -> bool:
        """Return True if cookies should be quoted."""

    @abstractmethod
    def clear(self, predicate: Optional[ClearCookiePredicate] = None) -> None:
        """Clear all cookies if no predicate is passed."""

    @abstractmethod
    def clear_domain(self, domain: str) -> None:
        """Clear all cookies for domain and all subdomains."""

    @abstractmethod
    def update_cookies(self, cookies: LooseCookies, response_url: URL = URL()) -> None:
        """Update cookies."""

    def update_cookies_from_headers(
        self, headers: Sequence[str], response_url: URL
    ) -> None:
        """Update cookies from raw Set-Cookie headers."""
        if headers and (cookies_to_update := parse_set_cookie_headers(headers)):
            self.update_cookies(cookies_to_update, response_url)

    @abstractmethod
    def filter_cookies(self, request_url: URL) -> "BaseCookie[str]":
        """Return the jar's cookies filtered by their attributes."""


class AbstractStreamWriter(ABC):
    """Abstract stream writer."""

    buffer_size: int = 0
    output_size: int = 0
    length: Optional[int] = 0

    @abstractmethod
    async def write(self, chunk: Union[bytes, bytearray, memoryview]) -> None:
        """Write chunk into stream."""

    @abstractmethod
    async def write_eof(self, chunk: bytes = b"") -> None:
        """Write last chunk."""

    @abstractmethod
    async def drain(self) -> None:
        """Flush the write buffer."""

    @abstractmethod
    def enable_compression(
        self, encoding: str = "deflate", strategy: Optional[int] = None
    ) -> None:
        """Enable HTTP body compression"""

    @abstractmethod
    def enable_chunking(self) -> None:
        """Enable HTTP chunked mode"""

    @abstractmethod
    async def write_headers(
        self, status_line: str, headers: "CIMultiDict[str]"
    ) -> None:
        """Write HTTP headers"""

    def send_headers(self) -> None:
        """Force sending buffered headers if not already sent.

        Required only if write_headers() buffers headers instead of sending immediately.
        For backwards compatibility, this method does nothing by default.
        """


class AbstractAccessLogger(ABC):
    """Abstract writer to access log."""

    __slots__ = ("logger", "log_format")

    def __init__(self, logger: logging.Logger, log_format: str) -> None:
        self.logger = logger
        self.log_format = log_format

    @abstractmethod
    def log(self, request: BaseRequest, response: StreamResponse, time: float) -> None:
        """Emit log to logger."""

    @property
    def enabled(self) -> bool:
        """Check if logger is enabled."""
        return True
