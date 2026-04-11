import re
import sys
import warnings
from collections.abc import Mapping, Sequence
from enum import Enum
from functools import _CacheInfo, lru_cache
from ipaddress import ip_address
from typing import (
    TYPE_CHECKING,
    Any,
    NoReturn,
    TypedDict,
    TypeVar,
    Union,
    cast,
    overload,
)
from urllib.parse import SplitResult, uses_relative

import idna
from multidict import MultiDict, MultiDictProxy, istr
from propcache.api import under_cached_property as cached_property

from ._parse import (
    USES_AUTHORITY,
    SplitURLType,
    make_netloc,
    query_to_pairs,
    split_netloc,
    split_url,
    unsplit_result,
)
from ._path import normalize_path, normalize_path_segments
from ._query import (
    Query,
    QueryVariable,
    SimpleQuery,
    get_str_query,
    get_str_query_from_iterable,
    get_str_query_from_sequence_iterable,
)
from ._quoters import (
    FRAGMENT_QUOTER,
    FRAGMENT_REQUOTER,
    PATH_QUOTER,
    PATH_REQUOTER,
    PATH_SAFE_UNQUOTER,
    PATH_UNQUOTER,
    QS_UNQUOTER,
    QUERY_QUOTER,
    QUERY_REQUOTER,
    QUOTER,
    REQUOTER,
    UNQUOTER,
    human_quote,
)

DEFAULT_PORTS = {"http": 80, "https": 443, "ws": 80, "wss": 443, "ftp": 21}
USES_RELATIVE = frozenset(uses_relative)

# Special schemes https://url.spec.whatwg.org/#special-scheme
# are not allowed to have an empty host https://url.spec.whatwg.org/#url-representation
SCHEME_REQUIRES_HOST = frozenset(("http", "https", "ws", "wss", "ftp"))


# reg-name: unreserved / pct-encoded / sub-delims
# this pattern matches anything that is *not* in those classes. and is only used
# on lower-cased ASCII values.
NOT_REG_NAME = re.compile(
    r"""
        # any character not in the unreserved or sub-delims sets, plus %
        # (validated with the additional check for pct-encoded sequences below)
        [^a-z0-9\-._~!$&'()*+,;=%]
    |
        # % only allowed if it is part of a pct-encoded
        # sequence of 2 hex digits.
        %(?![0-9a-f]{2})
    """,
    re.VERBOSE,
)

_T = TypeVar("_T")

if sys.version_info >= (3, 11):
    from typing import Self
else:
    Self = Any


class UndefinedType(Enum):
    """Singleton type for use with not set sentinel values."""

    _singleton = 0


UNDEFINED = UndefinedType._singleton


class CacheInfo(TypedDict):
    """Host encoding cache."""

    idna_encode: _CacheInfo
    idna_decode: _CacheInfo
    ip_address: _CacheInfo
    host_validate: _CacheInfo
    encode_host: _CacheInfo


class _InternalURLCache(TypedDict, total=False):
    _val: SplitURLType
    _origin: "URL"
    absolute: bool
    hash: int
    scheme: str
    raw_authority: str
    authority: str
    raw_user: Union[str, None]
    user: Union[str, None]
    raw_password: Union[str, None]
    password: Union[str, None]
    raw_host: Union[str, None]
    host: Union[str, None]
    host_subcomponent: Union[str, None]
    host_port_subcomponent: Union[str, None]
    port: Union[int, None]
    explicit_port: Union[int, None]
    raw_path: str
    path: str
    _parsed_query: list[tuple[str, str]]
    query: "MultiDictProxy[str]"
    raw_query_string: str
    query_string: str
    path_qs: str
    raw_path_qs: str
    raw_fragment: str
    fragment: str
    raw_parts: tuple[str, ...]
    parts: tuple[str, ...]
    parent: "URL"
    raw_name: str
    name: str
    raw_suffix: str
    suffix: str
    raw_suffixes: tuple[str, ...]
    suffixes: tuple[str, ...]


def rewrite_module(obj: _T) -> _T:
    obj.__module__ = "yarl"
    return obj


@lru_cache
def encode_url(url_str: str) -> "URL":
    """Parse unencoded URL."""
    cache: _InternalURLCache = {}
    host: Union[str, None]
    scheme, netloc, path, query, fragment = split_url(url_str)
    if not netloc:  # netloc
        host = ""
    else:
        if ":" in netloc or "@" in netloc or "[" in netloc:
            # Complex netloc
            username, password, host, port = split_netloc(netloc)
        else:
            username = password = port = None
            host = netloc
        if host is None:
            if scheme in SCHEME_REQUIRES_HOST:
                msg = (
                    "Invalid URL: host is required for "
                    f"absolute urls with the {scheme} scheme"
                )
                raise ValueError(msg)
            else:
                host = ""
        host = _encode_host(host, validate_host=False)
        # Remove brackets as host encoder adds back brackets for IPv6 addresses
        cache["raw_host"] = host[1:-1] if "[" in host else host
        cache["explicit_port"] = port
        if password is None and username is None:
            # Fast path for URLs without user, password
            netloc = host if port is None else f"{host}:{port}"
            cache["raw_user"] = None
            cache["raw_password"] = None
        else:
            raw_user = REQUOTER(username) if username else username
            raw_password = REQUOTER(password) if password else password
            netloc = make_netloc(raw_user, raw_password, host, port)
            cache["raw_user"] = raw_user
            cache["raw_password"] = raw_password

    if path:
        path = PATH_REQUOTER(path)
        if netloc and "." in path:
            path = normalize_path(path)
    if query:
        query = QUERY_REQUOTER(query)
    if fragment:
        fragment = FRAGMENT_REQUOTER(fragment)

    cache["scheme"] = scheme
    cache["raw_path"] = "/" if not path and netloc else path
    cache["raw_query_string"] = query
    cache["raw_fragment"] = fragment

    self = object.__new__(URL)
    self._scheme = scheme
    self._netloc = netloc
    self._path = path
    self._query = query
    self._fragment = fragment
    self._cache = cache
    return self


@lru_cache
def pre_encoded_url(url_str: str) -> "URL":
    """Parse pre-encoded URL."""
    self = object.__new__(URL)
    val = split_url(url_str)
    self._scheme, self._netloc, self._path, self._query, self._fragment = val
    self._cache = {}
    return self


@lru_cache
def build_pre_encoded_url(
    scheme: str,
    authority: str,
    user: Union[str, None],
    password: Union[str, None],
    host: str,
    port: Union[int, None],
    path: str,
    query_string: str,
    fragment: str,
) -> "URL":
    """Build a pre-encoded URL from parts."""
    self = object.__new__(URL)
    self._scheme = scheme
    if authority:
        self._netloc = authority
    elif host:
        if port is not None:
            port = None if port == DEFAULT_PORTS.get(scheme) else port
        if user is None and password is None:
            self._netloc = host if port is None else f"{host}:{port}"
        else:
            self._netloc = make_netloc(user, password, host, port)
    else:
        self._netloc = ""
    self._path = path
    self._query = query_string
    self._fragment = fragment
    self._cache = {}
    return self


def from_parts_uncached(
    scheme: str, netloc: str, path: str, query: str, fragment: str
) -> "URL":
    """Create a new URL from parts."""
    self = object.__new__(URL)
    self._scheme = scheme
    self._netloc = netloc
    self._path = path
    self._query = query
    self._fragment = fragment
    self._cache = {}
    return self


from_parts = lru_cache(from_parts_uncached)


@rewrite_module
class URL:
    # Don't derive from str
    # follow pathlib.Path design
    # probably URL will not suffer from pathlib problems:
    # it's intended for libraries like aiohttp,
    # not to be passed into standard library functions like os.open etc.

    # URL grammar (RFC 3986)
    # pct-encoded = "%" HEXDIG HEXDIG
    # reserved    = gen-delims / sub-delims
    # gen-delims  = ":" / "/" / "?" / "#" / "[" / "]" / "@"
    # sub-delims  = "!" / "$" / "&" / "'" / "(" / ")"
    #             / "*" / "+" / "," / ";" / "="
    # unreserved  = ALPHA / DIGIT / "-" / "." / "_" / "~"
    # URI         = scheme ":" hier-part [ "?" query ] [ "#" fragment ]
    # hier-part   = "//" authority path-abempty
    #             / path-absolute
    #             / path-rootless
    #             / path-empty
    # scheme      = ALPHA *( ALPHA / DIGIT / "+" / "-" / "." )
    # authority   = [ userinfo "@" ] host [ ":" port ]
    # userinfo    = *( unreserved / pct-encoded / sub-delims / ":" )
    # host        = IP-literal / IPv4address / reg-name
    # IP-literal = "[" ( IPv6address / IPvFuture  ) "]"
    # IPvFuture  = "v" 1*HEXDIG "." 1*( unreserved / sub-delims / ":" )
    # IPv6address =                            6( h16 ":" ) ls32
    #             /                       "::" 5( h16 ":" ) ls32
    #             / [               h16 ] "::" 4( h16 ":" ) ls32
    #             / [ *1( h16 ":" ) h16 ] "::" 3( h16 ":" ) ls32
    #             / [ *2( h16 ":" ) h16 ] "::" 2( h16 ":" ) ls32
    #             / [ *3( h16 ":" ) h16 ] "::"    h16 ":"   ls32
    #             / [ *4( h16 ":" ) h16 ] "::"              ls32
    #             / [ *5( h16 ":" ) h16 ] "::"              h16
    #             / [ *6( h16 ":" ) h16 ] "::"
    # ls32        = ( h16 ":" h16 ) / IPv4address
    #             ; least-significant 32 bits of address
    # h16         = 1*4HEXDIG
    #             ; 16 bits of address represented in hexadecimal
    # IPv4address = dec-octet "." dec-octet "." dec-octet "." dec-octet
    # dec-octet   = DIGIT                 ; 0-9
    #             / %x31-39 DIGIT         ; 10-99
    #             / "1" 2DIGIT            ; 100-199
    #             / "2" %x30-34 DIGIT     ; 200-249
    #             / "25" %x30-35          ; 250-255
    # reg-name    = *( unreserved / pct-encoded / sub-delims )
    # port        = *DIGIT
    # path          = path-abempty    ; begins with "/" or is empty
    #               / path-absolute   ; begins with "/" but not "//"
    #               / path-noscheme   ; begins with a non-colon segment
    #               / path-rootless   ; begins with a segment
    #               / path-empty      ; zero characters
    # path-abempty  = *( "/" segment )
    # path-absolute = "/" [ segment-nz *( "/" segment ) ]
    # path-noscheme = segment-nz-nc *( "/" segment )
    # path-rootless = segment-nz *( "/" segment )
    # path-empty    = 0<pchar>
    # segment       = *pchar
    # segment-nz    = 1*pchar
    # segment-nz-nc = 1*( unreserved / pct-encoded / sub-delims / "@" )
    #               ; non-zero-length segment without any colon ":"
    # pchar         = unreserved / pct-encoded / sub-delims / ":" / "@"
    # query       = *( pchar / "/" / "?" )
    # fragment    = *( pchar / "/" / "?" )
    # URI-reference = URI / relative-ref
    # relative-ref  = relative-part [ "?" query ] [ "#" fragment ]
    # relative-part = "//" authority path-abempty
    #               / path-absolute
    #               / path-noscheme
    #               / path-empty
    # absolute-URI  = scheme ":" hier-part [ "?" query ]
    __slots__ = ("_cache", "_scheme", "_netloc", "_path", "_query", "_fragment")

    _cache: _InternalURLCache
    _scheme: str
    _netloc: str
    _path: str
    _query: str
    _fragment: str

    def __new__(
        cls,
        val: Union[str, SplitResult, "URL", UndefinedType] = UNDEFINED,
        *,
        encoded: bool = False,
        strict: Union[bool, None] = None,
    ) -> "URL":
        if strict is not None:  # pragma: no cover
            warnings.warn("strict parameter is ignored")
        if type(val) is str:
            return pre_encoded_url(val) if encoded else encode_url(val)
        if type(val) is cls:
            return val
        if type(val) is SplitResult:
            if not encoded:
                raise ValueError("Cannot apply decoding to SplitResult")
            return from_parts(*val)
        if isinstance(val, str):
            return pre_encoded_url(str(val)) if encoded else encode_url(str(val))
        if val is UNDEFINED:
            # Special case for UNDEFINED since it might be unpickling and we do
            # not want to cache as the `__set_state__` call would mutate the URL
            # object in the `pre_encoded_url` or `encoded_url` caches.
            self = object.__new__(URL)
            self._scheme = self._netloc = self._path = self._query = self._fragment = ""
            self._cache = {}
            return self
        raise TypeError("Constructor parameter should be str")

    @classmethod
    def build(
        cls,
        *,
        scheme: str = "",
        authority: str = "",
        user: Union[str, None] = None,
        password: Union[str, None] = None,
        host: str = "",
        port: Union[int, None] = None,
        path: str = "",
        query: Union[Query, None] = None,
        query_string: str = "",
        fragment: str = "",
        encoded: bool = False,
    ) -> "URL":
        """Creates and returns a new URL"""

        if authority and (user or password or host or port):
            raise ValueError(
                'Can\'t mix "authority" with "user", "password", "host" or "port".'
            )
        if port is not None and not isinstance(port, int):
            raise TypeError(f"The port is required to be int, got {type(port)!r}.")
        if port and not host:
            raise ValueError('Can\'t build URL with "port" but without "host".')
        if query and query_string:
            raise ValueError('Only one of "query" or "query_string" should be passed')
        if (
            scheme is None  # type: ignore[redundant-expr]
            or authority is None  # type: ignore[redundant-expr]
            or host is None  # type: ignore[redundant-expr]
            or path is None  # type: ignore[redundant-expr]
            or query_string is None  # type: ignore[redundant-expr]
            or fragment is None
        ):
            raise TypeError(
                'NoneType is illegal for "scheme", "authority", "host", "path", '
                '"query_string", and "fragment" args, use empty string instead.'
            )

        if query:
            query_string = get_str_query(query) or ""

        if encoded:
            return build_pre_encoded_url(
                scheme,
                authority,
                user,
                password,
                host,
                port,
                path,
                query_string,
                fragment,
            )

        self = object.__new__(URL)
        self._scheme = scheme
        _host: Union[str, None] = None
        if authority:
            user, password, _host, port = split_netloc(authority)
            _host = _encode_host(_host, validate_host=False) if _host else ""
        elif host:
            _host = _encode_host(host, validate_host=True)
        else:
            self._netloc = ""

        if _host is not None:
            if port is not None:
                port = None if port == DEFAULT_PORTS.get(scheme) else port
            if user is None and password is None:
                self._netloc = _host if port is None else f"{_host}:{port}"
            else:
                self._netloc = make_netloc(user, password, _host, port, True)

        path = PATH_QUOTER(path) if path else path
        if path and self._netloc:
            if "." in path:
                path = normalize_path(path)
            if path[0] != "/":
                msg = (
                    "Path in a URL with authority should "
                    "start with a slash ('/') if set"
                )
                raise ValueError(msg)

        self._path = path
        if not query and query_string:
            query_string = QUERY_QUOTER(query_string)
        self._query = query_string
        self._fragment = FRAGMENT_QUOTER(fragment) if fragment else fragment
        self._cache = {}
        return self

    def __init_subclass__(cls) -> NoReturn:
        raise TypeError(f"Inheriting a class {cls!r} from URL is forbidden")

    def __str__(self) -> str:
        if not self._path and self._netloc and (self._query or self._fragment):
            path = "/"
        else:
            path = self._path
        if (port := self.explicit_port) is not None and port == DEFAULT_PORTS.get(
            self._scheme
        ):
            # port normalization - using None for default ports to remove from rendering
            # https://datatracker.ietf.org/doc/html/rfc3986.html#section-6.2.3
            host = self.host_subcomponent
            netloc = make_netloc(self.raw_user, self.raw_password, host, None)
        else:
            netloc = self._netloc
        return unsplit_result(self._scheme, netloc, path, self._query, self._fragment)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{str(self)}')"

    def __bytes__(self) -> bytes:
        return str(self).encode("ascii")

    def __eq__(self, other: object) -> bool:
        if type(other) is not URL:
            return NotImplemented

        path1 = "/" if not self._path and self._netloc else self._path
        path2 = "/" if not other._path and other._netloc else other._path
        return (
            self._scheme == other._scheme
            and self._netloc == other._netloc
            and path1 == path2
            and self._query == other._query
            and self._fragment == other._fragment
        )

    def __hash__(self) -> int:
        if (ret := self._cache.get("hash")) is None:
            path = "/" if not self._path and self._netloc else self._path
            ret = self._cache["hash"] = hash(
                (self._scheme, self._netloc, path, self._query, self._fragment)
            )
        return ret

    def __le__(self, other: object) -> bool:
        if type(other) is not URL:
            return NotImplemented
        return self._val <= other._val

    def __lt__(self, other: object) -> bool:
        if type(other) is not URL:
            return NotImplemented
        return self._val < other._val

    def __ge__(self, other: object) -> bool:
        if type(other) is not URL:
            return NotImplemented
        return self._val >= other._val

    def __gt__(self, other: object) -> bool:
        if type(other) is not URL:
            return NotImplemented
        return self._val > other._val

    def __truediv__(self, name: str) -> "URL":
        if not isinstance(name, str):
            return NotImplemented  # type: ignore[unreachable]
        return self._make_child((str(name),))

    def __mod__(self, query: Query) -> "URL":
        return self.update_query(query)

    def __bool__(self) -> bool:
        return bool(self._netloc or self._path or self._query or self._fragment)

    def __getstate__(self) -> tuple[SplitResult]:
        return (tuple.__new__(SplitResult, self._val),)

    def __setstate__(
        self, state: Union[tuple[SplitURLType], tuple[None, _InternalURLCache]]
    ) -> None:
        if state[0] is None and isinstance(state[1], dict):
            # default style pickle
            val = state[1]["_val"]
        else:
            unused: list[object]
            val, *unused = state
        self._scheme, self._netloc, self._path, self._query, self._fragment = val
        self._cache = {}

    def _cache_netloc(self) -> None:
        """Cache the netloc parts of the URL."""
        c = self._cache
        split_loc = split_netloc(self._netloc)
        c["raw_user"], c["raw_password"], c["raw_host"], c["explicit_port"] = split_loc

    def is_absolute(self) -> bool:
        """A check for absolute URLs.

        Return True for absolute ones (having scheme or starting
        with //), False otherwise.

        Is is preferred to call the .absolute property instead
        as it is cached.
        """
        return self.absolute

    def is_default_port(self) -> bool:
        """A check for default port.

        Return True if port is default for specified scheme,
        e.g. 'http://python.org' or 'http://python.org:80', False
        otherwise.

        Return False for relative URLs.

        """
        if (explicit := self.explicit_port) is None:
            # If the explicit port is None, then the URL must be
            # using the default port unless its a relative URL
            # which does not have an implicit port / default port
            return self._netloc != ""
        return explicit == DEFAULT_PORTS.get(self._scheme)

    def origin(self) -> "URL":
        """Return an URL with scheme, host and port parts only.

        user, password, path, query and fragment are removed.

        """
        # TODO: add a keyword-only option for keeping user/pass maybe?
        return self._origin

    @cached_property
    def _val(self) -> SplitURLType:
        return (self._scheme, self._netloc, self._path, self._query, self._fragment)

    @cached_property
    def _origin(self) -> "URL":
        """Return an URL with scheme, host and port parts only.

        user, password, path, query and fragment are removed.
        """
        if not (netloc := self._netloc):
            raise ValueError("URL should be absolute")
        if not (scheme := self._scheme):
            raise ValueError("URL should have scheme")
        if "@" in netloc:
            encoded_host = self.host_subcomponent
            netloc = make_netloc(None, None, encoded_host, self.explicit_port)
        elif not self._path and not self._query and not self._fragment:
            return self
        return from_parts(scheme, netloc, "", "", "")

    def relative(self) -> "URL":
        """Return a relative part of the URL.

        scheme, user, password, host and port are removed.

        """
        if not self._netloc:
            raise ValueError("URL should be absolute")
        return from_parts("", "", self._path, self._query, self._fragment)

    @cached_property
    def absolute(self) -> bool:
        """A check for absolute URLs.

        Return True for absolute ones (having scheme or starting
        with //), False otherwise.

        """
        # `netloc`` is an empty string for relative URLs
        # Checking `netloc` is faster than checking `hostname`
        # because `hostname` is a property that does some extra work
        # to parse the host from the `netloc`
        return self._netloc != ""

    @cached_property
    def scheme(self) -> str:
        """Scheme for absolute URLs.

        Empty string for relative URLs or URLs starting with //

        """
        return self._scheme

    @cached_property
    def raw_authority(self) -> str:
        """Encoded authority part of URL.

        Empty string for relative URLs.

        """
        return self._netloc

    @cached_property
    def authority(self) -> str:
        """Decoded authority part of URL.

        Empty string for relative URLs.

        """
        return make_netloc(self.user, self.password, self.host, self.port)

    @cached_property
    def raw_user(self) -> Union[str, None]:
        """Encoded user part of URL.

        None if user is missing.

        """
        # not .username
        self._cache_netloc()
        return self._cache["raw_user"]

    @cached_property
    def user(self) -> Union[str, None]:
        """Decoded user part of URL.

        None if user is missing.

        """
        if (raw_user := self.raw_user) is None:
            return None
        return UNQUOTER(raw_user)

    @cached_property
    def raw_password(self) -> Union[str, None]:
        """Encoded password part of URL.

        None if password is missing.

        """
        self._cache_netloc()
        return self._cache["raw_password"]

    @cached_property
    def password(self) -> Union[str, None]:
        """Decoded password part of URL.

        None if password is missing.

        """
        if (raw_password := self.raw_password) is None:
            return None
        return UNQUOTER(raw_password)

    @cached_property
    def raw_host(self) -> Union[str, None]:
        """Encoded host part of URL.

        None for relative URLs.

        When working with IPv6 addresses, use the `host_subcomponent` property instead
        as it will return the host subcomponent with brackets.
        """
        # Use host instead of hostname for sake of shortness
        # May add .hostname prop later
        self._cache_netloc()
        return self._cache["raw_host"]

    @cached_property
    def host(self) -> Union[str, None]:
        """Decoded host part of URL.

        None for relative URLs.

        """
        if (raw := self.raw_host) is None:
            return None
        if raw and raw[-1].isdigit() or ":" in raw:
            # IP addresses are never IDNA encoded
            return raw
        return _idna_decode(raw)

    @cached_property
    def host_subcomponent(self) -> Union[str, None]:
        """Return the host subcomponent part of URL.

        None for relative URLs.

        https://datatracker.ietf.org/doc/html/rfc3986#section-3.2.2

        `IP-literal = "[" ( IPv6address / IPvFuture  ) "]"`

        Examples:
        - `http://example.com:8080` -> `example.com`
        - `http://example.com:80` -> `example.com`
        - `https://127.0.0.1:8443` -> `127.0.0.1`
        - `https://[::1]:8443` -> `[::1]`
        - `http://[::1]` -> `[::1]`

        """
        if (raw := self.raw_host) is None:
            return None
        return f"[{raw}]" if ":" in raw else raw

    @cached_property
    def host_port_subcomponent(self) -> Union[str, None]:
        """Return the host and port subcomponent part of URL.

        Trailing dots are removed from the host part.

        This value is suitable for use in the Host header of an HTTP request.

        None for relative URLs.

        https://datatracker.ietf.org/doc/html/rfc3986#section-3.2.2
        `IP-literal = "[" ( IPv6address / IPvFuture  ) "]"`
        https://datatracker.ietf.org/doc/html/rfc3986#section-3.2.3
        port        = *DIGIT

        Examples:
        - `http://example.com:8080` -> `example.com:8080`
        - `http://example.com:80` -> `example.com`
        - `http://example.com.:80` -> `example.com`
        - `https://127.0.0.1:8443` -> `127.0.0.1:8443`
        - `https://[::1]:8443` -> `[::1]:8443`
        - `http://[::1]` -> `[::1]`

        """
        if (raw := self.raw_host) is None:
            return None
        if raw[-1] == ".":
            # Remove all trailing dots from the netloc as while
            # they are valid FQDNs in DNS, TLS validation fails.
            # See https://github.com/aio-libs/aiohttp/issues/3636.
            # To avoid string manipulation we only call rstrip if
            # the last character is a dot.
            raw = raw.rstrip(".")
        port = self.explicit_port
        if port is None or port == DEFAULT_PORTS.get(self._scheme):
            return f"[{raw}]" if ":" in raw else raw
        return f"[{raw}]:{port}" if ":" in raw else f"{raw}:{port}"

    @cached_property
    def port(self) -> Union[int, None]:
        """Port part of URL, with scheme-based fallback.

        None for relative URLs or URLs without explicit port and
        scheme without default port substitution.

        """
        if (explicit_port := self.explicit_port) is not None:
            return explicit_port
        return DEFAULT_PORTS.get(self._scheme)

    @cached_property
    def explicit_port(self) -> Union[int, None]:
        """Port part of URL, without scheme-based fallback.

        None for relative URLs or URLs without explicit port.

        """
        self._cache_netloc()
        return self._cache["explicit_port"]

    @cached_property
    def raw_path(self) -> str:
        """Encoded path of URL.

        / for absolute URLs without path part.

        """
        return self._path if self._path or not self._netloc else "/"

    @cached_property
    def path(self) -> str:
        """Decoded path of URL.

        / for absolute URLs without path part.

        """
        return PATH_UNQUOTER(self._path) if self._path else "/" if self._netloc else ""

    @cached_property
    def path_safe(self) -> str:
        """Decoded path of URL.

        / for absolute URLs without path part.

        / (%2F) and % (%25) are not decoded

        """
        if self._path:
            return PATH_SAFE_UNQUOTER(self._path)
        return "/" if self._netloc else ""

    @cached_property
    def _parsed_query(self) -> list[tuple[str, str]]:
        """Parse query part of URL."""
        return query_to_pairs(self._query)

    @cached_property
    def query(self) -> "MultiDictProxy[str]":
        """A MultiDictProxy representing parsed query parameters in decoded
        representation.

        Empty value if URL has no query part.

        """
        return MultiDictProxy(MultiDict(self._parsed_query))

    @cached_property
    def raw_query_string(self) -> str:
        """Encoded query part of URL.

        Empty string if query is missing.

        """
        return self._query

    @cached_property
    def query_string(self) -> str:
        """Decoded query part of URL.

        Empty string if query is missing.

        """
        return QS_UNQUOTER(self._query) if self._query else ""

    @cached_property
    def path_qs(self) -> str:
        """Decoded path of URL with query."""
        return self.path if not (q := self.query_string) else f"{self.path}?{q}"

    @cached_property
    def raw_path_qs(self) -> str:
        """Encoded path of URL with query."""
        if q := self._query:
            return f"{self._path}?{q}" if self._path or not self._netloc else f"/?{q}"
        return self._path if self._path or not self._netloc else "/"

    @cached_property
    def raw_fragment(self) -> str:
        """Encoded fragment part of URL.

        Empty string if fragment is missing.

        """
        return self._fragment

    @cached_property
    def fragment(self) -> str:
        """Decoded fragment part of URL.

        Empty string if fragment is missing.

        """
        return UNQUOTER(self._fragment) if self._fragment else ""

    @cached_property
    def raw_parts(self) -> tuple[str, ...]:
        """A tuple containing encoded *path* parts.

        ('/',) for absolute URLs if *path* is missing.

        """
        path = self._path
        if self._netloc:
            return ("/", *path[1:].split("/")) if path else ("/",)
        if path and path[0] == "/":
            return ("/", *path[1:].split("/"))
        return tuple(path.split("/"))

    @cached_property
    def parts(self) -> tuple[str, ...]:
        """A tuple containing decoded *path* parts.

        ('/',) for absolute URLs if *path* is missing.

        """
        return tuple(UNQUOTER(part) for part in self.raw_parts)

    @cached_property
    def parent(self) -> "URL":
        """A new URL with last part of path removed and cleaned up query and
        fragment.

        """
        path = self._path
        if not path or path == "/":
            if self._fragment or self._query:
                return from_parts(self._scheme, self._netloc, path, "", "")
            return self
        parts = path.split("/")
        return from_parts(self._scheme, self._netloc, "/".join(parts[:-1]), "", "")

    @cached_property
    def raw_name(self) -> str:
        """The last part of raw_parts."""
        parts = self.raw_parts
        if not self._netloc:
            return parts[-1]
        parts = parts[1:]
        return parts[-1] if parts else ""

    @cached_property
    def name(self) -> str:
        """The last part of parts."""
        return UNQUOTER(self.raw_name)

    @cached_property
    def raw_suffix(self) -> str:
        name = self.raw_name
        i = name.rfind(".")
        return name[i:] if 0 < i < len(name) - 1 else ""

    @cached_property
    def suffix(self) -> str:
        return UNQUOTER(self.raw_suffix)

    @cached_property
    def raw_suffixes(self) -> tuple[str, ...]:
        name = self.raw_name
        if name.endswith("."):
            return ()
        name = name.lstrip(".")
        return tuple("." + suffix for suffix in name.split(".")[1:])

    @cached_property
    def suffixes(self) -> tuple[str, ...]:
        return tuple(UNQUOTER(suffix) for suffix in self.raw_suffixes)

    def _make_child(self, paths: "Sequence[str]", encoded: bool = False) -> "URL":
        """
        add paths to self._path, accounting for absolute vs relative paths,
        keep existing, but do not create new, empty segments
        """
        parsed: list[str] = []
        needs_normalize: bool = False
        for idx, path in enumerate(reversed(paths)):
            # empty segment of last is not removed
            last = idx == 0
            if path and path[0] == "/":
                raise ValueError(
                    f"Appending path {path!r} starting from slash is forbidden"
                )
            # We need to quote the path if it is not already encoded
            # This cannot be done at the end because the existing
            # path is already quoted and we do not want to double quote
            # the existing path.
            path = path if encoded else PATH_QUOTER(path)
            needs_normalize |= "." in path
            segments = path.split("/")
            segments.reverse()
            # remove trailing empty segment for all but the last path
            parsed += segments[1:] if not last and segments[0] == "" else segments

        if (path := self._path) and (old_segments := path.split("/")):
            # If the old path ends with a slash, the last segment is an empty string
            # and should be removed before adding the new path segments.
            old = old_segments[:-1] if old_segments[-1] == "" else old_segments
            old.reverse()
            parsed += old

        # If the netloc is present, inject a leading slash when adding a
        # path to an absolute URL where there was none before.
        if (netloc := self._netloc) and parsed and parsed[-1] != "":
            parsed.append("")

        parsed.reverse()
        if not netloc or not needs_normalize:
            return from_parts(self._scheme, netloc, "/".join(parsed), "", "")

        path = "/".join(normalize_path_segments(parsed))
        # If normalizing the path segments removed the leading slash, add it back.
        if path and path[0] != "/":
            path = f"/{path}"
        return from_parts(self._scheme, netloc, path, "", "")

    def with_scheme(self, scheme: str) -> "URL":
        """Return a new URL with scheme replaced."""
        # N.B. doesn't cleanup query/fragment
        if not isinstance(scheme, str):
            raise TypeError("Invalid scheme type")
        lower_scheme = scheme.lower()
        netloc = self._netloc
        if not netloc and lower_scheme in SCHEME_REQUIRES_HOST:
            msg = (
                "scheme replacement is not allowed for "
                f"relative URLs for the {lower_scheme} scheme"
            )
            raise ValueError(msg)
        return from_parts(lower_scheme, netloc, self._path, self._query, self._fragment)

    def with_user(self, user: Union[str, None]) -> "URL":
        """Return a new URL with user replaced.

        Autoencode user if needed.

        Clear user/password if user is None.

        """
        # N.B. doesn't cleanup query/fragment
        if user is None:
            password = None
        elif isinstance(user, str):
            user = QUOTER(user)
            password = self.raw_password
        else:
            raise TypeError("Invalid user type")
        if not (netloc := self._netloc):
            raise ValueError("user replacement is not allowed for relative URLs")
        encoded_host = self.host_subcomponent or ""
        netloc = make_netloc(user, password, encoded_host, self.explicit_port)
        return from_parts(self._scheme, netloc, self._path, self._query, self._fragment)

    def with_password(self, password: Union[str, None]) -> "URL":
        """Return a new URL with password replaced.

        Autoencode password if needed.

        Clear password if argument is None.

        """
        # N.B. doesn't cleanup query/fragment
        if password is None:
            pass
        elif isinstance(password, str):
            password = QUOTER(password)
        else:
            raise TypeError("Invalid password type")
        if not (netloc := self._netloc):
            raise ValueError("password replacement is not allowed for relative URLs")
        encoded_host = self.host_subcomponent or ""
        port = self.explicit_port
        netloc = make_netloc(self.raw_user, password, encoded_host, port)
        return from_parts(self._scheme, netloc, self._path, self._query, self._fragment)

    def with_host(self, host: str) -> "URL":
        """Return a new URL with host replaced.

        Autoencode host if needed.

        Changing host for relative URLs is not allowed, use .join()
        instead.

        """
        # N.B. doesn't cleanup query/fragment
        if not isinstance(host, str):
            raise TypeError("Invalid host type")
        if not (netloc := self._netloc):
            raise ValueError("host replacement is not allowed for relative URLs")
        if not host:
            raise ValueError("host removing is not allowed")
        encoded_host = _encode_host(host, validate_host=True) if host else ""
        port = self.explicit_port
        netloc = make_netloc(self.raw_user, self.raw_password, encoded_host, port)
        return from_parts(self._scheme, netloc, self._path, self._query, self._fragment)

    def with_port(self, port: Union[int, None]) -> "URL":
        """Return a new URL with port replaced.

        Clear port to default if None is passed.

        """
        # N.B. doesn't cleanup query/fragment
        if port is not None:
            if isinstance(port, bool) or not isinstance(port, int):
                raise TypeError(f"port should be int or None, got {type(port)}")
            if not (0 <= port <= 65535):
                raise ValueError(f"port must be between 0 and 65535, got {port}")
        if not (netloc := self._netloc):
            raise ValueError("port replacement is not allowed for relative URLs")
        encoded_host = self.host_subcomponent or ""
        netloc = make_netloc(self.raw_user, self.raw_password, encoded_host, port)
        return from_parts(self._scheme, netloc, self._path, self._query, self._fragment)

    def with_path(
        self,
        path: str,
        *,
        encoded: bool = False,
        keep_query: bool = False,
        keep_fragment: bool = False,
    ) -> "URL":
        """Return a new URL with path replaced."""
        netloc = self._netloc
        if not encoded:
            path = PATH_QUOTER(path)
            if netloc:
                path = normalize_path(path) if "." in path else path
        if path and path[0] != "/":
            path = f"/{path}"
        query = self._query if keep_query else ""
        fragment = self._fragment if keep_fragment else ""
        return from_parts(self._scheme, netloc, path, query, fragment)

    @overload
    def with_query(self, query: Query) -> "URL": ...

    @overload
    def with_query(self, **kwargs: QueryVariable) -> "URL": ...

    def with_query(self, *args: Any, **kwargs: Any) -> "URL":
        """Return a new URL with query part replaced.

        Accepts any Mapping (e.g. dict, multidict.MultiDict instances)
        or str, autoencode the argument if needed.

        A sequence of (key, value) pairs is supported as well.

        It also can take an arbitrary number of keyword arguments.

        Clear query if None is passed.

        """
        # N.B. doesn't cleanup query/fragment
        query = get_str_query(*args, **kwargs) or ""
        return from_parts_uncached(
            self._scheme, self._netloc, self._path, query, self._fragment
        )

    @overload
    def extend_query(self, query: Query) -> "URL": ...

    @overload
    def extend_query(self, **kwargs: QueryVariable) -> "URL": ...

    def extend_query(self, *args: Any, **kwargs: Any) -> "URL":
        """Return a new URL with query part combined with the existing.

        This method will not remove existing query parameters.

        Example:
        >>> url = URL('http://example.com/?a=1&b=2')
        >>> url.extend_query(a=3, c=4)
        URL('http://example.com/?a=1&b=2&a=3&c=4')
        """
        if not (new_query := get_str_query(*args, **kwargs)):
            return self
        if query := self._query:
            # both strings are already encoded so we can use a simple
            # string join
            query += new_query if query[-1] == "&" else f"&{new_query}"
        else:
            query = new_query
        return from_parts_uncached(
            self._scheme, self._netloc, self._path, query, self._fragment
        )

    @overload
    def update_query(self, query: Query) -> "URL": ...

    @overload
    def update_query(self, **kwargs: QueryVariable) -> "URL": ...

    def update_query(self, *args: Any, **kwargs: Any) -> "URL":
        """Return a new URL with query part updated.

        This method will overwrite existing query parameters.

        Example:
        >>> url = URL('http://example.com/?a=1&b=2')
        >>> url.update_query(a=3, c=4)
        URL('http://example.com/?a=3&b=2&c=4')
        """
        in_query: Union[
            str,
            Mapping[str, QueryVariable],
            Sequence[tuple[Union[str, istr], SimpleQuery]],
            None,
        ]
        if kwargs:
            if args:
                msg = "Either kwargs or single query parameter must be present"
                raise ValueError(msg)
            in_query = kwargs
        elif len(args) == 1:
            in_query = args[0]
        else:
            raise ValueError("Either kwargs or single query parameter must be present")

        if in_query is None:
            query = ""
        elif not in_query:
            query = self._query
        elif isinstance(in_query, Mapping):
            qm: MultiDict[QueryVariable] = MultiDict(self._parsed_query)
            qm.update(in_query)
            query = get_str_query_from_sequence_iterable(qm.items())
        elif isinstance(in_query, str):
            qstr: MultiDict[str] = MultiDict(self._parsed_query)
            qstr.update(query_to_pairs(in_query))
            query = get_str_query_from_iterable(qstr.items())
        elif isinstance(in_query, (bytes, bytearray, memoryview)):
            msg = "Invalid query type: bytes, bytearray and memoryview are forbidden"
            raise TypeError(msg)
        elif isinstance(in_query, Sequence):
            # We don't expect sequence values if we're given a list of pairs
            # already; only mappings like builtin `dict` which can't have the
            # same key pointing to multiple values are allowed to use
            # `_query_seq_pairs`.
            if TYPE_CHECKING:
                in_query = cast(
                    Sequence[tuple[Union[str, istr], SimpleQuery]], in_query
                )
            qs: MultiDict[SimpleQuery] = MultiDict(self._parsed_query)
            qs.update(in_query)
            query = get_str_query_from_iterable(qs.items())
        else:
            raise TypeError(
                "Invalid query type: only str, mapping or "
                "sequence of (key, value) pairs is allowed"
            )
        return from_parts_uncached(
            self._scheme, self._netloc, self._path, query, self._fragment
        )

    def without_query_params(self, *query_params: str) -> "URL":
        """Remove some keys from query part and return new URL."""
        params_to_remove = set(query_params) & self.query.keys()
        if not params_to_remove:
            return self
        return self.with_query(
            tuple(
                (name, value)
                for name, value in self.query.items()
                if name not in params_to_remove
            )
        )

    def with_fragment(self, fragment: Union[str, None]) -> "URL":
        """Return a new URL with fragment replaced.

        Autoencode fragment if needed.

        Clear fragment to default if None is passed.

        """
        # N.B. doesn't cleanup query/fragment
        if fragment is None:
            raw_fragment = ""
        elif not isinstance(fragment, str):
            raise TypeError("Invalid fragment type")
        else:
            raw_fragment = FRAGMENT_QUOTER(fragment)
        if self._fragment == raw_fragment:
            return self
        return from_parts(
            self._scheme, self._netloc, self._path, self._query, raw_fragment
        )

    def with_name(
        self,
        name: str,
        *,
        keep_query: bool = False,
        keep_fragment: bool = False,
    ) -> "URL":
        """Return a new URL with name (last part of path) replaced.

        Query and fragment parts are cleaned up.

        Name is encoded if needed.

        """
        # N.B. DOES cleanup query/fragment
        if not isinstance(name, str):
            raise TypeError("Invalid name type")
        if "/" in name:
            raise ValueError("Slash in name is not allowed")
        name = PATH_QUOTER(name)
        if name in (".", ".."):
            raise ValueError(". and .. values are forbidden")
        parts = list(self.raw_parts)
        if netloc := self._netloc:
            if len(parts) == 1:
                parts.append(name)
            else:
                parts[-1] = name
            parts[0] = ""  # replace leading '/'
        else:
            parts[-1] = name
            if parts[0] == "/":
                parts[0] = ""  # replace leading '/'

        query = self._query if keep_query else ""
        fragment = self._fragment if keep_fragment else ""
        return from_parts(self._scheme, netloc, "/".join(parts), query, fragment)

    def with_suffix(
        self,
        suffix: str,
        *,
        keep_query: bool = False,
        keep_fragment: bool = False,
    ) -> "URL":
        """Return a new URL with suffix (file extension of name) replaced.

        Query and fragment parts are cleaned up.

        suffix is encoded if needed.
        """
        if not isinstance(suffix, str):
            raise TypeError("Invalid suffix type")
        if suffix and not suffix[0] == "." or suffix == "." or "/" in suffix:
            raise ValueError(f"Invalid suffix {suffix!r}")
        name = self.raw_name
        if not name:
            raise ValueError(f"{self!r} has an empty name")
        old_suffix = self.raw_suffix
        suffix = PATH_QUOTER(suffix)
        name = name + suffix if not old_suffix else name[: -len(old_suffix)] + suffix
        if name in (".", ".."):
            raise ValueError(". and .. values are forbidden")
        parts = list(self.raw_parts)
        if netloc := self._netloc:
            if len(parts) == 1:
                parts.append(name)
            else:
                parts[-1] = name
            parts[0] = ""  # replace leading '/'
        else:
            parts[-1] = name
            if parts[0] == "/":
                parts[0] = ""  # replace leading '/'

        query = self._query if keep_query else ""
        fragment = self._fragment if keep_fragment else ""
        return from_parts(self._scheme, netloc, "/".join(parts), query, fragment)

    def join(self, url: "URL") -> "URL":
        """Join URLs

        Construct a full (“absolute”) URL by combining a “base URL”
        (self) with another URL (url).

        Informally, this uses components of the base URL, in
        particular the addressing scheme, the network location and
        (part of) the path, to provide missing components in the
        relative URL.

        """
        if type(url) is not URL:
            raise TypeError("url should be URL")

        scheme = url._scheme or self._scheme
        if scheme != self._scheme or scheme not in USES_RELATIVE:
            return url

        # scheme is in uses_authority as uses_authority is a superset of uses_relative
        if (join_netloc := url._netloc) and scheme in USES_AUTHORITY:
            return from_parts(scheme, join_netloc, url._path, url._query, url._fragment)

        orig_path = self._path
        if join_path := url._path:
            if join_path[0] == "/":
                path = join_path
            elif not orig_path:
                path = f"/{join_path}"
            elif orig_path[-1] == "/":
                path = f"{orig_path}{join_path}"
            else:
                # …
                # and relativizing ".."
                # parts[0] is / for absolute urls,
                # this join will add a double slash there
                path = "/".join([*self.parts[:-1], ""]) + join_path
                # which has to be removed
                if orig_path[0] == "/":
                    path = path[1:]
            path = normalize_path(path) if "." in path else path
        else:
            path = orig_path

        return from_parts(
            scheme,
            self._netloc,
            path,
            url._query if join_path or url._query else self._query,
            url._fragment if join_path or url._fragment else self._fragment,
        )

    def joinpath(self, *other: str, encoded: bool = False) -> "URL":
        """Return a new URL with the elements in other appended to the path."""
        return self._make_child(other, encoded=encoded)

    def human_repr(self) -> str:
        """Return decoded human readable string for URL representation."""
        user = human_quote(self.user, "#/:?@[]")
        password = human_quote(self.password, "#/:?@[]")
        if (host := self.host) and ":" in host:
            host = f"[{host}]"
        path = human_quote(self.path, "#?")
        if TYPE_CHECKING:
            assert path is not None
        query_string = "&".join(
            "{}={}".format(human_quote(k, "#&+;="), human_quote(v, "#&+;="))
            for k, v in self.query.items()
        )
        fragment = human_quote(self.fragment, "")
        if TYPE_CHECKING:
            assert fragment is not None
        netloc = make_netloc(user, password, host, self.explicit_port)
        return unsplit_result(self._scheme, netloc, path, query_string, fragment)


_DEFAULT_IDNA_SIZE = 256
_DEFAULT_ENCODE_SIZE = 512


@lru_cache(_DEFAULT_IDNA_SIZE)
def _idna_decode(raw: str) -> str:
    try:
        return idna.decode(raw.encode("ascii"))
    except UnicodeError:  # e.g. '::1'
        return raw.encode("ascii").decode("idna")


@lru_cache(_DEFAULT_IDNA_SIZE)
def _idna_encode(host: str) -> str:
    try:
        return idna.encode(host, uts46=True).decode("ascii")
    except UnicodeError:
        return host.encode("idna").decode("ascii")


@lru_cache(_DEFAULT_ENCODE_SIZE)
def _encode_host(host: str, validate_host: bool) -> str:
    """Encode host part of URL."""
    # If the host ends with a digit or contains a colon, its likely
    # an IP address.
    if host and (host[-1].isdigit() or ":" in host):
        raw_ip, sep, zone = host.partition("%")
        # If it looks like an IP, we check with _ip_compressed_version
        # and fall-through if its not an IP address. This is a performance
        # optimization to avoid parsing IP addresses as much as possible
        # because it is orders of magnitude slower than almost any other
        # operation this library does.
        # Might be an IP address, check it
        #
        # IP Addresses can look like:
        # https://datatracker.ietf.org/doc/html/rfc3986#section-3.2.2
        # - 127.0.0.1 (last character is a digit)
        # - 2001:db8::ff00:42:8329 (contains a colon)
        # - 2001:db8::ff00:42:8329%eth0 (contains a colon)
        # - [2001:db8::ff00:42:8329] (contains a colon -- brackets should
        #                             have been removed before it gets here)
        # Rare IP Address formats are not supported per:
        # https://datatracker.ietf.org/doc/html/rfc3986#section-7.4
        #
        # IP parsing is slow, so its wrapped in an LRU
        try:
            ip = ip_address(raw_ip)
        except ValueError:
            pass
        else:
            # These checks should not happen in the
            # LRU to keep the cache size small
            host = ip.compressed
            if ip.version == 6:
                return f"[{host}%{zone}]" if sep else f"[{host}]"
            return f"{host}%{zone}" if sep else host

    # IDNA encoding is slow, skip it for ASCII-only strings
    if host.isascii():
        # Check for invalid characters explicitly; _idna_encode() does this
        # for non-ascii host names.
        host = host.lower()
        if validate_host and (invalid := NOT_REG_NAME.search(host)):
            value, pos, extra = invalid.group(), invalid.start(), ""
            if value == "@" or (value == ":" and "@" in host[pos:]):
                # this looks like an authority string
                extra = (
                    ", if the value includes a username or password, "
                    "use 'authority' instead of 'host'"
                )
            raise ValueError(
                f"Host {host!r} cannot contain {value!r} (at position {pos}){extra}"
            ) from None
        return host

    return _idna_encode(host)


@rewrite_module
def cache_clear() -> None:
    """Clear all LRU caches."""
    _idna_encode.cache_clear()
    _idna_decode.cache_clear()
    _encode_host.cache_clear()


@rewrite_module
def cache_info() -> CacheInfo:
    """Report cache statistics."""
    return {
        "idna_encode": _idna_encode.cache_info(),
        "idna_decode": _idna_decode.cache_info(),
        "ip_address": _encode_host.cache_info(),
        "host_validate": _encode_host.cache_info(),
        "encode_host": _encode_host.cache_info(),
    }


@rewrite_module
def cache_configure(
    *,
    idna_encode_size: Union[int, None] = _DEFAULT_IDNA_SIZE,
    idna_decode_size: Union[int, None] = _DEFAULT_IDNA_SIZE,
    ip_address_size: Union[int, None, UndefinedType] = UNDEFINED,
    host_validate_size: Union[int, None, UndefinedType] = UNDEFINED,
    encode_host_size: Union[int, None, UndefinedType] = UNDEFINED,
) -> None:
    """Configure LRU cache sizes."""
    global _idna_decode, _idna_encode, _encode_host
    # ip_address_size, host_validate_size are no longer
    # used, but are kept for backwards compatibility.
    if ip_address_size is not UNDEFINED or host_validate_size is not UNDEFINED:
        warnings.warn(
            "cache_configure() no longer accepts the "
            "ip_address_size or host_validate_size arguments, "
            "they are used to set the encode_host_size instead "
            "and will be removed in the future",
            DeprecationWarning,
            stacklevel=2,
        )

    if encode_host_size is not None:
        for size in (ip_address_size, host_validate_size):
            if size is None:
                encode_host_size = None
            elif encode_host_size is UNDEFINED:
                if size is not UNDEFINED:
                    encode_host_size = size
            elif size is not UNDEFINED:
                if TYPE_CHECKING:
                    assert isinstance(size, int)
                    assert isinstance(encode_host_size, int)
                encode_host_size = max(size, encode_host_size)
        if encode_host_size is UNDEFINED:
            encode_host_size = _DEFAULT_ENCODE_SIZE

    _encode_host = lru_cache(encode_host_size)(_encode_host.__wrapped__)
    _idna_decode = lru_cache(idna_decode_size)(_idna_decode.__wrapped__)
    _idna_encode = lru_cache(idna_encode_size)(_idna_encode.__wrapped__)
