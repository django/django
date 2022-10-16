import codecs
import copy
from io import BytesIO
from itertools import chain
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlsplit

from django.conf import settings
from django.core import signing
from django.core.exceptions import (
    DisallowedHost,
    ImproperlyConfigured,
    RequestDataTooBig,
    TooManyFieldsSent,
)
from django.core.files import uploadhandler
from django.http.multipartparser import MultiPartParser, MultiPartParserError
from django.utils.datastructures import (
    CaseInsensitiveMapping,
    ImmutableList,
    MultiValueDict,
)
from django.utils.encoding import escape_uri_path, iri_to_uri
from django.utils.functional import cached_property
from django.utils.http import is_same_domain, parse_header_parameters
from django.utils.regex_helper import _lazy_re_compile

RAISE_ERROR = object()
host_validation_re = _lazy_re_compile(
    r"^([a-z0-9.-]+|\[[a-f0-9]*:[a-f0-9\.:]+\])(:[0-9]+)?$"
)


class UnreadablePostError(OSError):
    pass


class RawPostDataException(Exception):
    """
    You cannot access raw_post_data from a request that has
    multipart/* POST data if it has been accessed via POST,
    FILES, etc..
    """

    pass


class HttpRequest:
    """A basic HTTP request."""

    # The encoding used in GET/POST dicts. None means use default setting.
    _encoding = None
    _upload_handlers = []

    non_picklable_attrs = frozenset(["resolver_match", "_stream"])

    def __init__(self):
        # WARNING: The `WSGIRequest` subclass doesn't call `super`.
        # Any variable assignment made here should also happen in
        # `WSGIRequest.__init__()`.

        self.GET = QueryDict(mutable=True)
        self.data = QueryDict(mutable=True)
        self.COOKIES = {}
        self.META = {}
        self.FILES = MultiValueDict()

        self.path = ""
        self.path_info = ""
        self.method = None
        self.resolver_match = None
        self.content_type = None
        self.content_params = None

    def __repr__(self):
        if self.method is None or not self.get_full_path():
            return "<%s>" % self.__class__.__name__
        return "<%s: %s %r>" % (
            self.__class__.__name__,
            self.method,
            self.get_full_path(),
        )

    def __getstate__(self):
        obj_dict = self.__dict__.copy()
        for attr in self.non_picklable_attrs:
            if attr in obj_dict:
                del obj_dict[attr]
        return obj_dict

    def __deepcopy__(self, memo):
        obj = copy.copy(self)
        for attr in self.non_picklable_attrs:
            if hasattr(self, attr):
                setattr(obj, attr, copy.deepcopy(getattr(self, attr), memo))
        memo[id(self)] = obj
        return obj

    @cached_property
    def headers(self):
        return HttpHeaders(self.META)

    @cached_property
    def accepted_types(self):
        """Return a list of MediaType instances."""
        return parse_accept_header(self.headers.get("Accept", "*/*"))

    def accepts(self, media_type):
        return any(
            accepted_type.match(media_type) for accepted_type in self.accepted_types
        )

    def _set_content_type_params(self, meta):
        """Set content_type, content_params, and encoding."""
        self.content_type, self.content_params = parse_header_parameters(
            meta.get("CONTENT_TYPE", "")
        )
        if "charset" in self.content_params:
            try:
                codecs.lookup(self.content_params["charset"])
            except LookupError:
                pass
            else:
                self.encoding = self.content_params["charset"]

    def _get_raw_host(self):
        """
        Return the HTTP host using the environment or request headers. Skip
        allowed hosts protection, so may return an insecure host.
        """
        # We try three options, in order of decreasing preference.
        if settings.USE_X_FORWARDED_HOST and ("HTTP_X_FORWARDED_HOST" in self.META):
            host = self.META["HTTP_X_FORWARDED_HOST"]
        elif "HTTP_HOST" in self.META:
            host = self.META["HTTP_HOST"]
        else:
            # Reconstruct the host using the algorithm from PEP 333.
            host = self.META["SERVER_NAME"]
            server_port = self.get_port()
            if server_port != ("443" if self.is_secure() else "80"):
                host = "%s:%s" % (host, server_port)
        return host

    def get_host(self):
        """Return the HTTP host using the environment or request headers."""
        host = self._get_raw_host()

        # Allow variants of localhost if ALLOWED_HOSTS is empty and DEBUG=True.
        allowed_hosts = settings.ALLOWED_HOSTS
        if settings.DEBUG and not allowed_hosts:
            allowed_hosts = [".localhost", "127.0.0.1", "[::1]"]

        domain, port = split_domain_port(host)
        if domain and validate_host(domain, allowed_hosts):
            return host
        else:
            msg = "Invalid HTTP_HOST header: %r." % host
            if domain:
                msg += " You may need to add %r to ALLOWED_HOSTS." % domain
            else:
                msg += (
                    " The domain name provided is not valid according to RFC 1034/1035."
                )
            raise DisallowedHost(msg)

    def get_port(self):
        """Return the port number for the request as a string."""
        if settings.USE_X_FORWARDED_PORT and "HTTP_X_FORWARDED_PORT" in self.META:
            port = self.META["HTTP_X_FORWARDED_PORT"]
        else:
            port = self.META["SERVER_PORT"]
        return str(port)

    def get_full_path(self, force_append_slash=False):
        return self._get_full_path(self.path, force_append_slash)

    def get_full_path_info(self, force_append_slash=False):
        return self._get_full_path(self.path_info, force_append_slash)

    def _get_full_path(self, path, force_append_slash):
        # RFC 3986 requires query string arguments to be in the ASCII range.
        # Rather than crash if this doesn't happen, we encode defensively.
        return "%s%s%s" % (
            escape_uri_path(path),
            "/" if force_append_slash and not path.endswith("/") else "",
            ("?" + iri_to_uri(self.META.get("QUERY_STRING", "")))
            if self.META.get("QUERY_STRING", "")
            else "",
        )

    def get_signed_cookie(self, key, default=RAISE_ERROR, salt="", max_age=None):
        """
        Attempt to return a signed cookie. If the signature fails or the
        cookie has expired, raise an exception, unless the `default` argument
        is provided,  in which case return that value.
        """
        try:
            cookie_value = self.COOKIES[key]
        except KeyError:
            if default is not RAISE_ERROR:
                return default
            else:
                raise
        try:
            value = signing.get_cookie_signer(salt=key + salt).unsign(
                cookie_value, max_age=max_age
            )
        except signing.BadSignature:
            if default is not RAISE_ERROR:
                return default
            else:
                raise
        return value

    def build_absolute_uri(self, location=None):
        """
        Build an absolute URI from the location and the variables available in
        this request. If no ``location`` is specified, build the absolute URI
        using request.get_full_path(). If the location is absolute, convert it
        to an RFC 3987 compliant URI and return it. If location is relative or
        is scheme-relative (i.e., ``//example.com/``), urljoin() it to a base
        URL constructed from the request variables.
        """
        if location is None:
            # Make it an absolute url (but schemeless and domainless) for the
            # edge case that the path starts with '//'.
            location = "//%s" % self.get_full_path()
        else:
            # Coerce lazy locations.
            location = str(location)
        bits = urlsplit(location)
        if not (bits.scheme and bits.netloc):
            # Handle the simple, most common case. If the location is absolute
            # and a scheme or host (netloc) isn't provided, skip an expensive
            # urljoin() as long as no path segments are '.' or '..'.
            if (
                bits.path.startswith("/")
                and not bits.scheme
                and not bits.netloc
                and "/./" not in bits.path
                and "/../" not in bits.path
            ):
                # If location starts with '//' but has no netloc, reuse the
                # schema and netloc from the current request. Strip the double
                # slashes and continue as if it wasn't specified.
                if location.startswith("//"):
                    location = location[2:]
                location = self._current_scheme_host + location
            else:
                # Join the constructed URL with the provided location, which
                # allows the provided location to apply query strings to the
                # base path.
                location = urljoin(self._current_scheme_host + self.path, location)
        return iri_to_uri(location)

    @cached_property
    def _current_scheme_host(self):
        return "{}://{}".format(self.scheme, self.get_host())

    def _get_scheme(self):
        """
        Hook for subclasses like WSGIRequest to implement. Return 'http' by
        default.
        """
        return "http"

    @property
    def scheme(self):
        if settings.SECURE_PROXY_SSL_HEADER:
            try:
                header, secure_value = settings.SECURE_PROXY_SSL_HEADER
            except ValueError:
                raise ImproperlyConfigured(
                    "The SECURE_PROXY_SSL_HEADER setting must be a tuple containing "
                    "two values."
                )
            header_value = self.META.get(header)
            if header_value is not None:
                header_value, *_ = header_value.split(",", 1)
                return "https" if header_value.strip() == secure_value else "http"
        return self._get_scheme()

    def is_secure(self):
        return self.scheme == "https"

    @property
    def encoding(self):
        return self._encoding

    @encoding.setter
    def encoding(self, val):
        """
        Set the encoding used for GET/POST accesses. If the GET or POST
        dictionary has already been created, remove and recreate it on the
        next access (so that it is decoded correctly).
        """
        self._encoding = val
        if hasattr(self, "GET"):
            del self.GET
        if hasattr(self, "_post"):
            del self._post

    def _initialize_handlers(self):
        self._upload_handlers = [
            uploadhandler.load_handler(handler, self)
            for handler in settings.FILE_UPLOAD_HANDLERS
        ]

    @property
    def upload_handlers(self):
        if not self._upload_handlers:
            # If there are no upload handlers defined, initialize them from settings.
            self._initialize_handlers()
        return self._upload_handlers

    @upload_handlers.setter
    def upload_handlers(self, upload_handlers):
        if hasattr(self, "_files"):
            raise AttributeError(
                "You cannot set the upload handlers after the upload has been "
                "processed."
            )
        self._upload_handlers = upload_handlers

    def parse_file_upload(self, META, post_data):
        """Return a tuple of (POST QueryDict, FILES MultiValueDict)."""
        self.upload_handlers = ImmutableList(
            self.upload_handlers,
            warning=(
                "You cannot alter upload handlers after the upload has been "
                "processed."
            ),
        )
        parser = MultiPartParser(META, post_data, self.upload_handlers, self.encoding)
        return parser.parse()

    @property
    def body(self):
        if not hasattr(self, "_body"):
            if self._read_started:
                raise RawPostDataException(
                    "You cannot access body after reading from request's data stream"
                )

            # Limit the maximum request data size that will be handled in-memory.
            if (
                settings.DATA_UPLOAD_MAX_MEMORY_SIZE is not None
                and int(self.META.get("CONTENT_LENGTH") or 0)
                > settings.DATA_UPLOAD_MAX_MEMORY_SIZE
            ):
                raise RequestDataTooBig(
                    "Request body exceeded settings.DATA_UPLOAD_MAX_MEMORY_SIZE."
                )

            try:
                self._body = self.read()
            except OSError as e:
                raise UnreadablePostError(*e.args) from e
            finally:
                self._stream.close()
            self._stream = BytesIO(self._body)
        return self._body

    def _mark_post_parse_error(self):
        self._post = QueryDict()
        self._files = MultiValueDict()

    def _load_post_and_files(self):
        """Populate self._post and self._files if the content-type is a form type"""
        if self._read_started and not hasattr(self, "_body"):
            self._mark_post_parse_error()
            return

        if self.content_type == "multipart/form-data":
            if hasattr(self, "_body"):
                # Use already read data
                data = BytesIO(self._body)
            else:
                data = self
            try:
                self._post, self._files = self.parse_file_upload(self.META, data)
            except MultiPartParserError:
                # An error occurred while parsing POST data. Since when
                # formatting the error the request handler might access
                # self.POST, set self._post and self._file to prevent
                # attempts to parse POST data again.
                self._mark_post_parse_error()
                raise
        elif self.content_type == "application/x-www-form-urlencoded":
            self._post, self._files = (
                QueryDict(self.body, encoding=self._encoding),
                MultiValueDict(),
            )
        else:
            self._post, self._files = (
                QueryDict(encoding=self._encoding),
                MultiValueDict(),
            )

    def close(self):
        if hasattr(self, "_files"):
            for f in chain.from_iterable(list_[1] for list_ in self._files.lists()):
                f.close()

    # File-like and iterator interface.
    #
    # Expects self._stream to be set to an appropriate source of bytes by
    # a corresponding request subclass (e.g. WSGIRequest).
    # Also when request data has already been read by request.POST or
    # request.body, self._stream points to a BytesIO instance
    # containing that data.

    def read(self, *args, **kwargs):
        self._read_started = True
        try:
            return self._stream.read(*args, **kwargs)
        except OSError as e:
            raise UnreadablePostError(*e.args) from e

    def readline(self, *args, **kwargs):
        self._read_started = True
        try:
            return self._stream.readline(*args, **kwargs)
        except OSError as e:
            raise UnreadablePostError(*e.args) from e

    def __iter__(self):
        return iter(self.readline, b"")

    def readlines(self):
        return list(self)

    def _get_post(self):
        # Not quite equivalent as files could still be accessed.
        # But NOT a covered behaviour.
        if self.method != "POST":
            return QueryDict(encoding=self._encoding)
        return self.data

    def _set_post(self, post):
        self.data = post

    POST = property(_get_post, _set_post)


class HttpHeaders(CaseInsensitiveMapping):
    HTTP_PREFIX = "HTTP_"
    # PEP 333 gives two headers which aren't prepended with HTTP_.
    UNPREFIXED_HEADERS = {"CONTENT_TYPE", "CONTENT_LENGTH"}

    def __init__(self, environ):
        headers = {}
        for header, value in environ.items():
            name = self.parse_header_name(header)
            if name:
                headers[name] = value
        super().__init__(headers)

    def __getitem__(self, key):
        """Allow header lookup using underscores in place of hyphens."""
        return super().__getitem__(key.replace("_", "-"))

    @classmethod
    def parse_header_name(cls, header):
        if header.startswith(cls.HTTP_PREFIX):
            header = header[len(cls.HTTP_PREFIX) :]
        elif header not in cls.UNPREFIXED_HEADERS:
            return None
        return header.replace("_", "-").title()

    @classmethod
    def to_wsgi_name(cls, header):
        header = header.replace("-", "_").upper()
        if header in cls.UNPREFIXED_HEADERS:
            return header
        return f"{cls.HTTP_PREFIX}{header}"

    @classmethod
    def to_asgi_name(cls, header):
        return header.replace("-", "_").upper()

    @classmethod
    def to_wsgi_names(cls, headers):
        return {
            cls.to_wsgi_name(header_name): value
            for header_name, value in headers.items()
        }

    @classmethod
    def to_asgi_names(cls, headers):
        return {
            cls.to_asgi_name(header_name): value
            for header_name, value in headers.items()
        }


class QueryDict(MultiValueDict):
    """
    A specialized MultiValueDict which represents a query string.

    A QueryDict can be used to represent GET or POST data. It subclasses
    MultiValueDict since keys in such data can be repeated, for instance
    in the data from a form with a <select multiple> field.

    By default QueryDicts are immutable, though the copy() method
    will always return a mutable copy.

    Both keys and values set on this class are converted from the given encoding
    (DEFAULT_CHARSET by default) to str.
    """

    # These are both reset in __init__, but is specified here at the class
    # level so that unpickling will have valid values
    _mutable = True
    _encoding = None

    def __init__(self, query_string=None, mutable=False, encoding=None):
        super().__init__()
        self.encoding = encoding or settings.DEFAULT_CHARSET
        query_string = query_string or ""
        parse_qsl_kwargs = {
            "keep_blank_values": True,
            "encoding": self.encoding,
            "max_num_fields": settings.DATA_UPLOAD_MAX_NUMBER_FIELDS,
        }
        if isinstance(query_string, bytes):
            # query_string normally contains URL-encoded data, a subset of ASCII.
            try:
                query_string = query_string.decode(self.encoding)
            except UnicodeDecodeError:
                # ... but some user agents are misbehaving :-(
                query_string = query_string.decode("iso-8859-1")
        try:
            for key, value in parse_qsl(query_string, **parse_qsl_kwargs):
                self.appendlist(key, value)
        except ValueError as e:
            # ValueError can also be raised if the strict_parsing argument to
            # parse_qsl() is True. As that is not used by Django, assume that
            # the exception was raised by exceeding the value of max_num_fields
            # instead of fragile checks of exception message strings.
            raise TooManyFieldsSent(
                "The number of GET/POST parameters exceeded "
                "settings.DATA_UPLOAD_MAX_NUMBER_FIELDS."
            ) from e
        self._mutable = mutable

    @classmethod
    def fromkeys(cls, iterable, value="", mutable=False, encoding=None):
        """
        Return a new QueryDict with keys (may be repeated) from an iterable and
        values from value.
        """
        q = cls("", mutable=True, encoding=encoding)
        for key in iterable:
            q.appendlist(key, value)
        if not mutable:
            q._mutable = False
        return q

    @property
    def encoding(self):
        if self._encoding is None:
            self._encoding = settings.DEFAULT_CHARSET
        return self._encoding

    @encoding.setter
    def encoding(self, value):
        self._encoding = value

    def _assert_mutable(self):
        if not self._mutable:
            raise AttributeError("This QueryDict instance is immutable")

    def __setitem__(self, key, value):
        self._assert_mutable()
        key = bytes_to_text(key, self.encoding)
        value = bytes_to_text(value, self.encoding)
        super().__setitem__(key, value)

    def __delitem__(self, key):
        self._assert_mutable()
        super().__delitem__(key)

    def __copy__(self):
        result = self.__class__("", mutable=True, encoding=self.encoding)
        for key, value in self.lists():
            result.setlist(key, value)
        return result

    def __deepcopy__(self, memo):
        result = self.__class__("", mutable=True, encoding=self.encoding)
        memo[id(self)] = result
        for key, value in self.lists():
            result.setlist(copy.deepcopy(key, memo), copy.deepcopy(value, memo))
        return result

    def setlist(self, key, list_):
        self._assert_mutable()
        key = bytes_to_text(key, self.encoding)
        list_ = [bytes_to_text(elt, self.encoding) for elt in list_]
        super().setlist(key, list_)

    def setlistdefault(self, key, default_list=None):
        self._assert_mutable()
        return super().setlistdefault(key, default_list)

    def appendlist(self, key, value):
        self._assert_mutable()
        key = bytes_to_text(key, self.encoding)
        value = bytes_to_text(value, self.encoding)
        super().appendlist(key, value)

    def pop(self, key, *args):
        self._assert_mutable()
        return super().pop(key, *args)

    def popitem(self):
        self._assert_mutable()
        return super().popitem()

    def clear(self):
        self._assert_mutable()
        super().clear()

    def setdefault(self, key, default=None):
        self._assert_mutable()
        key = bytes_to_text(key, self.encoding)
        default = bytes_to_text(default, self.encoding)
        return super().setdefault(key, default)

    def copy(self):
        """Return a mutable copy of this object."""
        return self.__deepcopy__({})

    def urlencode(self, safe=None):
        """
        Return an encoded string of all query string arguments.

        `safe` specifies characters which don't require quoting, for example::

            >>> q = QueryDict(mutable=True)
            >>> q['next'] = '/a&b/'
            >>> q.urlencode()
            'next=%2Fa%26b%2F'
            >>> q.urlencode(safe='/')
            'next=/a%26b/'
        """
        output = []
        if safe:
            safe = safe.encode(self.encoding)

            def encode(k, v):
                return "%s=%s" % ((quote(k, safe), quote(v, safe)))

        else:

            def encode(k, v):
                return urlencode({k: v})

        for k, list_ in self.lists():
            output.extend(
                encode(k.encode(self.encoding), str(v).encode(self.encoding))
                for v in list_
            )
        return "&".join(output)


class MediaType:
    def __init__(self, media_type_raw_line):
        full_type, self.params = parse_header_parameters(
            media_type_raw_line if media_type_raw_line else ""
        )
        self.main_type, _, self.sub_type = full_type.partition("/")

    def __str__(self):
        params_str = "".join("; %s=%s" % (k, v) for k, v in self.params.items())
        return "%s%s%s" % (
            self.main_type,
            ("/%s" % self.sub_type) if self.sub_type else "",
            params_str,
        )

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__qualname__, self)

    @property
    def is_all_types(self):
        return self.main_type == "*" and self.sub_type == "*"

    def match(self, other):
        if self.is_all_types:
            return True
        other = MediaType(other)
        if self.main_type == other.main_type and self.sub_type in {"*", other.sub_type}:
            return True
        return False


# It's neither necessary nor appropriate to use
# django.utils.encoding.force_str() for parsing URLs and form inputs. Thus,
# this slightly more restricted function, used by QueryDict.
def bytes_to_text(s, encoding):
    """
    Convert bytes objects to strings, using the given encoding. Illegally
    encoded input characters are replaced with Unicode "unknown" codepoint
    (\ufffd).

    Return any non-bytes objects without change.
    """
    if isinstance(s, bytes):
        return str(s, encoding, "replace")
    else:
        return s


def split_domain_port(host):
    """
    Return a (domain, port) tuple from a given host.

    Returned domain is lowercased. If the host is invalid, the domain will be
    empty.
    """
    host = host.lower()

    if not host_validation_re.match(host):
        return "", ""

    if host[-1] == "]":
        # It's an IPv6 address without a port.
        return host, ""
    bits = host.rsplit(":", 1)
    domain, port = bits if len(bits) == 2 else (bits[0], "")
    # Remove a trailing dot (if present) from the domain.
    domain = domain[:-1] if domain.endswith(".") else domain
    return domain, port


def validate_host(host, allowed_hosts):
    """
    Validate the given host for this site.

    Check that the host looks valid and matches a host or host pattern in the
    given list of ``allowed_hosts``. Any pattern beginning with a period
    matches a domain and all its subdomains (e.g. ``.example.com`` matches
    ``example.com`` and any subdomain), ``*`` matches anything, and anything
    else must match exactly.

    Note: This function assumes that the given host is lowercased and has
    already had the port, if any, stripped off.

    Return ``True`` for a valid host, ``False`` otherwise.
    """
    return any(
        pattern == "*" or is_same_domain(host, pattern) for pattern in allowed_hosts
    )


def parse_accept_header(header):
    return [MediaType(token) for token in header.split(",") if token.strip()]
