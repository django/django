import codecs
import copy
import operator
import re
from io import BytesIO
from itertools import chain
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlsplit

from django.conf import settings
from django.core import signing
from django.core.exceptions import (
    BadRequest,
    DisallowedHost,
    ImproperlyConfigured,
    RequestDataTooBig,
    TooManyFieldsSent,
    TooManyFilesSent,
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

RAISE_ERROR = object()
host_validation_re = re.compile(
    r"^([a-z0-9.-]+|\[[a-f0-9]*:[a-f0-9\.:]+\])(?::([0-9]+))?$"
)


class ParsedHostHeader:
    __slots__ = ("domain", "port", "combined")

    def __init__(self, domain, port, combined):
        self.domain = domain
        self.port = port
        self.combined = combined


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

    def __init__(self):
        # WARNING: The `WSGIRequest` subclass doesn't call `super`.
        # Any variable assignment made here should also happen in
        # `WSGIRequest.__init__()`.

        self.GET = QueryDict(mutable=True)
        self.POST = QueryDict(mutable=True)
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

    @cached_property
    def headers(self):
        return HttpHeaders(self.META)

    @cached_property
    def accepted_types(self):
        """Return a list of MediaType instances, in order of preference (quality)."""
        header_value = self.headers.get("Accept", "*/*")
        return sorted(
            (
                media_type
                for token in header_value.split(",")
                if token.strip() and (media_type := MediaType(token)).quality != 0
            ),
            key=operator.attrgetter("quality", "specificity"),
            reverse=True,
        )

    @cached_property
    def accepted_types_by_precedence(self):
        """
        Return a list of MediaType instances, in order of precedence (specificity).
        """
        return sorted(
            self.accepted_types,
            key=operator.attrgetter("specificity", "quality"),
            reverse=True,
        )

    def accepted_type(self, media_type):
        """
        Return the MediaType instance which best matches the given media type.
        """
        media_type = MediaType(media_type)
        return next(
            (
                accepted_type
                for accepted_type in self.accepted_types_by_precedence
                if media_type.match(accepted_type)
            ),
            None,
        )

    def get_preferred_type(self, media_types):
        """Select the preferred media type from the provided options."""
        if not media_types or not self.accepted_types:
            return None

        desired_types = [
            (accepted_type, media_type)
            for media_type in media_types
            if (accepted_type := self.accepted_type(media_type)) is not None
        ]

        if not desired_types:
            return None

        # Of the desired media types, select the one which is preferred.
        return min(desired_types, key=lambda t: self.accepted_types.index(t[0]))[1]

    def accepts(self, media_type):
        """Does the client accept a response in the given media type?"""
        return self.accepted_type(media_type) is not None

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

    def _get_parsed_host_header(self, validate=True):
        if not hasattr(self, "_parsed_host_obj"):
            use_x_fw_host = settings.USE_X_FORWARDED_HOST
            use_x_fw_port = settings.USE_X_FORWARDED_PORT

            port_in_x_fw_host = False
            default_port = "443" if self.is_secure() else "80"

            if use_x_fw_host and "HTTP_X_FORWARDED_HOST" in self.META:
                host, port = _parse_host_header(self.META["HTTP_X_FORWARDED_HOST"])
                port_in_x_fw_host = port != ""
            elif "HTTP_HOST" in self.META:
                host, port = _parse_host_header(self.META["HTTP_HOST"])
            else:
                # Reconstruct the host using the algorithm from PEP 333.
                host, port = self.META["SERVER_NAME"], str(self.META["SERVER_PORT"])
                if port == default_port:
                    port = ""

            if use_x_fw_port and "HTTP_X_FORWARDED_PORT" in self.META:
                if port_in_x_fw_host:
                    raise DisallowedHost(
                        "HTTP_X_FORWARDED_HOST contains a port number "
                        "and USE_X_FORWARDED_PORT is set to True"
                    )
                port = self.META["HTTP_X_FORWARDED_PORT"]

            reconstructed = "%s:%s" % (host, port) if port else host

            domain, port = split_domain_port(reconstructed)
            parsed_host = self._parsed_host_obj = ParsedHostHeader(
                domain, port or default_port, reconstructed
            )
        else:
            parsed_host = self._parsed_host_obj

        # Allow variants of localhost if ALLOWED_HOSTS is empty and DEBUG=True.
        allowed_hosts = settings.ALLOWED_HOSTS
        if settings.DEBUG and not allowed_hosts:
            allowed_hosts = [".localhost", "127.0.0.1", "[::1]"]

        msg = "Invalid HTTP_HOST header: %r." % parsed_host.combined
        if validate and not (
            parsed_host.domain and validate_host(parsed_host.domain, allowed_hosts)
        ):
            if parsed_host.domain:
                msg += " You may need to add %r to ALLOWED_HOSTS." % parsed_host.domain
            else:
                msg += (
                    " The domain name provided is not valid according to RFC 1034/1035."
                )
            raise DisallowedHost(msg)

        if validate and not validate_port(parsed_host.port):
            raise DisallowedHost("The port provided is not valid")

        return parsed_host

    def get_host(self):
        """Return the HTTP host using the environment or request headers."""
        return self._get_parsed_host_header().combined

    def get_port(self):
        """Return the port number for the request as a string."""
        return self._get_parsed_host_header().port

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
            (
                ("?" + iri_to_uri(self.META.get("QUERY_STRING", "")))
                if self.META.get("QUERY_STRING", "")
                else ""
            ),
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

    def get_raw_uri(self):
        """
        Return an absolute URI from variables available in this request. Skip
        allowed hosts protection, so may return insecure URI.
        """
        return (
            f"{self.scheme}://"
            f"{self._get_parsed_host_header(validate=False).combined}"
            f"{self.get_full_path()}"
        )

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
                location = self._current_scheme_host + location.removeprefix("//")
            else:
                # Join the constructed URL with the provided location, which
                # allows the provided location to apply query strings to the
                # base path.
                location = urljoin(self._current_scheme_host + self.path, location)
        return iri_to_uri(location)

    @cached_property
    def _current_scheme_host(self):
        return f"{self.scheme}://{self.get_host()}"

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
        if self.method != "POST":
            self._post, self._files = (
                QueryDict(encoding=self._encoding),
                MultiValueDict(),
            )
            return
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
            except (MultiPartParserError, TooManyFilesSent):
                # An error occurred while parsing POST data. Since when
                # formatting the error the request handler might access
                # self.POST, set self._post and self._file to prevent
                # attempts to parse POST data again.
                self._mark_post_parse_error()
                raise
        elif self.content_type == "application/x-www-form-urlencoded":
            # According to RFC 1866, the "application/x-www-form-urlencoded"
            # content type does not have a charset and should be always treated
            # as UTF-8.
            if self._encoding is not None and self._encoding.lower() != "utf-8":
                raise BadRequest(
                    "HTTP requests with the 'application/x-www-form-urlencoded' "
                    "content type must be UTF-8 encoded."
                )
            self._post = QueryDict(self.body, encoding="utf-8")
            self._files = MultiValueDict()
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
            header = header.removeprefix(cls.HTTP_PREFIX)
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

    @cached_property
    def range_params(self):
        params = self.params.copy()
        params.pop("q", None)
        return params

    def match(self, other):
        if not other:
            return False

        if not isinstance(other, MediaType):
            other = MediaType(other)

        main_types = [self.main_type, other.main_type]
        sub_types = [self.sub_type, other.sub_type]

        # Main types and sub types must be defined.
        if not all((*main_types, *sub_types)):
            return False

        # Main types must match or one be "*", same for sub types.
        for this_type, other_type in (main_types, sub_types):
            if this_type != other_type and this_type != "*" and other_type != "*":
                return False

        if bool(self.range_params) == bool(other.range_params):
            # If both have params or neither have params, they must be identical.
            result = self.range_params == other.range_params
        else:
            # If self has params and other does not, it's a match.
            # If other has params and self does not, don't match.
            result = bool(self.range_params or not other.range_params)
        return result

    @cached_property
    def quality(self):
        try:
            quality = float(self.params.get("q", 1))
        except ValueError:
            # Discard invalid values.
            return 1

        # Valid quality values must be between 0 and 1.
        if quality < 0 or quality > 1:
            return 1

        return round(quality, 3)

    @property
    def specificity(self):
        """
        Return a value from 0-3 for how specific the media type is.
        """
        if self.main_type == "*":
            return 0
        elif self.sub_type == "*":
            return 1
        elif not self.range_params:
            return 2
        return 3


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


def _parse_host_header(host_header):
    """
    Returns a (domain, port) tuple for a given host.

    Neither domain name nor port are validated.
    """

    if host_header[-1] == "]":
        # It's an IPv6 address without a port.
        return host_header, ""
    bits = host_header.rsplit(":", 1)
    return tuple(bits) if len(bits) == 2 else (bits[0], "")


def split_domain_port(host):
    """
    Return a (domain, port) tuple from a given host.

    Returned domain is lowercased. If the host is invalid, the domain will be
    empty.
    """
    host = host.lower()

    host_match = re.match(host_validation_re, host)
    if not host_match:
        return "", ""

    domain, port = host_match.groups()
    port = port or ""
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


def validate_port(port):
    """
    Validate the given port for this site.

    Checks that the port is a number and that it's between 1 and 65535.

    Note: This function doesn't instantly return Falseif the port contains
    leading zeros.

    Return ``True`` for a valid port, ``False`` otherwise.
    """
    return port.isdigit() and 1 <= int(port) <= 65535
