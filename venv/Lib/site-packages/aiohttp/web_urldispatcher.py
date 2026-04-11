import abc
import asyncio
import base64
import functools
import hashlib
import html
import inspect
import keyword
import os
import platform
import re
import sys
import warnings
from functools import wraps
from pathlib import Path
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Container,
    Dict,
    Final,
    Generator,
    Iterable,
    Iterator,
    List,
    Mapping,
    NoReturn,
    Optional,
    Pattern,
    Set,
    Sized,
    Tuple,
    Type,
    TypedDict,
    Union,
    cast,
)

from yarl import URL, __version__ as yarl_version

from . import hdrs
from .abc import AbstractMatchInfo, AbstractRouter, AbstractView
from .helpers import DEBUG
from .http import HttpVersion11
from .typedefs import Handler, PathLike
from .web_exceptions import (
    HTTPException,
    HTTPExpectationFailed,
    HTTPForbidden,
    HTTPMethodNotAllowed,
    HTTPNotFound,
)
from .web_fileresponse import FileResponse
from .web_request import Request
from .web_response import Response, StreamResponse
from .web_routedef import AbstractRouteDef

__all__ = (
    "UrlDispatcher",
    "UrlMappingMatchInfo",
    "AbstractResource",
    "Resource",
    "PlainResource",
    "DynamicResource",
    "AbstractRoute",
    "ResourceRoute",
    "StaticResource",
    "View",
)


if TYPE_CHECKING:
    from .web_app import Application

    BaseDict = Dict[str, str]
else:
    BaseDict = dict

CIRCULAR_SYMLINK_ERROR = (
    (OSError,)
    if sys.version_info < (3, 10) and sys.platform.startswith("win32")
    else (RuntimeError,) if sys.version_info < (3, 13) else ()
)

YARL_VERSION: Final[Tuple[int, ...]] = tuple(map(int, yarl_version.split(".")[:2]))

HTTP_METHOD_RE: Final[Pattern[str]] = re.compile(
    r"^[0-9A-Za-z!#\$%&'\*\+\-\.\^_`\|~]+$"
)
ROUTE_RE: Final[Pattern[str]] = re.compile(
    r"(\{[_a-zA-Z][^{}]*(?:\{[^{}]*\}[^{}]*)*\})"
)
PATH_SEP: Final[str] = re.escape("/")

IS_WINDOWS: Final[bool] = platform.system() == "Windows"

_ExpectHandler = Callable[[Request], Awaitable[Optional[StreamResponse]]]
_Resolve = Tuple[Optional["UrlMappingMatchInfo"], Set[str]]

html_escape = functools.partial(html.escape, quote=True)


class _InfoDict(TypedDict, total=False):
    path: str

    formatter: str
    pattern: Pattern[str]

    directory: Path
    prefix: str
    routes: Mapping[str, "AbstractRoute"]

    app: "Application"

    domain: str

    rule: "AbstractRuleMatching"

    http_exception: HTTPException


class AbstractResource(Sized, Iterable["AbstractRoute"]):
    def __init__(self, *, name: Optional[str] = None) -> None:
        self._name = name

    @property
    def name(self) -> Optional[str]:
        return self._name

    @property
    @abc.abstractmethod
    def canonical(self) -> str:
        """Exposes the resource's canonical path.

        For example '/foo/bar/{name}'

        """

    @abc.abstractmethod  # pragma: no branch
    def url_for(self, **kwargs: str) -> URL:
        """Construct url for resource with additional params."""

    @abc.abstractmethod  # pragma: no branch
    async def resolve(self, request: Request) -> _Resolve:
        """Resolve resource.

        Return (UrlMappingMatchInfo, allowed_methods) pair.
        """

    @abc.abstractmethod
    def add_prefix(self, prefix: str) -> None:
        """Add a prefix to processed URLs.

        Required for subapplications support.
        """

    @abc.abstractmethod
    def get_info(self) -> _InfoDict:
        """Return a dict with additional info useful for introspection"""

    def freeze(self) -> None:
        pass

    @abc.abstractmethod
    def raw_match(self, path: str) -> bool:
        """Perform a raw match against path"""


class AbstractRoute(abc.ABC):
    def __init__(
        self,
        method: str,
        handler: Union[Handler, Type[AbstractView]],
        *,
        expect_handler: Optional[_ExpectHandler] = None,
        resource: Optional[AbstractResource] = None,
    ) -> None:

        if expect_handler is None:
            expect_handler = _default_expect_handler

        assert inspect.iscoroutinefunction(expect_handler) or (
            sys.version_info < (3, 14) and asyncio.iscoroutinefunction(expect_handler)
        ), f"Coroutine is expected, got {expect_handler!r}"

        method = method.upper()
        if not HTTP_METHOD_RE.match(method):
            raise ValueError(f"{method} is not allowed HTTP method")

        assert callable(handler), handler
        if inspect.iscoroutinefunction(handler) or (
            sys.version_info < (3, 14) and asyncio.iscoroutinefunction(handler)
        ):
            pass
        elif inspect.isgeneratorfunction(handler):
            if TYPE_CHECKING:
                assert False
            warnings.warn(
                "Bare generators are deprecated, use @coroutine wrapper",
                DeprecationWarning,
            )
        elif isinstance(handler, type) and issubclass(handler, AbstractView):
            pass
        else:
            warnings.warn(
                "Bare functions are deprecated, use async ones", DeprecationWarning
            )

            @wraps(handler)
            async def handler_wrapper(request: Request) -> StreamResponse:
                result = old_handler(request)  # type: ignore[call-arg]
                if asyncio.iscoroutine(result):
                    result = await result
                assert isinstance(result, StreamResponse)
                return result

            old_handler = handler
            handler = handler_wrapper

        self._method = method
        self._handler = handler
        self._expect_handler = expect_handler
        self._resource = resource

    @property
    def method(self) -> str:
        return self._method

    @property
    def handler(self) -> Handler:
        return self._handler

    @property
    @abc.abstractmethod
    def name(self) -> Optional[str]:
        """Optional route's name, always equals to resource's name."""

    @property
    def resource(self) -> Optional[AbstractResource]:
        return self._resource

    @abc.abstractmethod
    def get_info(self) -> _InfoDict:
        """Return a dict with additional info useful for introspection"""

    @abc.abstractmethod  # pragma: no branch
    def url_for(self, *args: str, **kwargs: str) -> URL:
        """Construct url for route with additional params."""

    async def handle_expect_header(self, request: Request) -> Optional[StreamResponse]:
        return await self._expect_handler(request)


class UrlMappingMatchInfo(BaseDict, AbstractMatchInfo):

    __slots__ = ("_route", "_apps", "_current_app", "_frozen")

    def __init__(self, match_dict: Dict[str, str], route: AbstractRoute) -> None:
        super().__init__(match_dict)
        self._route = route
        self._apps: List[Application] = []
        self._current_app: Optional[Application] = None
        self._frozen = False

    @property
    def handler(self) -> Handler:
        return self._route.handler

    @property
    def route(self) -> AbstractRoute:
        return self._route

    @property
    def expect_handler(self) -> _ExpectHandler:
        return self._route.handle_expect_header

    @property
    def http_exception(self) -> Optional[HTTPException]:
        return None

    def get_info(self) -> _InfoDict:  # type: ignore[override]
        return self._route.get_info()

    @property
    def apps(self) -> Tuple["Application", ...]:
        return tuple(self._apps)

    def add_app(self, app: "Application") -> None:
        if self._frozen:
            raise RuntimeError("Cannot change apps stack after .freeze() call")
        if self._current_app is None:
            self._current_app = app
        self._apps.insert(0, app)

    @property
    def current_app(self) -> "Application":
        app = self._current_app
        assert app is not None
        return app

    @current_app.setter
    def current_app(self, app: "Application") -> None:
        if DEBUG:  # pragma: no cover
            if app not in self._apps:
                raise RuntimeError(
                    "Expected one of the following apps {!r}, got {!r}".format(
                        self._apps, app
                    )
                )
        self._current_app = app

    def freeze(self) -> None:
        self._frozen = True

    def __repr__(self) -> str:
        return f"<MatchInfo {super().__repr__()}: {self._route}>"


class MatchInfoError(UrlMappingMatchInfo):

    __slots__ = ("_exception",)

    def __init__(self, http_exception: HTTPException) -> None:
        self._exception = http_exception
        super().__init__({}, SystemRoute(self._exception))

    @property
    def http_exception(self) -> HTTPException:
        return self._exception

    def __repr__(self) -> str:
        return "<MatchInfoError {}: {}>".format(
            self._exception.status, self._exception.reason
        )


async def _default_expect_handler(request: Request) -> None:
    """Default handler for Expect header.

    Just send "100 Continue" to client.
    raise HTTPExpectationFailed if value of header is not "100-continue"
    """
    expect = request.headers.get(hdrs.EXPECT, "")
    if request.version == HttpVersion11:
        if expect.lower() == "100-continue":
            await request.writer.write(b"HTTP/1.1 100 Continue\r\n\r\n")
            # Reset output_size as we haven't started the main body yet.
            request.writer.output_size = 0
        else:
            raise HTTPExpectationFailed(text="Unknown Expect: %s" % expect)


class Resource(AbstractResource):
    def __init__(self, *, name: Optional[str] = None) -> None:
        super().__init__(name=name)
        self._routes: Dict[str, ResourceRoute] = {}
        self._any_route: Optional[ResourceRoute] = None
        self._allowed_methods: Set[str] = set()

    def add_route(
        self,
        method: str,
        handler: Union[Type[AbstractView], Handler],
        *,
        expect_handler: Optional[_ExpectHandler] = None,
    ) -> "ResourceRoute":
        if route := self._routes.get(method, self._any_route):
            raise RuntimeError(
                "Added route will never be executed, "
                f"method {route.method} is already "
                "registered"
            )

        route_obj = ResourceRoute(method, handler, self, expect_handler=expect_handler)
        self.register_route(route_obj)
        return route_obj

    def register_route(self, route: "ResourceRoute") -> None:
        assert isinstance(
            route, ResourceRoute
        ), f"Instance of Route class is required, got {route!r}"
        if route.method == hdrs.METH_ANY:
            self._any_route = route
        self._allowed_methods.add(route.method)
        self._routes[route.method] = route

    async def resolve(self, request: Request) -> _Resolve:
        if (match_dict := self._match(request.rel_url.path_safe)) is None:
            return None, set()
        if route := self._routes.get(request.method, self._any_route):
            return UrlMappingMatchInfo(match_dict, route), self._allowed_methods
        return None, self._allowed_methods

    @abc.abstractmethod
    def _match(self, path: str) -> Optional[Dict[str, str]]:
        pass  # pragma: no cover

    def __len__(self) -> int:
        return len(self._routes)

    def __iter__(self) -> Iterator["ResourceRoute"]:
        return iter(self._routes.values())

    # TODO: implement all abstract methods


class PlainResource(Resource):
    def __init__(self, path: str, *, name: Optional[str] = None) -> None:
        super().__init__(name=name)
        assert not path or path.startswith("/")
        self._path = path

    @property
    def canonical(self) -> str:
        return self._path

    def freeze(self) -> None:
        if not self._path:
            self._path = "/"

    def add_prefix(self, prefix: str) -> None:
        assert prefix.startswith("/")
        assert not prefix.endswith("/")
        assert len(prefix) > 1
        self._path = prefix + self._path

    def _match(self, path: str) -> Optional[Dict[str, str]]:
        # string comparison is about 10 times faster than regexp matching
        if self._path == path:
            return {}
        return None

    def raw_match(self, path: str) -> bool:
        return self._path == path

    def get_info(self) -> _InfoDict:
        return {"path": self._path}

    def url_for(self) -> URL:  # type: ignore[override]
        return URL.build(path=self._path, encoded=True)

    def __repr__(self) -> str:
        name = "'" + self.name + "' " if self.name is not None else ""
        return f"<PlainResource {name} {self._path}>"


class DynamicResource(Resource):

    DYN = re.compile(r"\{(?P<var>[_a-zA-Z][_a-zA-Z0-9]*)\}")
    DYN_WITH_RE = re.compile(r"\{(?P<var>[_a-zA-Z][_a-zA-Z0-9]*):(?P<re>.+)\}")
    GOOD = r"[^{}/]+"

    def __init__(self, path: str, *, name: Optional[str] = None) -> None:
        super().__init__(name=name)
        self._orig_path = path
        pattern = ""
        formatter = ""
        for part in ROUTE_RE.split(path):
            match = self.DYN.fullmatch(part)
            if match:
                pattern += "(?P<{}>{})".format(match.group("var"), self.GOOD)
                formatter += "{" + match.group("var") + "}"
                continue

            match = self.DYN_WITH_RE.fullmatch(part)
            if match:
                pattern += "(?P<{var}>{re})".format(**match.groupdict())
                formatter += "{" + match.group("var") + "}"
                continue

            if "{" in part or "}" in part:
                raise ValueError(f"Invalid path '{path}'['{part}']")

            part = _requote_path(part)
            formatter += part
            pattern += re.escape(part)

        try:
            compiled = re.compile(pattern)
        except re.error as exc:
            raise ValueError(f"Bad pattern '{pattern}': {exc}") from None
        assert compiled.pattern.startswith(PATH_SEP)
        assert formatter.startswith("/")
        self._pattern = compiled
        self._formatter = formatter

    @property
    def canonical(self) -> str:
        return self._formatter

    def add_prefix(self, prefix: str) -> None:
        assert prefix.startswith("/")
        assert not prefix.endswith("/")
        assert len(prefix) > 1
        self._pattern = re.compile(re.escape(prefix) + self._pattern.pattern)
        self._formatter = prefix + self._formatter

    def _match(self, path: str) -> Optional[Dict[str, str]]:
        match = self._pattern.fullmatch(path)
        if match is None:
            return None
        return {
            key: _unquote_path_safe(value) for key, value in match.groupdict().items()
        }

    def raw_match(self, path: str) -> bool:
        return self._orig_path == path

    def get_info(self) -> _InfoDict:
        return {"formatter": self._formatter, "pattern": self._pattern}

    def url_for(self, **parts: str) -> URL:
        url = self._formatter.format_map({k: _quote_path(v) for k, v in parts.items()})
        return URL.build(path=url, encoded=True)

    def __repr__(self) -> str:
        name = "'" + self.name + "' " if self.name is not None else ""
        return "<DynamicResource {name} {formatter}>".format(
            name=name, formatter=self._formatter
        )


class PrefixResource(AbstractResource):
    def __init__(self, prefix: str, *, name: Optional[str] = None) -> None:
        assert not prefix or prefix.startswith("/"), prefix
        assert prefix in ("", "/") or not prefix.endswith("/"), prefix
        super().__init__(name=name)
        self._prefix = _requote_path(prefix)
        self._prefix2 = self._prefix + "/"

    @property
    def canonical(self) -> str:
        return self._prefix

    def add_prefix(self, prefix: str) -> None:
        assert prefix.startswith("/")
        assert not prefix.endswith("/")
        assert len(prefix) > 1
        self._prefix = prefix + self._prefix
        self._prefix2 = self._prefix + "/"

    def raw_match(self, prefix: str) -> bool:
        return False

    # TODO: impl missing abstract methods


class StaticResource(PrefixResource):
    VERSION_KEY = "v"

    def __init__(
        self,
        prefix: str,
        directory: PathLike,
        *,
        name: Optional[str] = None,
        expect_handler: Optional[_ExpectHandler] = None,
        chunk_size: int = 256 * 1024,
        show_index: bool = False,
        follow_symlinks: bool = False,
        append_version: bool = False,
    ) -> None:
        super().__init__(prefix, name=name)
        try:
            directory = Path(directory).expanduser().resolve(strict=True)
        except FileNotFoundError as error:
            raise ValueError(f"'{directory}' does not exist") from error
        if not directory.is_dir():
            raise ValueError(f"'{directory}' is not a directory")
        self._directory = directory
        self._show_index = show_index
        self._chunk_size = chunk_size
        self._follow_symlinks = follow_symlinks
        self._expect_handler = expect_handler
        self._append_version = append_version

        self._routes = {
            "GET": ResourceRoute(
                "GET", self._handle, self, expect_handler=expect_handler
            ),
            "HEAD": ResourceRoute(
                "HEAD", self._handle, self, expect_handler=expect_handler
            ),
        }
        self._allowed_methods = set(self._routes)

    def url_for(  # type: ignore[override]
        self,
        *,
        filename: PathLike,
        append_version: Optional[bool] = None,
    ) -> URL:
        if append_version is None:
            append_version = self._append_version
        filename = str(filename).lstrip("/")

        url = URL.build(path=self._prefix, encoded=True)
        # filename is not encoded
        if YARL_VERSION < (1, 6):
            url = url / filename.replace("%", "%25")
        else:
            url = url / filename

        if append_version:
            unresolved_path = self._directory.joinpath(filename)
            try:
                if self._follow_symlinks:
                    normalized_path = Path(os.path.normpath(unresolved_path))
                    normalized_path.relative_to(self._directory)
                    filepath = normalized_path.resolve()
                else:
                    filepath = unresolved_path.resolve()
                    filepath.relative_to(self._directory)
            except (ValueError, FileNotFoundError):
                # ValueError for case when path point to symlink
                # with follow_symlinks is False
                return url  # relatively safe
            if filepath.is_file():
                # TODO cache file content
                # with file watcher for cache invalidation
                with filepath.open("rb") as f:
                    file_bytes = f.read()
                h = self._get_file_hash(file_bytes)
                url = url.with_query({self.VERSION_KEY: h})
                return url
        return url

    @staticmethod
    def _get_file_hash(byte_array: bytes) -> str:
        m = hashlib.sha256()  # todo sha256 can be configurable param
        m.update(byte_array)
        b64 = base64.urlsafe_b64encode(m.digest())
        return b64.decode("ascii")

    def get_info(self) -> _InfoDict:
        return {
            "directory": self._directory,
            "prefix": self._prefix,
            "routes": self._routes,
        }

    def set_options_route(self, handler: Handler) -> None:
        if "OPTIONS" in self._routes:
            raise RuntimeError("OPTIONS route was set already")
        self._routes["OPTIONS"] = ResourceRoute(
            "OPTIONS", handler, self, expect_handler=self._expect_handler
        )
        self._allowed_methods.add("OPTIONS")

    async def resolve(self, request: Request) -> _Resolve:
        path = request.rel_url.path_safe
        method = request.method
        # We normalise here to avoid matches that traverse below the static root.
        # e.g. /static/../../../../home/user/webapp/static/
        norm_path = os.path.normpath(path)
        if IS_WINDOWS:
            norm_path = norm_path.replace("\\", "/")
        if not norm_path.startswith(self._prefix2) and norm_path != self._prefix:
            return None, set()

        allowed_methods = self._allowed_methods
        if method not in allowed_methods:
            return None, allowed_methods

        match_dict = {"filename": _unquote_path_safe(path[len(self._prefix) + 1 :])}
        return (UrlMappingMatchInfo(match_dict, self._routes[method]), allowed_methods)

    def __len__(self) -> int:
        return len(self._routes)

    def __iter__(self) -> Iterator[AbstractRoute]:
        return iter(self._routes.values())

    async def _handle(self, request: Request) -> StreamResponse:
        filename = request.match_info["filename"]
        unresolved_path = self._directory.joinpath(filename)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._resolve_path_to_response, unresolved_path
        )

    def _resolve_path_to_response(self, unresolved_path: Path) -> StreamResponse:
        """Take the unresolved path and query the file system to form a response."""
        # Check for access outside the root directory. For follow symlinks, URI
        # cannot traverse out, but symlinks can. Otherwise, no access outside
        # root is permitted.
        try:
            if self._follow_symlinks:
                normalized_path = Path(os.path.normpath(unresolved_path))
                normalized_path.relative_to(self._directory)
                file_path = normalized_path.resolve()
            else:
                file_path = unresolved_path.resolve()
                file_path.relative_to(self._directory)
        except (ValueError, *CIRCULAR_SYMLINK_ERROR) as error:
            # ValueError is raised for the relative check. Circular symlinks
            # raise here on resolving for python < 3.13.
            raise HTTPNotFound() from error

        # if path is a directory, return the contents if permitted. Note the
        # directory check will raise if a segment is not readable.
        try:
            if file_path.is_dir():
                if self._show_index:
                    return Response(
                        text=self._directory_as_html(file_path),
                        content_type="text/html",
                    )
                else:
                    raise HTTPForbidden()
        except PermissionError as error:
            raise HTTPForbidden() from error

        # Return the file response, which handles all other checks.
        return FileResponse(file_path, chunk_size=self._chunk_size)

    def _directory_as_html(self, dir_path: Path) -> str:
        """returns directory's index as html."""
        assert dir_path.is_dir()

        relative_path_to_dir = dir_path.relative_to(self._directory).as_posix()
        index_of = f"Index of /{html_escape(relative_path_to_dir)}"
        h1 = f"<h1>{index_of}</h1>"

        index_list = []
        dir_index = dir_path.iterdir()
        for _file in sorted(dir_index):
            # show file url as relative to static path
            rel_path = _file.relative_to(self._directory).as_posix()
            quoted_file_url = _quote_path(f"{self._prefix}/{rel_path}")

            # if file is a directory, add '/' to the end of the name
            if _file.is_dir():
                file_name = f"{_file.name}/"
            else:
                file_name = _file.name

            index_list.append(
                f'<li><a href="{quoted_file_url}">{html_escape(file_name)}</a></li>'
            )
        ul = "<ul>\n{}\n</ul>".format("\n".join(index_list))
        body = f"<body>\n{h1}\n{ul}\n</body>"

        head_str = f"<head>\n<title>{index_of}</title>\n</head>"
        html = f"<html>\n{head_str}\n{body}\n</html>"

        return html

    def __repr__(self) -> str:
        name = "'" + self.name + "'" if self.name is not None else ""
        return "<StaticResource {name} {path} -> {directory!r}>".format(
            name=name, path=self._prefix, directory=self._directory
        )


class PrefixedSubAppResource(PrefixResource):
    def __init__(self, prefix: str, app: "Application") -> None:
        super().__init__(prefix)
        self._app = app
        self._add_prefix_to_resources(prefix)

    def add_prefix(self, prefix: str) -> None:
        super().add_prefix(prefix)
        self._add_prefix_to_resources(prefix)

    def _add_prefix_to_resources(self, prefix: str) -> None:
        router = self._app.router
        for resource in router.resources():
            # Since the canonical path of a resource is about
            # to change, we need to unindex it and then reindex
            router.unindex_resource(resource)
            resource.add_prefix(prefix)
            router.index_resource(resource)

    def url_for(self, *args: str, **kwargs: str) -> URL:
        raise RuntimeError(".url_for() is not supported by sub-application root")

    def get_info(self) -> _InfoDict:
        return {"app": self._app, "prefix": self._prefix}

    async def resolve(self, request: Request) -> _Resolve:
        match_info = await self._app.router.resolve(request)
        match_info.add_app(self._app)
        if isinstance(match_info.http_exception, HTTPMethodNotAllowed):
            methods = match_info.http_exception.allowed_methods
        else:
            methods = set()
        return match_info, methods

    def __len__(self) -> int:
        return len(self._app.router.routes())

    def __iter__(self) -> Iterator[AbstractRoute]:
        return iter(self._app.router.routes())

    def __repr__(self) -> str:
        return "<PrefixedSubAppResource {prefix} -> {app!r}>".format(
            prefix=self._prefix, app=self._app
        )


class AbstractRuleMatching(abc.ABC):
    @abc.abstractmethod  # pragma: no branch
    async def match(self, request: Request) -> bool:
        """Return bool if the request satisfies the criteria"""

    @abc.abstractmethod  # pragma: no branch
    def get_info(self) -> _InfoDict:
        """Return a dict with additional info useful for introspection"""

    @property
    @abc.abstractmethod  # pragma: no branch
    def canonical(self) -> str:
        """Return a str"""


class Domain(AbstractRuleMatching):
    re_part = re.compile(r"(?!-)[a-z\d-]{1,63}(?<!-)")

    def __init__(self, domain: str) -> None:
        super().__init__()
        self._domain = self.validation(domain)

    @property
    def canonical(self) -> str:
        return self._domain

    def validation(self, domain: str) -> str:
        if not isinstance(domain, str):
            raise TypeError("Domain must be str")
        domain = domain.rstrip(".").lower()
        if not domain:
            raise ValueError("Domain cannot be empty")
        elif "://" in domain:
            raise ValueError("Scheme not supported")
        url = URL("http://" + domain)
        assert url.raw_host is not None
        if not all(self.re_part.fullmatch(x) for x in url.raw_host.split(".")):
            raise ValueError("Domain not valid")
        if url.port == 80:
            return url.raw_host
        return f"{url.raw_host}:{url.port}"

    async def match(self, request: Request) -> bool:
        host = request.headers.get(hdrs.HOST)
        if not host:
            return False
        return self.match_domain(host)

    def match_domain(self, host: str) -> bool:
        return host.lower() == self._domain

    def get_info(self) -> _InfoDict:
        return {"domain": self._domain}


class MaskDomain(Domain):
    re_part = re.compile(r"(?!-)[a-z\d\*-]{1,63}(?<!-)")

    def __init__(self, domain: str) -> None:
        super().__init__(domain)
        mask = self._domain.replace(".", r"\.").replace("*", ".*")
        self._mask = re.compile(mask)

    @property
    def canonical(self) -> str:
        return self._mask.pattern

    def match_domain(self, host: str) -> bool:
        return self._mask.fullmatch(host) is not None


class MatchedSubAppResource(PrefixedSubAppResource):
    def __init__(self, rule: AbstractRuleMatching, app: "Application") -> None:
        AbstractResource.__init__(self)
        self._prefix = ""
        self._app = app
        self._rule = rule

    @property
    def canonical(self) -> str:
        return self._rule.canonical

    def get_info(self) -> _InfoDict:
        return {"app": self._app, "rule": self._rule}

    async def resolve(self, request: Request) -> _Resolve:
        if not await self._rule.match(request):
            return None, set()
        match_info = await self._app.router.resolve(request)
        match_info.add_app(self._app)
        if isinstance(match_info.http_exception, HTTPMethodNotAllowed):
            methods = match_info.http_exception.allowed_methods
        else:
            methods = set()
        return match_info, methods

    def __repr__(self) -> str:
        return f"<MatchedSubAppResource -> {self._app!r}>"


class ResourceRoute(AbstractRoute):
    """A route with resource"""

    def __init__(
        self,
        method: str,
        handler: Union[Handler, Type[AbstractView]],
        resource: AbstractResource,
        *,
        expect_handler: Optional[_ExpectHandler] = None,
    ) -> None:
        super().__init__(
            method, handler, expect_handler=expect_handler, resource=resource
        )

    def __repr__(self) -> str:
        return "<ResourceRoute [{method}] {resource} -> {handler!r}".format(
            method=self.method, resource=self._resource, handler=self.handler
        )

    @property
    def name(self) -> Optional[str]:
        if self._resource is None:
            return None
        return self._resource.name

    def url_for(self, *args: str, **kwargs: str) -> URL:
        """Construct url for route with additional params."""
        assert self._resource is not None
        return self._resource.url_for(*args, **kwargs)

    def get_info(self) -> _InfoDict:
        assert self._resource is not None
        return self._resource.get_info()


class SystemRoute(AbstractRoute):
    def __init__(self, http_exception: HTTPException) -> None:
        super().__init__(hdrs.METH_ANY, self._handle)
        self._http_exception = http_exception

    def url_for(self, *args: str, **kwargs: str) -> URL:
        raise RuntimeError(".url_for() is not allowed for SystemRoute")

    @property
    def name(self) -> Optional[str]:
        return None

    def get_info(self) -> _InfoDict:
        return {"http_exception": self._http_exception}

    async def _handle(self, request: Request) -> StreamResponse:
        raise self._http_exception

    @property
    def status(self) -> int:
        return self._http_exception.status

    @property
    def reason(self) -> str:
        return self._http_exception.reason

    def __repr__(self) -> str:
        return "<SystemRoute {self.status}: {self.reason}>".format(self=self)


class View(AbstractView):
    async def _iter(self) -> StreamResponse:
        if self.request.method not in hdrs.METH_ALL:
            self._raise_allowed_methods()
        method: Optional[Callable[[], Awaitable[StreamResponse]]]
        method = getattr(self, self.request.method.lower(), None)
        if method is None:
            self._raise_allowed_methods()
        ret = await method()
        assert isinstance(ret, StreamResponse)
        return ret

    def __await__(self) -> Generator[None, None, StreamResponse]:
        return self._iter().__await__()

    def _raise_allowed_methods(self) -> NoReturn:
        allowed_methods = {m for m in hdrs.METH_ALL if hasattr(self, m.lower())}
        raise HTTPMethodNotAllowed(self.request.method, allowed_methods)


class ResourcesView(Sized, Iterable[AbstractResource], Container[AbstractResource]):
    def __init__(self, resources: List[AbstractResource]) -> None:
        self._resources = resources

    def __len__(self) -> int:
        return len(self._resources)

    def __iter__(self) -> Iterator[AbstractResource]:
        yield from self._resources

    def __contains__(self, resource: object) -> bool:
        return resource in self._resources


class RoutesView(Sized, Iterable[AbstractRoute], Container[AbstractRoute]):
    def __init__(self, resources: List[AbstractResource]):
        self._routes: List[AbstractRoute] = []
        for resource in resources:
            for route in resource:
                self._routes.append(route)

    def __len__(self) -> int:
        return len(self._routes)

    def __iter__(self) -> Iterator[AbstractRoute]:
        yield from self._routes

    def __contains__(self, route: object) -> bool:
        return route in self._routes


class UrlDispatcher(AbstractRouter, Mapping[str, AbstractResource]):

    NAME_SPLIT_RE = re.compile(r"[.:-]")

    def __init__(self) -> None:
        super().__init__()
        self._resources: List[AbstractResource] = []
        self._named_resources: Dict[str, AbstractResource] = {}
        self._resource_index: dict[str, list[AbstractResource]] = {}
        self._matched_sub_app_resources: List[MatchedSubAppResource] = []

    async def resolve(self, request: Request) -> UrlMappingMatchInfo:
        resource_index = self._resource_index
        allowed_methods: Set[str] = set()

        # MatchedSubAppResource is primarily used to match on domain names
        # (though custom rules could match on other things). This means that
        # the traversal algorithm below can't be applied, and that we likely
        # need to check these first so a sub app that defines the same path
        # as a parent app will get priority if there's a domain match.
        #
        # For most cases we do not expect there to be many of these since
        # currently they are only added by `.add_domain()`.
        for resource in self._matched_sub_app_resources:
            match_dict, allowed = await resource.resolve(request)
            if match_dict is not None:
                return match_dict
            else:
                allowed_methods |= allowed

        # Walk the url parts looking for candidates. We walk the url backwards
        # to ensure the most explicit match is found first. If there are multiple
        # candidates for a given url part because there are multiple resources
        # registered for the same canonical path, we resolve them in a linear
        # fashion to ensure registration order is respected.
        url_part = request.rel_url.path_safe
        while url_part:
            for candidate in resource_index.get(url_part, ()):
                match_dict, allowed = await candidate.resolve(request)
                if match_dict is not None:
                    return match_dict
                else:
                    allowed_methods |= allowed
            if url_part == "/":
                break
            url_part = url_part.rpartition("/")[0] or "/"

        if allowed_methods:
            return MatchInfoError(HTTPMethodNotAllowed(request.method, allowed_methods))

        return MatchInfoError(HTTPNotFound())

    def __iter__(self) -> Iterator[str]:
        return iter(self._named_resources)

    def __len__(self) -> int:
        return len(self._named_resources)

    def __contains__(self, resource: object) -> bool:
        return resource in self._named_resources

    def __getitem__(self, name: str) -> AbstractResource:
        return self._named_resources[name]

    def resources(self) -> ResourcesView:
        return ResourcesView(self._resources)

    def routes(self) -> RoutesView:
        return RoutesView(self._resources)

    def named_resources(self) -> Mapping[str, AbstractResource]:
        return MappingProxyType(self._named_resources)

    def register_resource(self, resource: AbstractResource) -> None:
        assert isinstance(
            resource, AbstractResource
        ), f"Instance of AbstractResource class is required, got {resource!r}"
        if self.frozen:
            raise RuntimeError("Cannot register a resource into frozen router.")

        name = resource.name

        if name is not None:
            parts = self.NAME_SPLIT_RE.split(name)
            for part in parts:
                if keyword.iskeyword(part):
                    raise ValueError(
                        f"Incorrect route name {name!r}, "
                        "python keywords cannot be used "
                        "for route name"
                    )
                if not part.isidentifier():
                    raise ValueError(
                        "Incorrect route name {!r}, "
                        "the name should be a sequence of "
                        "python identifiers separated "
                        "by dash, dot or column".format(name)
                    )
            if name in self._named_resources:
                raise ValueError(
                    "Duplicate {!r}, "
                    "already handled by {!r}".format(name, self._named_resources[name])
                )
            self._named_resources[name] = resource
        self._resources.append(resource)

        if isinstance(resource, MatchedSubAppResource):
            # We cannot index match sub-app resources because they have match rules
            self._matched_sub_app_resources.append(resource)
        else:
            self.index_resource(resource)

    def _get_resource_index_key(self, resource: AbstractResource) -> str:
        """Return a key to index the resource in the resource index."""
        if "{" in (index_key := resource.canonical):
            # strip at the first { to allow for variables, and than
            # rpartition at / to allow for variable parts in the path
            # For example if the canonical path is `/core/locations{tail:.*}`
            # the index key will be `/core` since index is based on the
            # url parts split by `/`
            index_key = index_key.partition("{")[0].rpartition("/")[0]
        return index_key.rstrip("/") or "/"

    def index_resource(self, resource: AbstractResource) -> None:
        """Add a resource to the resource index."""
        resource_key = self._get_resource_index_key(resource)
        # There may be multiple resources for a canonical path
        # so we keep them in a list to ensure that registration
        # order is respected.
        self._resource_index.setdefault(resource_key, []).append(resource)

    def unindex_resource(self, resource: AbstractResource) -> None:
        """Remove a resource from the resource index."""
        resource_key = self._get_resource_index_key(resource)
        self._resource_index[resource_key].remove(resource)

    def add_resource(self, path: str, *, name: Optional[str] = None) -> Resource:
        if path and not path.startswith("/"):
            raise ValueError("path should be started with / or be empty")
        # Reuse last added resource if path and name are the same
        if self._resources:
            resource = self._resources[-1]
            if resource.name == name and resource.raw_match(path):
                return cast(Resource, resource)
        if not ("{" in path or "}" in path or ROUTE_RE.search(path)):
            resource = PlainResource(path, name=name)
            self.register_resource(resource)
            return resource
        resource = DynamicResource(path, name=name)
        self.register_resource(resource)
        return resource

    def add_route(
        self,
        method: str,
        path: str,
        handler: Union[Handler, Type[AbstractView]],
        *,
        name: Optional[str] = None,
        expect_handler: Optional[_ExpectHandler] = None,
    ) -> AbstractRoute:
        resource = self.add_resource(path, name=name)
        return resource.add_route(method, handler, expect_handler=expect_handler)

    def add_static(
        self,
        prefix: str,
        path: PathLike,
        *,
        name: Optional[str] = None,
        expect_handler: Optional[_ExpectHandler] = None,
        chunk_size: int = 256 * 1024,
        show_index: bool = False,
        follow_symlinks: bool = False,
        append_version: bool = False,
    ) -> AbstractResource:
        """Add static files view.

        prefix - url prefix
        path - folder with files

        """
        assert prefix.startswith("/")
        if prefix.endswith("/"):
            prefix = prefix[:-1]
        resource = StaticResource(
            prefix,
            path,
            name=name,
            expect_handler=expect_handler,
            chunk_size=chunk_size,
            show_index=show_index,
            follow_symlinks=follow_symlinks,
            append_version=append_version,
        )
        self.register_resource(resource)
        return resource

    def add_head(self, path: str, handler: Handler, **kwargs: Any) -> AbstractRoute:
        """Shortcut for add_route with method HEAD."""
        return self.add_route(hdrs.METH_HEAD, path, handler, **kwargs)

    def add_options(self, path: str, handler: Handler, **kwargs: Any) -> AbstractRoute:
        """Shortcut for add_route with method OPTIONS."""
        return self.add_route(hdrs.METH_OPTIONS, path, handler, **kwargs)

    def add_get(
        self,
        path: str,
        handler: Handler,
        *,
        name: Optional[str] = None,
        allow_head: bool = True,
        **kwargs: Any,
    ) -> AbstractRoute:
        """Shortcut for add_route with method GET.

        If allow_head is true, another
        route is added allowing head requests to the same endpoint.
        """
        resource = self.add_resource(path, name=name)
        if allow_head:
            resource.add_route(hdrs.METH_HEAD, handler, **kwargs)
        return resource.add_route(hdrs.METH_GET, handler, **kwargs)

    def add_post(self, path: str, handler: Handler, **kwargs: Any) -> AbstractRoute:
        """Shortcut for add_route with method POST."""
        return self.add_route(hdrs.METH_POST, path, handler, **kwargs)

    def add_put(self, path: str, handler: Handler, **kwargs: Any) -> AbstractRoute:
        """Shortcut for add_route with method PUT."""
        return self.add_route(hdrs.METH_PUT, path, handler, **kwargs)

    def add_patch(self, path: str, handler: Handler, **kwargs: Any) -> AbstractRoute:
        """Shortcut for add_route with method PATCH."""
        return self.add_route(hdrs.METH_PATCH, path, handler, **kwargs)

    def add_delete(self, path: str, handler: Handler, **kwargs: Any) -> AbstractRoute:
        """Shortcut for add_route with method DELETE."""
        return self.add_route(hdrs.METH_DELETE, path, handler, **kwargs)

    def add_view(
        self, path: str, handler: Type[AbstractView], **kwargs: Any
    ) -> AbstractRoute:
        """Shortcut for add_route with ANY methods for a class-based view."""
        return self.add_route(hdrs.METH_ANY, path, handler, **kwargs)

    def freeze(self) -> None:
        super().freeze()
        for resource in self._resources:
            resource.freeze()

    def add_routes(self, routes: Iterable[AbstractRouteDef]) -> List[AbstractRoute]:
        """Append routes to route table.

        Parameter should be a sequence of RouteDef objects.

        Returns a list of registered AbstractRoute instances.
        """
        registered_routes = []
        for route_def in routes:
            registered_routes.extend(route_def.register(self))
        return registered_routes


def _quote_path(value: str) -> str:
    if YARL_VERSION < (1, 6):
        value = value.replace("%", "%25")
    return URL.build(path=value, encoded=False).raw_path


def _unquote_path_safe(value: str) -> str:
    if "%" not in value:
        return value
    return value.replace("%2F", "/").replace("%25", "%")


def _requote_path(value: str) -> str:
    # Quote non-ascii characters and other characters which must be quoted,
    # but preserve existing %-sequences.
    result = _quote_path(value)
    if "%" in value:
        result = result.replace("%25", "%")
    return result
