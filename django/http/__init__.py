from __future__ import absolute_import, unicode_literals

import copy
import datetime
from email.header import Header
import os
import re
import sys
import time
import warnings

from io import BytesIO
from pprint import pformat
try:
    from urllib.parse import quote, parse_qsl, urlencode, urljoin, urlparse
except ImportError:     # Python 2
    from urllib import quote, urlencode
    from urlparse import parse_qsl, urljoin, urlparse

from django.utils.six.moves import http_cookies
# Some versions of Python 2.7 and later won't need this encoding bug fix:
_cookie_encodes_correctly = http_cookies.SimpleCookie().value_encode(';') == (';', '"\\073"')
# See ticket #13007, http://bugs.python.org/issue2193 and http://trac.edgewall.org/ticket/2256
_tc = http_cookies.SimpleCookie()
try:
    _tc.load(str('foo:bar=1'))
    _cookie_allows_colon_in_names = True
except http_cookies.CookieError:
    _cookie_allows_colon_in_names = False

if _cookie_encodes_correctly and _cookie_allows_colon_in_names:
    SimpleCookie = http_cookies.SimpleCookie
else:
    Morsel = http_cookies.Morsel

    class SimpleCookie(http_cookies.SimpleCookie):
        if not _cookie_encodes_correctly:
            def value_encode(self, val):
                # Some browsers do not support quoted-string from RFC 2109,
                # including some versions of Safari and Internet Explorer.
                # These browsers split on ';', and some versions of Safari
                # are known to split on ', '. Therefore, we encode ';' and ','

                # SimpleCookie already does the hard work of encoding and decoding.
                # It uses octal sequences like '\\012' for newline etc.
                # and non-ASCII chars. We just make use of this mechanism, to
                # avoid introducing two encoding schemes which would be confusing
                # and especially awkward for javascript.

                # NB, contrary to Python docs, value_encode returns a tuple containing
                # (real val, encoded_val)
                val, encoded = super(SimpleCookie, self).value_encode(val)

                encoded = encoded.replace(";", "\\073").replace(",","\\054")
                # If encoded now contains any quoted chars, we need double quotes
                # around the whole string.
                if "\\" in encoded and not encoded.startswith('"'):
                    encoded = '"' + encoded + '"'

                return val, encoded

        if not _cookie_allows_colon_in_names:
            def load(self, rawdata):
                self.bad_cookies = set()
                super(SimpleCookie, self).load(force_str(rawdata))
                for key in self.bad_cookies:
                    del self[key]

            # override private __set() method:
            # (needed for using our Morsel, and for laxness with CookieError
            def _BaseCookie__set(self, key, real_value, coded_value):
                key = force_str(key)
                try:
                    M = self.get(key, Morsel())
                    M.set(key, real_value, coded_value)
                    dict.__setitem__(self, key, M)
                except http_cookies.CookieError:
                    self.bad_cookies.add(key)
                    dict.__setitem__(self, key, http_cookies.Morsel())


from django.conf import settings
from django.core import signing
from django.core.exceptions import ImproperlyConfigured, SuspiciousOperation
from django.core.files import uploadhandler
from django.http.multipartparser import MultiPartParser
from django.http.utils import *
from django.utils.datastructures import MultiValueDict, ImmutableList
from django.utils.encoding import force_bytes, force_str, force_text, iri_to_uri
from django.utils.http import cookie_date
from django.utils import six
from django.utils import timezone

RESERVED_CHARS="!*'();:@&=+$,/?%#[]"

absolute_http_url_re = re.compile(r"^https?://", re.I)

class Http404(Exception):
    pass

RAISE_ERROR = object()


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

        # Disallow potentially poisoned hostnames.
        if set(';/?@&=+$,').intersection(host):
            raise SuspiciousOperation('Invalid HTTP_HOST header: %s' % host)

        return host

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
        # Populates self._post and self._files
        if self.method != 'POST':
            self._post, self._files = QueryDict('', encoding=self._encoding), MultiValueDict()
            return
        if self._read_started and not hasattr(self, '_body'):
            self._mark_post_parse_error()
            return

        if self.META.get('CONTENT_TYPE', '').startswith('multipart'):
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
        else:
            self._post, self._files = QueryDict(self.body, encoding=self._encoding), MultiValueDict()

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


def parse_cookie(cookie):
    if cookie == '':
        return {}
    if not isinstance(cookie, http_cookies.BaseCookie):
        try:
            c = SimpleCookie()
            c.load(cookie)
        except http_cookies.CookieError:
            # Invalid cookie
            return {}
    else:
        c = cookie
    cookiedict = {}
    for key in c.keys():
        cookiedict[key] = c.get(key).value
    return cookiedict

class BadHeaderError(ValueError):
    pass

class HttpResponse(object):
    """A basic HTTP response, with content and dictionary-accessed headers."""

    status_code = 200

    def __init__(self, content='', content_type=None, status=None,
            mimetype=None):
        # _headers is a mapping of the lower-case name to the original case of
        # the header (required for working with legacy systems) and the header
        # value. Both the name of the header and its value are ASCII strings.
        self._headers = {}
        self._charset = settings.DEFAULT_CHARSET
        if mimetype:
            warnings.warn("Using mimetype keyword argument is deprecated, use"
                          " content_type instead", PendingDeprecationWarning)
            content_type = mimetype
        if not content_type:
            content_type = "%s; charset=%s" % (settings.DEFAULT_CONTENT_TYPE,
                    self._charset)
        # content is a bytestring. See the content property methods.
        self.content = content
        self.cookies = SimpleCookie()
        if status:
            self.status_code = status

        self['Content-Type'] = content_type

    def serialize(self):
        """Full HTTP message, including headers, as a bytestring."""
        headers = [
            ('%s: %s' % (key, value)).encode('us-ascii')
            for key, value in self._headers.values()
        ]
        return b'\r\n'.join(headers) + b'\r\n\r\n' + self.content

    if six.PY3:
        __bytes__ = serialize
    else:
        __str__ = serialize

    def _convert_to_charset(self, value, charset, mime_encode=False):
        """Converts headers key/value to ascii/latin1 native strings.

        `charset` must be 'ascii' or 'latin-1'. If `mime_encode` is True and
        `value` value can't be represented in the given charset, MIME-encoding
        is applied.
        """
        if not isinstance(value, (bytes, six.text_type)):
            value = str(value)
        try:
            if six.PY3:
                if isinstance(value, str):
                    # Ensure string is valid in given charset
                    value.encode(charset)
                else:
                    # Convert bytestring using given charset
                    value = value.decode(charset)
            else:
                if isinstance(value, str):
                    # Ensure string is valid in given charset
                    value.decode(charset)
                else:
                    # Convert unicode string to given charset
                    value = value.encode(charset)
        except UnicodeError as e:
            if mime_encode:
                # Wrapping in str() is a workaround for #12422 under Python 2.
                value = str(Header(value, 'utf-8').encode())
            else:
                e.reason += ', HTTP response headers must be in %s format' % charset
                raise
        if str('\n') in value or str('\r') in value:
            raise BadHeaderError("Header values can't contain newlines (got %r)" % value)
        return value

    def __setitem__(self, header, value):
        header = self._convert_to_charset(header, 'ascii')
        value = self._convert_to_charset(value, 'latin1', mime_encode=True)
        self._headers[header.lower()] = (header, value)

    def __delitem__(self, header):
        try:
            del self._headers[header.lower()]
        except KeyError:
            pass

    def __getitem__(self, header):
        return self._headers[header.lower()][1]

    def __getstate__(self):
        # SimpleCookie is not pickeable with pickle.HIGHEST_PROTOCOL, so we
        # serialise to a string instead
        state = self.__dict__.copy()
        state['cookies'] = str(state['cookies'])
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.cookies = SimpleCookie(self.cookies)

    def has_header(self, header):
        """Case-insensitive check for a header."""
        return header.lower() in self._headers

    __contains__ = has_header

    def items(self):
        return self._headers.values()

    def get(self, header, alternate=None):
        return self._headers.get(header.lower(), (None, alternate))[1]

    def set_cookie(self, key, value='', max_age=None, expires=None, path='/',
                   domain=None, secure=False, httponly=False):
        """
        Sets a cookie.

        ``expires`` can be:
        - a string in the correct format,
        - a naive ``datetime.datetime`` object in UTC,
        - an aware ``datetime.datetime`` object in any time zone.
        If it is a ``datetime.datetime`` object then ``max_age`` will be calculated.

        """
        self.cookies[key] = value
        if expires is not None:
            if isinstance(expires, datetime.datetime):
                if timezone.is_aware(expires):
                    expires = timezone.make_naive(expires, timezone.utc)
                delta = expires - expires.utcnow()
                # Add one second so the date matches exactly (a fraction of
                # time gets lost between converting to a timedelta and
                # then the date string).
                delta = delta + datetime.timedelta(seconds=1)
                # Just set max_age - the max_age logic will set expires.
                expires = None
                max_age = max(0, delta.days * 86400 + delta.seconds)
            else:
                self.cookies[key]['expires'] = expires
        if max_age is not None:
            self.cookies[key]['max-age'] = max_age
            # IE requires expires, so set it if hasn't been already.
            if not expires:
                self.cookies[key]['expires'] = cookie_date(time.time() +
                                                           max_age)
        if path is not None:
            self.cookies[key]['path'] = path
        if domain is not None:
            self.cookies[key]['domain'] = domain
        if secure:
            self.cookies[key]['secure'] = True
        if httponly:
            self.cookies[key]['httponly'] = True

    def set_signed_cookie(self, key, value, salt='', **kwargs):
        value = signing.get_cookie_signer(salt=key + salt).sign(value)
        return self.set_cookie(key, value, **kwargs)

    def delete_cookie(self, key, path='/', domain=None):
        self.set_cookie(key, max_age=0, path=path, domain=domain,
                        expires='Thu, 01-Jan-1970 00:00:00 GMT')

    @property
    def content(self):
        if self.has_header('Content-Encoding'):
            def make_bytes(value):
                if isinstance(value, int):
                    value = six.text_type(value)
                if isinstance(value, six.text_type):
                    value = value.encode('ascii')
                # force conversion to bytes in case chunk is a subclass
                return bytes(value)
            return b''.join(make_bytes(e) for e in self._container)
        return b''.join(force_bytes(e, self._charset) for e in self._container)

    @content.setter
    def content(self, value):
        if hasattr(value, '__iter__') and not isinstance(value, (bytes, six.string_types)):
            self._container = value
            self._base_content_is_iter = True
        else:
            self._container = [value]
            self._base_content_is_iter = False

    def __iter__(self):
        self._iterator = iter(self._container)
        return self

    def __next__(self):
        chunk = next(self._iterator)
        if isinstance(chunk, int):
            chunk = six.text_type(chunk)
        if isinstance(chunk, six.text_type):
            chunk = chunk.encode(self._charset)
        # force conversion to bytes in case chunk is a subclass
        return bytes(chunk)

    next = __next__             # Python 2 compatibility

    def close(self):
        if hasattr(self._container, 'close'):
            self._container.close()

    # The remaining methods partially implement the file-like object interface.
    # See http://docs.python.org/lib/bltin-file-objects.html
    def write(self, content):
        if self._base_content_is_iter:
            raise Exception("This %s instance is not writable" % self.__class__)
        self._container.append(content)

    def flush(self):
        pass

    def tell(self):
        if self._base_content_is_iter:
            raise Exception("This %s instance cannot tell its position" % self.__class__)
        return sum([len(chunk) for chunk in self])

class HttpResponseRedirectBase(HttpResponse):
    allowed_schemes = ['http', 'https', 'ftp']

    def __init__(self, redirect_to, *args, **kwargs):
        parsed = urlparse(redirect_to)
        if parsed.scheme and parsed.scheme not in self.allowed_schemes:
            raise SuspiciousOperation("Unsafe redirect to URL with protocol '%s'" % parsed.scheme)
        super(HttpResponseRedirectBase, self).__init__(*args, **kwargs)
        self['Location'] = iri_to_uri(redirect_to)

class HttpResponseRedirect(HttpResponseRedirectBase):
    status_code = 302

class HttpResponsePermanentRedirect(HttpResponseRedirectBase):
    status_code = 301

class HttpResponseNotModified(HttpResponse):
    status_code = 304

    def __init__(self, *args, **kwargs):
        super(HttpResponseNotModified, self).__init__(*args, **kwargs)
        del self['content-type']

    @HttpResponse.content.setter
    def content(self, value):
        if value:
            raise AttributeError("You cannot set content to a 304 (Not Modified) response")
        self._container = []

class HttpResponseBadRequest(HttpResponse):
    status_code = 400

class HttpResponseNotFound(HttpResponse):
    status_code = 404

class HttpResponseForbidden(HttpResponse):
    status_code = 403

class HttpResponseNotAllowed(HttpResponse):
    status_code = 405

    def __init__(self, permitted_methods, *args, **kwargs):
        super(HttpResponseNotAllowed, self).__init__(*args, **kwargs)
        self['Allow'] = ', '.join(permitted_methods)

class HttpResponseGone(HttpResponse):
    status_code = 410

class HttpResponseServerError(HttpResponse):
    status_code = 500

# A backwards compatible alias for HttpRequest.get_host.
def get_host(request):
    return request.get_host()

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

