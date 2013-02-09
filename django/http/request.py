from __future__ import absolute_import, unicode_literals

import copy
import os
import re
import sys
import warnings
from io import BytesIO
from pprint import pformat
try:
    from urllib.parse import parse_qsl, urlencode, quote, urljoin
except ImportError:
    from urllib import urlencode, quote
    from urlparse import parse_qsl, urljoin

from django.conf import settings
from django.core import signing
from django.core.exceptions import SuspiciousOperation, ImproperlyConfigured
from django.core.files import uploadhandler
from django.http.multipartparser import MultiPartParser
from django.utils import six
from django.utils.datastructures import MultiValueDict, ImmutableList
from django.utils.encoding import force_bytes, force_text, force_str, iri_to_uri


RAISE_ERROR = object()
absolute_http_url_re = re.compile(r"^https?://", re.I)
host_validation_re = re.compile(r"^([a-z0-9.-]+|\[[a-f0-9]*:[a-f0-9:]+\])(:\d+)?$")


class UnreadablePostError(IOError):
    pass


class HttpRequest(object):
    """A basic HTTP request."""

    # The encoding used in GET/POST dicts. None means use default setting.
    _encoding = None
    _upload_handlers = []

    def __init__(self):
        self.GET, self.POST, self.COOKIES, self.META, self.FILES = {}, {}, {}, {}, {}
        self.path = ''
        self.path_info = ''
        self.method = None
        self._post_parse_error = False

    def __repr__(self):
        return build_request_repr(self)

    def get_host(self):
        """Returns the HTTP host using the environment or request headers."""
        # We try three options, in order of decreasing preference.
        if settings.USE_X_FORWARDED_HOST and (
            'HTTP_X_FORWARDED_HOST' in self.META):
            host = self.META['HTTP_X_FORWARDED_HOST']
        elif 'HTTP_HOST' in self.META:
            host = self.META['HTTP_HOST']
        else:
            # Reconstruct the host using the algorithm from PEP 333.
            host = self.META['SERVER_NAME']
            server_port = str(self.META['SERVER_PORT'])
            if server_port != ('443' if self.is_secure() else '80'):
                host = '%s:%s' % (host, server_port)

        allowed_hosts = ['*'] if settings.DEBUG else settings.ALLOWED_HOSTS
        if validate_host(host, allowed_hosts):
            return host
        else:
            raise SuspiciousOperation(
                "Invalid HTTP_HOST header (you may need to set ALLOWED_HOSTS): %s" % host)

    def get_full_path(self):
        # RFC 3986 requires query string arguments to be in the ASCII range.
        # Rather than crash if this doesn't happen, we encode defensively.
        return '%s%s' % (self.path, ('?' + iri_to_uri(self.META.get('QUERY_STRING', ''))) if self.META.get('QUERY_STRING', '') else '')

    def get_signed_cookie(self, key, default=RAISE_ERROR, salt='', max_age=None):
        """
        Attempts to return a signed cookie. If the signature fails or the
        cookie has expired, raises an exception... unless you provide the
        default argument in which case that value will be returned instead.
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
                cookie_value, max_age=max_age)
        except signing.BadSignature:
            if default is not RAISE_ERROR:
                return default
            else:
                raise
        return value

    def build_absolute_uri(self, location=None):
        """
        Builds an absolute URI from the location and the variables available in
        this request. If no location is specified, the absolute URI is built on
        ``request.get_full_path()``.
        """
        if not location:
            location = self.get_full_path()
        if not absolute_http_url_re.match(location):
            current_uri = '%s://%s%s' % ('https' if self.is_secure() else 'http',
                                         self.get_host(), self.path)
            location = urljoin(current_uri, location)
        return iri_to_uri(location)

    def _is_secure(self):
        return os.environ.get("HTTPS") == "on"

    def is_secure(self):
        # First, check the SECURE_PROXY_SSL_HEADER setting.
        if settings.SECURE_PROXY_SSL_HEADER:
            try:
                header, value = settings.SECURE_PROXY_SSL_HEADER
            except ValueError:
                raise ImproperlyConfigured('The SECURE_PROXY_SSL_HEADER setting must be a tuple containing two values.')
            if self.META.get(header, None) == value:
                return True

        # Failing that, fall back to _is_secure(), which is a hook for
        # subclasses to implement.
        return self._is_secure()

    def is_ajax(self):
        return self.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'

    @property
    def encoding(self):
        return self._encoding

    @encoding.setter
    def encoding(self, val):
        """
        Sets the encoding used for GET/POST accesses. If the GET or POST
        dictionary has already been created, it is removed and recreated on the
        next access (so that it is decoded correctly).
        """
        self._encoding = val
        if hasattr(self, '_get'):
            del self._get
        if hasattr(self, '_post'):
            del self._post

    def _initialize_handlers(self):
        self._upload_handlers = [uploadhandler.load_handler(handler, self)
                                 for handler in settings.FILE_UPLOAD_HANDLERS]

    @property
    def upload_handlers(self):
        if not self._upload_handlers:
            # If there are no upload handlers defined, initialize them from settings.
            self._initialize_handlers()
        return self._upload_handlers

    @upload_handlers.setter
    def upload_handlers(self, upload_handlers):
        if hasattr(self, '_files'):
            raise AttributeError("You cannot set the upload handlers after the upload has been processed.")
        self._upload_handlers = upload_handlers

    def parse_file_upload(self, META, post_data):
        """Returns a tuple of (POST QueryDict, FILES MultiValueDict)."""
        self.upload_handlers = ImmutableList(
            self.upload_handlers,
            warning="You cannot alter upload handlers after the upload has been processed."
        )
        parser = MultiPartParser(META, post_data, self.upload_handlers, self.encoding)
        return parser.parse()

    @property
    def body(self):
        if not hasattr(self, '_body'):
            if self._read_started:
                raise Exception("You cannot access body after reading from request's data stream")
            try:
                self._body = self.read()
            except IOError as e:
                six.reraise(UnreadablePostError, UnreadablePostError(*e.args), sys.exc_info()[2])
            self._stream = BytesIO(self._body)
        return self._body

    @property
    def raw_post_data(self):
        warnings.warn('HttpRequest.raw_post_data has been deprecated. Use HttpRequest.body instead.', DeprecationWarning)
        return self.body

    def _mark_post_parse_error(self):
        self._post = QueryDict('')
        self._files = MultiValueDict()
        self._post_parse_error = True

    def _load_post_and_files(self):
        """Populate self._post and self._files if the content-type is a form type"""
        if self.method != 'POST':
            self._post, self._files = QueryDict('', encoding=self._encoding), MultiValueDict()
            return
        if self._read_started and not hasattr(self, '_body'):
            self._mark_post_parse_error()
            return

        if self.META.get('CONTENT_TYPE', '').startswith('multipart/form-data'):
            if hasattr(self, '_body'):
                # Use already read data
                data = BytesIO(self._body)
            else:
                data = self
            try:
                self._post, self._files = self.parse_file_upload(self.META, data)
            except:
                # An error occured while parsing POST data. Since when
                # formatting the error the request handler might access
                # self.POST, set self._post and self._file to prevent
                # attempts to parse POST data again.
                # Mark that an error occured. This allows self.__repr__ to
                # be explicit about it instead of simply representing an
                # empty POST
                self._mark_post_parse_error()
                raise
        elif self.META.get('CONTENT_TYPE', '').startswith('application/x-www-form-urlencoded'):
            self._post, self._files = QueryDict(self.body, encoding=self._encoding), MultiValueDict()
        else:
            self._post, self._files = QueryDict('', encoding=self._encoding), MultiValueDict()

    ## File-like and iterator interface.
    ##
    ## Expects self._stream to be set to an appropriate source of bytes by
    ## a corresponding request subclass (e.g. WSGIRequest).
    ## Also when request data has already been read by request.POST or
    ## request.body, self._stream points to a BytesIO instance
    ## containing that data.

    def read(self, *args, **kwargs):
        self._read_started = True
        return self._stream.read(*args, **kwargs)

    def readline(self, *args, **kwargs):
        self._read_started = True
        return self._stream.readline(*args, **kwargs)

    def xreadlines(self):
        while True:
            buf = self.readline()
            if not buf:
                break
            yield buf

    __iter__ = xreadlines

    def readlines(self):
        return list(iter(self))


class QueryDict(MultiValueDict):
    """
    A specialized MultiValueDict that takes a query string when initialized.
    This is immutable unless you create a copy of it.

    Values retrieved from this class are converted from the given encoding
    (DEFAULT_CHARSET by default) to unicode.
    """
    # These are both reset in __init__, but is specified here at the class
    # level so that unpickling will have valid values
    _mutable = True
    _encoding = None

    def __init__(self, query_string, mutable=False, encoding=None):
        super(QueryDict, self).__init__()
        if not encoding:
            encoding = settings.DEFAULT_CHARSET
        self.encoding = encoding
        if six.PY3:
            if isinstance(query_string, bytes):
                # query_string contains URL-encoded data, a subset of ASCII.
                query_string = query_string.decode()
            for key, value in parse_qsl(query_string or '',
                                        keep_blank_values=True,
                                        encoding=encoding):
                self.appendlist(key, value)
        else:
            for key, value in parse_qsl(query_string or '',
                                        keep_blank_values=True):
                self.appendlist(force_text(key, encoding, errors='replace'),
                                force_text(value, encoding, errors='replace'))
        self._mutable = mutable

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
        super(QueryDict, self).__setitem__(key, value)

    def __delitem__(self, key):
        self._assert_mutable()
        super(QueryDict, self).__delitem__(key)

    def __copy__(self):
        result = self.__class__('', mutable=True, encoding=self.encoding)
        for key, value in six.iterlists(self):
            result.setlist(key, value)
        return result

    def __deepcopy__(self, memo):
        result = self.__class__('', mutable=True, encoding=self.encoding)
        memo[id(self)] = result
        for key, value in six.iterlists(self):
            result.setlist(copy.deepcopy(key, memo), copy.deepcopy(value, memo))
        return result

    def setlist(self, key, list_):
        self._assert_mutable()
        key = bytes_to_text(key, self.encoding)
        list_ = [bytes_to_text(elt, self.encoding) for elt in list_]
        super(QueryDict, self).setlist(key, list_)

    def setlistdefault(self, key, default_list=None):
        self._assert_mutable()
        return super(QueryDict, self).setlistdefault(key, default_list)

    def appendlist(self, key, value):
        self._assert_mutable()
        key = bytes_to_text(key, self.encoding)
        value = bytes_to_text(value, self.encoding)
        super(QueryDict, self).appendlist(key, value)

    def pop(self, key, *args):
        self._assert_mutable()
        return super(QueryDict, self).pop(key, *args)

    def popitem(self):
        self._assert_mutable()
        return super(QueryDict, self).popitem()

    def clear(self):
        self._assert_mutable()
        super(QueryDict, self).clear()

    def setdefault(self, key, default=None):
        self._assert_mutable()
        key = bytes_to_text(key, self.encoding)
        default = bytes_to_text(default, self.encoding)
        return super(QueryDict, self).setdefault(key, default)

    def copy(self):
        """Returns a mutable copy of this object."""
        return self.__deepcopy__({})

    def urlencode(self, safe=None):
        """
        Returns an encoded string of all query string arguments.

        :arg safe: Used to specify characters which do not require quoting, for
            example::

                >>> q = QueryDict('', mutable=True)
                >>> q['next'] = '/a&b/'
                >>> q.urlencode()
                'next=%2Fa%26b%2F'
                >>> q.urlencode(safe='/')
                'next=/a%26b/'

        """
        output = []
        if safe:
            safe = force_bytes(safe, self.encoding)
            encode = lambda k, v: '%s=%s' % ((quote(k, safe), quote(v, safe)))
        else:
            encode = lambda k, v: urlencode({k: v})
        for k, list_ in self.lists():
            k = force_bytes(k, self.encoding)
            output.extend([encode(k, force_bytes(v, self.encoding))
                           for v in list_])
        return '&'.join(output)


def build_request_repr(request, path_override=None, GET_override=None,
                       POST_override=None, COOKIES_override=None,
                       META_override=None):
    """
    Builds and returns the request's representation string. The request's
    attributes may be overridden by pre-processed values.
    """
    # Since this is called as part of error handling, we need to be very
    # robust against potentially malformed input.
    try:
        get = (pformat(GET_override)
               if GET_override is not None
               else pformat(request.GET))
    except Exception:
        get = '<could not parse>'
    if request._post_parse_error:
        post = '<could not parse>'
    else:
        try:
            post = (pformat(POST_override)
                    if POST_override is not None
                    else pformat(request.POST))
        except Exception:
            post = '<could not parse>'
    try:
        cookies = (pformat(COOKIES_override)
                   if COOKIES_override is not None
                   else pformat(request.COOKIES))
    except Exception:
        cookies = '<could not parse>'
    try:
        meta = (pformat(META_override)
                if META_override is not None
                else pformat(request.META))
    except Exception:
        meta = '<could not parse>'
    path = path_override if path_override is not None else request.path
    return force_str('<%s\npath:%s,\nGET:%s,\nPOST:%s,\nCOOKIES:%s,\nMETA:%s>' %
                     (request.__class__.__name__,
                      path,
                      six.text_type(get),
                      six.text_type(post),
                      six.text_type(cookies),
                      six.text_type(meta)))


# It's neither necessary nor appropriate to use
# django.utils.encoding.smart_text for parsing URLs and form inputs. Thus,
# this slightly more restricted function, used by QueryDict.
def bytes_to_text(s, encoding):
    """
    Converts basestring objects to unicode, using the given encoding. Illegally
    encoded input characters are replaced with Unicode "unknown" codepoint
    (\ufffd).

    Returns any non-basestring objects without change.
    """
    if isinstance(s, bytes):
        return six.text_type(s, encoding, 'replace')
    else:
        return s


def validate_host(host, allowed_hosts):
    """
    Validate the given host header value for this site.

    Check that the host looks valid and matches a host or host pattern in the
    given list of ``allowed_hosts``. Any pattern beginning with a period
    matches a domain and all its subdomains (e.g. ``.example.com`` matches
    ``example.com`` and any subdomain), ``*`` matches anything, and anything
    else must match exactly.

    Return ``True`` for a valid host, ``False`` otherwise.

    """
    # All validation is case-insensitive
    host = host.lower()

    # Basic sanity check
    if not host_validation_re.match(host):
        return False

    # Validate only the domain part.
    if host[-1] == ']':
        # It's an IPv6 address without a port.
        domain = host
    else:
        domain = host.rsplit(':', 1)[0]

    for pattern in allowed_hosts:
        pattern = pattern.lower()
        match = (
            pattern == '*' or
            pattern.startswith('.') and (
                domain.endswith(pattern) or domain == pattern[1:]
                ) or
            pattern == domain
            )
        if match:
            return True

    return False
