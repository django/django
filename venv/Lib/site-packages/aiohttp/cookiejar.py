import asyncio
import calendar
import contextlib
import datetime
import heapq
import itertools
import os  # noqa
import pathlib
import pickle
import re
import time
import warnings
from collections import defaultdict
from collections.abc import Mapping
from http.cookies import BaseCookie, Morsel, SimpleCookie
from typing import (
    DefaultDict,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

from yarl import URL

from ._cookie_helpers import preserve_morsel_with_coded_value
from .abc import AbstractCookieJar, ClearCookiePredicate
from .helpers import is_ip_address
from .typedefs import LooseCookies, PathLike, StrOrURL

__all__ = ("CookieJar", "DummyCookieJar")


CookieItem = Union[str, "Morsel[str]"]

# We cache these string methods here as their use is in performance critical code.
_FORMAT_PATH = "{}/{}".format
_FORMAT_DOMAIN_REVERSED = "{1}.{0}".format

# The minimum number of scheduled cookie expirations before we start cleaning up
# the expiration heap. This is a performance optimization to avoid cleaning up the
# heap too often when there are only a few scheduled expirations.
_MIN_SCHEDULED_COOKIE_EXPIRATION = 100
_SIMPLE_COOKIE = SimpleCookie()


class CookieJar(AbstractCookieJar):
    """Implements cookie storage adhering to RFC 6265."""

    DATE_TOKENS_RE = re.compile(
        r"[\x09\x20-\x2F\x3B-\x40\x5B-\x60\x7B-\x7E]*"
        r"(?P<token>[\x00-\x08\x0A-\x1F\d:a-zA-Z\x7F-\xFF]+)"
    )

    DATE_HMS_TIME_RE = re.compile(r"(\d{1,2}):(\d{1,2}):(\d{1,2})")

    DATE_DAY_OF_MONTH_RE = re.compile(r"(\d{1,2})")

    DATE_MONTH_RE = re.compile(
        "(jan)|(feb)|(mar)|(apr)|(may)|(jun)|(jul)|(aug)|(sep)|(oct)|(nov)|(dec)",
        re.I,
    )

    DATE_YEAR_RE = re.compile(r"(\d{2,4})")

    # calendar.timegm() fails for timestamps after datetime.datetime.max
    # Minus one as a loss of precision occurs when timestamp() is called.
    MAX_TIME = (
        int(datetime.datetime.max.replace(tzinfo=datetime.timezone.utc).timestamp()) - 1
    )
    try:
        calendar.timegm(time.gmtime(MAX_TIME))
    except (OSError, ValueError):
        # Hit the maximum representable time on Windows
        # https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/localtime-localtime32-localtime64
        # Throws ValueError on PyPy 3.9, OSError elsewhere
        MAX_TIME = calendar.timegm((3000, 12, 31, 23, 59, 59, -1, -1, -1))
    except OverflowError:
        # #4515: datetime.max may not be representable on 32-bit platforms
        MAX_TIME = 2**31 - 1
    # Avoid minuses in the future, 3x faster
    SUB_MAX_TIME = MAX_TIME - 1

    def __init__(
        self,
        *,
        unsafe: bool = False,
        quote_cookie: bool = True,
        treat_as_secure_origin: Union[StrOrURL, List[StrOrURL], None] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        super().__init__(loop=loop)
        self._cookies: DefaultDict[Tuple[str, str], SimpleCookie] = defaultdict(
            SimpleCookie
        )
        self._morsel_cache: DefaultDict[Tuple[str, str], Dict[str, Morsel[str]]] = (
            defaultdict(dict)
        )
        self._host_only_cookies: Set[Tuple[str, str]] = set()
        self._unsafe = unsafe
        self._quote_cookie = quote_cookie
        if treat_as_secure_origin is None:
            treat_as_secure_origin = []
        elif isinstance(treat_as_secure_origin, URL):
            treat_as_secure_origin = [treat_as_secure_origin.origin()]
        elif isinstance(treat_as_secure_origin, str):
            treat_as_secure_origin = [URL(treat_as_secure_origin).origin()]
        else:
            treat_as_secure_origin = [
                URL(url).origin() if isinstance(url, str) else url.origin()
                for url in treat_as_secure_origin
            ]
        self._treat_as_secure_origin = treat_as_secure_origin
        self._expire_heap: List[Tuple[float, Tuple[str, str, str]]] = []
        self._expirations: Dict[Tuple[str, str, str], float] = {}

    @property
    def quote_cookie(self) -> bool:
        return self._quote_cookie

    def save(self, file_path: PathLike) -> None:
        file_path = pathlib.Path(file_path)
        with file_path.open(mode="wb") as f:
            pickle.dump(self._cookies, f, pickle.HIGHEST_PROTOCOL)

    def load(self, file_path: PathLike) -> None:
        file_path = pathlib.Path(file_path)
        with file_path.open(mode="rb") as f:
            self._cookies = pickle.load(f)

    def clear(self, predicate: Optional[ClearCookiePredicate] = None) -> None:
        if predicate is None:
            self._expire_heap.clear()
            self._cookies.clear()
            self._morsel_cache.clear()
            self._host_only_cookies.clear()
            self._expirations.clear()
            return

        now = time.time()
        to_del = [
            key
            for (domain, path), cookie in self._cookies.items()
            for name, morsel in cookie.items()
            if (
                (key := (domain, path, name)) in self._expirations
                and self._expirations[key] <= now
            )
            or predicate(morsel)
        ]
        if to_del:
            self._delete_cookies(to_del)

    def clear_domain(self, domain: str) -> None:
        self.clear(lambda x: self._is_domain_match(domain, x["domain"]))

    def __iter__(self) -> "Iterator[Morsel[str]]":
        self._do_expiration()
        for val in self._cookies.values():
            yield from val.values()

    def __len__(self) -> int:
        """Return number of cookies.

        This function does not iterate self to avoid unnecessary expiration
        checks.
        """
        return sum(len(cookie.values()) for cookie in self._cookies.values())

    def _do_expiration(self) -> None:
        """Remove expired cookies."""
        if not (expire_heap_len := len(self._expire_heap)):
            return

        # If the expiration heap grows larger than the number expirations
        # times two, we clean it up to avoid keeping expired entries in
        # the heap and consuming memory. We guard this with a minimum
        # threshold to avoid cleaning up the heap too often when there are
        # only a few scheduled expirations.
        if (
            expire_heap_len > _MIN_SCHEDULED_COOKIE_EXPIRATION
            and expire_heap_len > len(self._expirations) * 2
        ):
            # Remove any expired entries from the expiration heap
            # that do not match the expiration time in the expirations
            # as it means the cookie has been re-added to the heap
            # with a different expiration time.
            self._expire_heap = [
                entry
                for entry in self._expire_heap
                if self._expirations.get(entry[1]) == entry[0]
            ]
            heapq.heapify(self._expire_heap)

        now = time.time()
        to_del: List[Tuple[str, str, str]] = []
        # Find any expired cookies and add them to the to-delete list
        while self._expire_heap:
            when, cookie_key = self._expire_heap[0]
            if when > now:
                break
            heapq.heappop(self._expire_heap)
            # Check if the cookie hasn't been re-added to the heap
            # with a different expiration time as it will be removed
            # later when it reaches the top of the heap and its
            # expiration time is met.
            if self._expirations.get(cookie_key) == when:
                to_del.append(cookie_key)

        if to_del:
            self._delete_cookies(to_del)

    def _delete_cookies(self, to_del: List[Tuple[str, str, str]]) -> None:
        for domain, path, name in to_del:
            self._host_only_cookies.discard((domain, name))
            self._cookies[(domain, path)].pop(name, None)
            self._morsel_cache[(domain, path)].pop(name, None)
            self._expirations.pop((domain, path, name), None)

    def _expire_cookie(self, when: float, domain: str, path: str, name: str) -> None:
        cookie_key = (domain, path, name)
        if self._expirations.get(cookie_key) == when:
            # Avoid adding duplicates to the heap
            return
        heapq.heappush(self._expire_heap, (when, cookie_key))
        self._expirations[cookie_key] = when

    def update_cookies(self, cookies: LooseCookies, response_url: URL = URL()) -> None:
        """Update cookies."""
        hostname = response_url.raw_host

        if not self._unsafe and is_ip_address(hostname):
            # Don't accept cookies from IPs
            return

        if isinstance(cookies, Mapping):
            cookies = cookies.items()

        for name, cookie in cookies:
            if not isinstance(cookie, Morsel):
                tmp = SimpleCookie()
                tmp[name] = cookie  # type: ignore[assignment]
                cookie = tmp[name]

            domain = cookie["domain"]

            # ignore domains with trailing dots
            if domain and domain[-1] == ".":
                domain = ""
                del cookie["domain"]

            if not domain and hostname is not None:
                # Set the cookie's domain to the response hostname
                # and set its host-only-flag
                self._host_only_cookies.add((hostname, name))
                domain = cookie["domain"] = hostname

            if domain and domain[0] == ".":
                # Remove leading dot
                domain = domain[1:]
                cookie["domain"] = domain

            if hostname and not self._is_domain_match(domain, hostname):
                # Setting cookies for different domains is not allowed
                continue

            path = cookie["path"]
            if not path or path[0] != "/":
                # Set the cookie's path to the response path
                path = response_url.path
                if not path.startswith("/"):
                    path = "/"
                else:
                    # Cut everything from the last slash to the end
                    path = "/" + path[1 : path.rfind("/")]
                cookie["path"] = path
            path = path.rstrip("/")

            if max_age := cookie["max-age"]:
                try:
                    delta_seconds = int(max_age)
                    max_age_expiration = min(time.time() + delta_seconds, self.MAX_TIME)
                    self._expire_cookie(max_age_expiration, domain, path, name)
                except ValueError:
                    cookie["max-age"] = ""

            elif expires := cookie["expires"]:
                if expire_time := self._parse_date(expires):
                    self._expire_cookie(expire_time, domain, path, name)
                else:
                    cookie["expires"] = ""

            key = (domain, path)
            if self._cookies[key].get(name) != cookie:
                # Don't blow away the cache if the same
                # cookie gets set again
                self._cookies[key][name] = cookie
                self._morsel_cache[key].pop(name, None)

        self._do_expiration()

    def filter_cookies(self, request_url: URL = URL()) -> "BaseCookie[str]":
        """Returns this jar's cookies filtered by their attributes."""
        # We always use BaseCookie now since all
        # cookies set on on filtered are fully constructed
        # Morsels, not just names and values.
        filtered: BaseCookie[str] = BaseCookie()
        if not self._cookies:
            # Skip do_expiration() if there are no cookies.
            return filtered
        self._do_expiration()
        if not self._cookies:
            # Skip rest of function if no non-expired cookies.
            return filtered
        if type(request_url) is not URL:
            warnings.warn(
                "filter_cookies expects yarl.URL instances only,"
                f"and will stop working in 4.x, got {type(request_url)}",
                DeprecationWarning,
                stacklevel=2,
            )
            request_url = URL(request_url)
        hostname = request_url.raw_host or ""

        is_not_secure = request_url.scheme not in ("https", "wss")
        if is_not_secure and self._treat_as_secure_origin:
            request_origin = URL()
            with contextlib.suppress(ValueError):
                request_origin = request_url.origin()
            is_not_secure = request_origin not in self._treat_as_secure_origin

        # Send shared cookie
        key = ("", "")
        for c in self._cookies[key].values():
            # Check cache first
            if c.key in self._morsel_cache[key]:
                filtered[c.key] = self._morsel_cache[key][c.key]
                continue

            # Build and cache the morsel
            mrsl_val = self._build_morsel(c)
            self._morsel_cache[key][c.key] = mrsl_val
            filtered[c.key] = mrsl_val

        if is_ip_address(hostname):
            if not self._unsafe:
                return filtered
            domains: Iterable[str] = (hostname,)
        else:
            # Get all the subdomains that might match a cookie (e.g. "foo.bar.com", "bar.com", "com")
            domains = itertools.accumulate(
                reversed(hostname.split(".")), _FORMAT_DOMAIN_REVERSED
            )

        # Get all the path prefixes that might match a cookie (e.g. "", "/foo", "/foo/bar")
        paths = itertools.accumulate(request_url.path.split("/"), _FORMAT_PATH)
        # Create every combination of (domain, path) pairs.
        pairs = itertools.product(domains, paths)

        path_len = len(request_url.path)
        # Point 2: https://www.rfc-editor.org/rfc/rfc6265.html#section-5.4
        for p in pairs:
            if p not in self._cookies:
                continue
            for name, cookie in self._cookies[p].items():
                domain = cookie["domain"]

                if (domain, name) in self._host_only_cookies and domain != hostname:
                    continue

                # Skip edge case when the cookie has a trailing slash but request doesn't.
                if len(cookie["path"]) > path_len:
                    continue

                if is_not_secure and cookie["secure"]:
                    continue

                # We already built the Morsel so reuse it here
                if name in self._morsel_cache[p]:
                    filtered[name] = self._morsel_cache[p][name]
                    continue

                # Build and cache the morsel
                mrsl_val = self._build_morsel(cookie)
                self._morsel_cache[p][name] = mrsl_val
                filtered[name] = mrsl_val

        return filtered

    def _build_morsel(self, cookie: Morsel[str]) -> Morsel[str]:
        """Build a morsel for sending, respecting quote_cookie setting."""
        if self._quote_cookie and cookie.coded_value and cookie.coded_value[0] == '"':
            return preserve_morsel_with_coded_value(cookie)
        morsel: Morsel[str] = Morsel()
        if self._quote_cookie:
            value, coded_value = _SIMPLE_COOKIE.value_encode(cookie.value)
        else:
            coded_value = value = cookie.value
        # We use __setstate__ instead of the public set() API because it allows us to
        # bypass validation and set already validated state. This is more stable than
        # setting protected attributes directly and unlikely to change since it would
        # break pickling.
        morsel.__setstate__({"key": cookie.key, "value": value, "coded_value": coded_value})  # type: ignore[attr-defined]
        return morsel

    @staticmethod
    def _is_domain_match(domain: str, hostname: str) -> bool:
        """Implements domain matching adhering to RFC 6265."""
        if hostname == domain:
            return True

        if not hostname.endswith(domain):
            return False

        non_matching = hostname[: -len(domain)]

        if not non_matching.endswith("."):
            return False

        return not is_ip_address(hostname)

    @classmethod
    def _parse_date(cls, date_str: str) -> Optional[int]:
        """Implements date string parsing adhering to RFC 6265."""
        if not date_str:
            return None

        found_time = False
        found_day = False
        found_month = False
        found_year = False

        hour = minute = second = 0
        day = 0
        month = 0
        year = 0

        for token_match in cls.DATE_TOKENS_RE.finditer(date_str):

            token = token_match.group("token")

            if not found_time:
                time_match = cls.DATE_HMS_TIME_RE.match(token)
                if time_match:
                    found_time = True
                    hour, minute, second = (int(s) for s in time_match.groups())
                    continue

            if not found_day:
                day_match = cls.DATE_DAY_OF_MONTH_RE.match(token)
                if day_match:
                    found_day = True
                    day = int(day_match.group())
                    continue

            if not found_month:
                month_match = cls.DATE_MONTH_RE.match(token)
                if month_match:
                    found_month = True
                    assert month_match.lastindex is not None
                    month = month_match.lastindex
                    continue

            if not found_year:
                year_match = cls.DATE_YEAR_RE.match(token)
                if year_match:
                    found_year = True
                    year = int(year_match.group())

        if 70 <= year <= 99:
            year += 1900
        elif 0 <= year <= 69:
            year += 2000

        if False in (found_day, found_month, found_year, found_time):
            return None

        if not 1 <= day <= 31:
            return None

        if year < 1601 or hour > 23 or minute > 59 or second > 59:
            return None

        return calendar.timegm((year, month, day, hour, minute, second, -1, -1, -1))


class DummyCookieJar(AbstractCookieJar):
    """Implements a dummy cookie storage.

    It can be used with the ClientSession when no cookie processing is needed.

    """

    def __init__(self, *, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        super().__init__(loop=loop)

    def __iter__(self) -> "Iterator[Morsel[str]]":
        while False:
            yield None

    def __len__(self) -> int:
        return 0

    @property
    def quote_cookie(self) -> bool:
        return True

    def clear(self, predicate: Optional[ClearCookiePredicate] = None) -> None:
        pass

    def clear_domain(self, domain: str) -> None:
        pass

    def update_cookies(self, cookies: LooseCookies, response_url: URL = URL()) -> None:
        pass

    def filter_cookies(self, request_url: URL) -> "BaseCookie[str]":
        return SimpleCookie()
