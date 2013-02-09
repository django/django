from __future__ import absolute_import

import datetime
import os
import re
import sys
import time
import warnings

from pprint import pformat
from urllib import urlencode, quote
from urlparse import urljoin, urlparse
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
try:
    # The mod_python version is more efficient, so try importing it first.
    from mod_python.util import parse_qsl
except ImportError:
    try:
        # Python 2.6 and greater
        from urlparse import parse_qsl
    except ImportError:
        # Python 2.5. Works on Python 2.6 but raises PendingDeprecationWarning
        from cgi import parse_qsl

import Cookie
# httponly support exists in Python 2.6's Cookie library,
# but not in Python 2.5.
_morsel_supports_httponly = 'httponly' in Cookie.Morsel._reserved
# Some versions of Python 2.7 and later won't need this encoding bug fix:
_cookie_encodes_correctly = Cookie.SimpleCookie().value_encode(';') == (';', '"\\073"')
# See ticket #13007, http://bugs.python.org/issue2193 and http://trac.edgewall.org/ticket/2256
_tc = Cookie.SimpleCookie()
try:
    _tc.load('foo:bar=1')
    _cookie_allows_colon_in_names = True
except Cookie.CookieError:
    _cookie_allows_colon_in_names = False

if _morsel_supports_httponly and _cookie_encodes_correctly and _cookie_allows_colon_in_names:
    SimpleCookie = Cookie.SimpleCookie
else:
    if not _morsel_supports_httponly:
        class Morsel(Cookie.Morsel):
            def __setitem__(self, K, V):
                K = K.lower()
                if K == "httponly":
                    if V:
                        # The superclass rejects httponly as a key,
                        # so we jump to the grandparent.
                        super(Cookie.Morsel, self).__setitem__(K, V)
                else:
                    super(Morsel, self).__setitem__(K, V)

            def OutputString(self, attrs=None):
                output = super(Morsel, self).OutputString(attrs)
                if "httponly" in self:
                    output += "; httponly"
                return output
    else:
        Morsel = Cookie.Morsel

    class SimpleCookie(Cookie.SimpleCookie):
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

        if not _cookie_allows_colon_in_names or not _morsel_supports_httponly:
            def load(self, rawdata):
                self.bad_cookies = set()
                super(SimpleCookie, self).load(rawdata)
                for key in self.bad_cookies:
                    del self[key]

            # override private __set() method:
            # (needed for using our Morsel, and for laxness with CookieError
            def _BaseCookie__set(self, key, real_value, coded_value):
                try:
                    M = self.get(key, Morsel())
                    M.set(key, real_value, coded_value)
                    dict.__setitem__(self, key, M)
                except Cookie.CookieError:
                    self.bad_cookies.add(key)
                    dict.__setitem__(self, key, Cookie.Morsel())


class CompatCookie(SimpleCookie):
    def __init__(self, *args, **kwargs):
        super(CompatCookie, self).__init__(*args, **kwargs)
        warnings.warn("CompatCookie is deprecated. Use django.http.SimpleCookie instead.", DeprecationWarning)

from django.conf import settings
from django.core import signing
from django.core.exceptions import ImproperlyConfigured, SuspiciousOperation
from django.core.files import uploadhandler
from django.http.multipartparser import MultiPartParser
from django.http.utils import *
from django.utils.datastructures import MultiValueDict, ImmutableList
from django.utils.encoding import smart_str, iri_to_uri, force_unicode
from django.utils.http import cookie_date
from django.utils import timezone

RESERVED_CHARS="!*'();:@&=+$,/?%#[]"

absolute_http_url_re = re.compile(r"^https?://", re.I)
host_validation_re = re.compile(r"^([a-z0-9.-]+|\[[a-f0-9]*:[a-f0-9:]+\])(:\d+)?$")


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
    except:
        get = '<could not parse>'
    if request._post_parse_error:
        post = '<could not parse>'
    else:
        try:
            post = (pformat(POST_override)
                    if POST_override is not None
                    else pformat(request.POST))
        except:
            post = '<could not parse>'
    try:
        cookies = (pformat(COOKIES_override)
                   if COOKIES_override is not None
                   else pformat(request.COOKIES))
    except:
        cookies = '<could not parse>'
    try:
        meta = (pformat(META_override)
                if META_override is not None
                else pformat(request.META))
    except:
        meta = '<could not parse>'
    path = path_override if path_override is not None else request.path
    return smart_str(u'<%s\npath:%s,\nGET:%s,\nPOST:%s,\nCOOKIES:%s,\nMETA:%s>' %
                     (request.__class__.__name__,
                      path,
                      unicode(get),
                      unicode(post),
                      unicode(cookies),
                      unicode(meta)))

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
            if server_port != (self.is_secure() and '443' or '80'):
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
        return '%s%s' % (self.path, self.META.get('QUERY_STRING', '') and ('?' + iri_to_uri(self.META.get('QUERY_STRING', ''))) or '')

    def get_signed_cookie(self, key, default=RAISE_ERROR, salt='', max_age=None):
        """
        Attempts to return a signed cookie. If the signature fails or the
        cookie has expired, raises an exception... unless you provide the
        default argument in which case that value will be returned instead.
        """
        try:
            cookie_value = self.COOKIES[key].encode('utf-8')
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
            current_uri = '%s://%s%s' % (self.is_secure() and 'https' or 'http',
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

    def _set_encoding(self, val):
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

    def _get_encoding(self):
        return self._encoding

    encoding = property(_get_encoding, _set_encoding)

    def _initialize_handlers(self):
        self._upload_handlers = [uploadhandler.load_handler(handler, self)
                                 for handler in settings.FILE_UPLOAD_HANDLERS]

    def _set_upload_handlers(self, upload_handlers):
        if hasattr(self, '_files'):
            raise AttributeError("You cannot set the upload handlers after the upload has been processed.")
        self._upload_handlers = upload_handlers

    def _get_upload_handlers(self):
        if not self._upload_handlers:
            # If there are no upload handlers defined, initialize them from settings.
            self._initialize_handlers()
        return self._upload_handlers

    upload_handlers = property(_get_upload_handlers, _set_upload_handlers)

    def parse_file_upload(self, META, post_data):
        """Returns a tuple of (POST QueryDict, FILES MultiValueDict)."""
        self.upload_handlers = ImmutableList(
            self.upload_handlers,
            warning = "You cannot alter upload handlers after the upload has been processed."
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
            except IOError, e:
                raise UnreadablePostError, e, sys.exc_traceback
            self._stream = StringIO(self._body)
        return self._body

    @property
    def raw_post_data(self):
        warnings.warn('HttpRequest.raw_post_data has been deprecated. Use HttpRequest.body instead.', PendingDeprecationWarning)
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
                data = StringIO(self._body)
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
    ## a corresponding request subclass (WSGIRequest or ModPythonRequest).
    ## Also when request data has already been read by request.POST or
    ## request.body, self._stream points to a StringIO instance
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
        MultiValueDict.__init__(self)
        if not encoding:
            encoding = settings.DEFAULT_CHARSET
        self.encoding = encoding
        for key, value in parse_qsl((query_string or ''), True): # keep_blank_values=True
            self.appendlist(force_unicode(key, encoding, errors='replace'),
                            force_unicode(value, encoding, errors='replace'))
        self._mutable = mutable

    def _get_encoding(self):
        if self._encoding is None:
            self._encoding = settings.DEFAULT_CHARSET
        return self._encoding

    def _set_encoding(self, value):
        self._encoding = value

    encoding = property(_get_encoding, _set_encoding)

    def _assert_mutable(self):
        if not self._mutable:
            raise AttributeError("This QueryDict instance is immutable")

    def __setitem__(self, key, value):
        self._assert_mutable()
        key = str_to_unicode(key, self.encoding)
        value = str_to_unicode(value, self.encoding)
        MultiValueDict.__setitem__(self, key, value)

    def __delitem__(self, key):
        self._assert_mutable()
        super(QueryDict, self).__delitem__(key)

    def __copy__(self):
        result = self.__class__('', mutable=True, encoding=self.encoding)
        for key, value in dict.items(self):
            dict.__setitem__(result, key, value)
        return result

    def __deepcopy__(self, memo):
        import copy
        result = self.__class__('', mutable=True, encoding=self.encoding)
        memo[id(self)] = result
        for key, value in dict.items(self):
            dict.__setitem__(result, copy.deepcopy(key, memo), copy.deepcopy(value, memo))
        return result

    def setlist(self, key, list_):
        self._assert_mutable()
        key = str_to_unicode(key, self.encoding)
        list_ = [str_to_unicode(elt, self.encoding) for elt in list_]
        MultiValueDict.setlist(self, key, list_)

    def setlistdefault(self, key, default_list=()):
        self._assert_mutable()
        if key not in self:
            self.setlist(key, default_list)
        return MultiValueDict.getlist(self, key)

    def appendlist(self, key, value):
        self._assert_mutable()
        key = str_to_unicode(key, self.encoding)
        value = str_to_unicode(value, self.encoding)
        MultiValueDict.appendlist(self, key, value)

    def update(self, other_dict):
        self._assert_mutable()
        f = lambda s: str_to_unicode(s, self.encoding)
        if hasattr(other_dict, 'lists'):
            for key, valuelist in other_dict.lists():
                for value in valuelist:
                    MultiValueDict.update(self, {f(key): f(value)})
        else:
            d = dict([(f(k), f(v)) for k, v in other_dict.items()])
            MultiValueDict.update(self, d)

    def pop(self, key, *args):
        self._assert_mutable()
        return MultiValueDict.pop(self, key, *args)

    def popitem(self):
        self._assert_mutable()
        return MultiValueDict.popitem(self)

    def clear(self):
        self._assert_mutable()
        MultiValueDict.clear(self)

    def setdefault(self, key, default=None):
        self._assert_mutable()
        key = str_to_unicode(key, self.encoding)
        default = str_to_unicode(default, self.encoding)
        return MultiValueDict.setdefault(self, key, default)

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
            encode = lambda k, v: '%s=%s' % ((quote(k, safe), quote(v, safe)))
        else:
            encode = lambda k, v: urlencode({k: v})
        for k, list_ in self.lists():
            k = smart_str(k, self.encoding)
            output.extend([encode(k, smart_str(v, self.encoding))
                           for v in list_])
        return '&'.join(output)

def parse_cookie(cookie):
    if cookie == '':
        return {}
    if not isinstance(cookie, Cookie.BaseCookie):
        try:
            c = SimpleCookie()
            c.load(cookie)
        except Cookie.CookieError:
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

    def __init__(self, content='', mimetype=None, status=None,
            content_type=None):
        # _headers is a mapping of the lower-case name to the original case of
        # the header (required for working with legacy systems) and the header
        # value. Both the name of the header and its value are ASCII strings.
        self._headers = {}
        self._charset = settings.DEFAULT_CHARSET
        if mimetype: # For backwards compatibility.
            content_type = mimetype
        if not content_type:
            content_type = "%s; charset=%s" % (settings.DEFAULT_CONTENT_TYPE,
                    self._charset)
        self.content = content
        self.cookies = SimpleCookie()
        if status:
            self.status_code = status

        self['Content-Type'] = content_type

    def __str__(self):
        """Full HTTP message, including headers."""
        return '\n'.join(['%s: %s' % (key, value)
            for key, value in self._headers.values()]) \
            + '\n\n' + self.content

    def _convert_to_ascii(self, *values):
        """Converts all values to ascii strings."""
        for value in values:
            if isinstance(value, unicode):
                try:
                    value = value.encode('us-ascii')
                except UnicodeError, e:
                    e.reason += ', HTTP response headers must be in US-ASCII format'
                    raise
            else:
                value = str(value)
            if '\n' in value or '\r' in value:
                raise BadHeaderError("Header values can't contain newlines (got %r)" % (value))
            yield value

    def __setitem__(self, header, value):
        header, value = self._convert_to_ascii(header, value)
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

    def _get_content(self):
        if self.has_header('Content-Encoding'):
            return ''.join([str(e) for e in self._container])
        return ''.join([smart_str(e, self._charset) for e in self._container])

    def _set_content(self, value):
        if hasattr(value, '__iter__'):
            self._container = value
            self._base_content_is_iter = True
        else:
            self._container = [value]
            self._base_content_is_iter = False

    content = property(_get_content, _set_content)

    def __iter__(self):
        self._iterator = iter(self._container)
        return self

    def next(self):
        chunk = self._iterator.next()
        if isinstance(chunk, unicode):
            chunk = chunk.encode(self._charset)
        return str(chunk)

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
        return sum([len(str(chunk)) for chunk in self._container])

class HttpResponseRedirectBase(HttpResponse):
    allowed_schemes = ['http', 'https', 'ftp']

    def __init__(self, redirect_to):
        super(HttpResponseRedirectBase, self).__init__()
        parsed = urlparse(redirect_to)
        if parsed.scheme and parsed.scheme not in self.allowed_schemes:
            raise SuspiciousOperation("Unsafe redirect to URL with scheme '%s'" % parsed.scheme)
        self['Location'] = iri_to_uri(redirect_to)

class HttpResponseRedirect(HttpResponseRedirectBase):
    status_code = 302

class HttpResponsePermanentRedirect(HttpResponseRedirectBase):
    status_code = 301

class HttpResponseNotModified(HttpResponse):
    status_code = 304

class HttpResponseBadRequest(HttpResponse):
    status_code = 400

class HttpResponseNotFound(HttpResponse):
    status_code = 404

class HttpResponseForbidden(HttpResponse):
    status_code = 403

class HttpResponseNotAllowed(HttpResponse):
    status_code = 405

    def __init__(self, permitted_methods):
        super(HttpResponseNotAllowed, self).__init__()
        self['Allow'] = ', '.join(permitted_methods)

class HttpResponseGone(HttpResponse):
    status_code = 410

class HttpResponseServerError(HttpResponse):
    status_code = 500

# A backwards compatible alias for HttpRequest.get_host.
def get_host(request):
    return request.get_host()

# It's neither necessary nor appropriate to use
# django.utils.encoding.smart_unicode for parsing URLs and form inputs. Thus,
# this slightly more restricted function.
def str_to_unicode(s, encoding):
    """
    Converts basestring objects to unicode, using the given encoding. Illegally
    encoded input characters are replaced with Unicode "unknown" codepoint
    (\ufffd).

    Returns any non-basestring objects without change.
    """
    if isinstance(s, str):
        return unicode(s, encoding, 'replace')
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
