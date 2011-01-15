from pprint import pformat
import sys
from threading import Lock
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import socket

from django import http
from django.core import signals
from django.core.handlers import base
from django.core.urlresolvers import set_script_prefix
from django.utils import datastructures
from django.utils.encoding import force_unicode, iri_to_uri
from django.utils.log import getLogger

logger = getLogger('django.request')


# See http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html
STATUS_CODE_TEXT = {
    100: 'CONTINUE',
    101: 'SWITCHING PROTOCOLS',
    200: 'OK',
    201: 'CREATED',
    202: 'ACCEPTED',
    203: 'NON-AUTHORITATIVE INFORMATION',
    204: 'NO CONTENT',
    205: 'RESET CONTENT',
    206: 'PARTIAL CONTENT',
    300: 'MULTIPLE CHOICES',
    301: 'MOVED PERMANENTLY',
    302: 'FOUND',
    303: 'SEE OTHER',
    304: 'NOT MODIFIED',
    305: 'USE PROXY',
    306: 'RESERVED',
    307: 'TEMPORARY REDIRECT',
    400: 'BAD REQUEST',
    401: 'UNAUTHORIZED',
    402: 'PAYMENT REQUIRED',
    403: 'FORBIDDEN',
    404: 'NOT FOUND',
    405: 'METHOD NOT ALLOWED',
    406: 'NOT ACCEPTABLE',
    407: 'PROXY AUTHENTICATION REQUIRED',
    408: 'REQUEST TIMEOUT',
    409: 'CONFLICT',
    410: 'GONE',
    411: 'LENGTH REQUIRED',
    412: 'PRECONDITION FAILED',
    413: 'REQUEST ENTITY TOO LARGE',
    414: 'REQUEST-URI TOO LONG',
    415: 'UNSUPPORTED MEDIA TYPE',
    416: 'REQUESTED RANGE NOT SATISFIABLE',
    417: 'EXPECTATION FAILED',
    500: 'INTERNAL SERVER ERROR',
    501: 'NOT IMPLEMENTED',
    502: 'BAD GATEWAY',
    503: 'SERVICE UNAVAILABLE',
    504: 'GATEWAY TIMEOUT',
    505: 'HTTP VERSION NOT SUPPORTED',
}

class LimitedStream(object):
    '''
    LimitedStream wraps another stream in order to not allow reading from it
    past specified amount of bytes.
    '''
    def __init__(self, stream, limit, buf_size=64 * 1024 * 1024):
        self.stream = stream
        self.remaining = limit
        self.buffer = ''
        self.buf_size = buf_size

    def _read_limited(self, size=None):
        if size is None or size > self.remaining:
            size = self.remaining
        if size == 0:
            return ''
        result = self.stream.read(size)
        self.remaining -= len(result)
        return result

    def read(self, size=None):
        if size is None:
            result = self.buffer + self._read_limited()
            self.buffer = ''
        elif size < len(self.buffer):
            result = self.buffer[:size]
            self.buffer = self.buffer[size:]
        else: # size >= len(self.buffer)
            result = self.buffer + self._read_limited(size - len(self.buffer))
            self.buffer = ''
        return result

    def readline(self, size=None):
        while '\n' not in self.buffer or \
              (size is not None and len(self.buffer) < size):
            if size:
                chunk = self._read_limited(size - len(self.buffer))
            else:
                chunk = self._read_limited()
            if not chunk:
                break
            self.buffer += chunk
        sio = StringIO(self.buffer)
        if size:
            line = sio.readline(size)
        else:
            line = sio.readline()
        self.buffer = sio.read()
        return line

class WSGIRequest(http.HttpRequest):
    def __init__(self, environ):
        script_name = base.get_script_name(environ)
        path_info = force_unicode(environ.get('PATH_INFO', u'/'))
        if not path_info or path_info == script_name:
            # Sometimes PATH_INFO exists, but is empty (e.g. accessing
            # the SCRIPT_NAME URL without a trailing slash). We really need to
            # operate as if they'd requested '/'. Not amazingly nice to force
            # the path like this, but should be harmless.
            #
            # (The comparison of path_info to script_name is to work around an
            # apparent bug in flup 1.0.1. Se Django ticket #8490).
            path_info = u'/'
        self.environ = environ
        self.path_info = path_info
        self.path = '%s%s' % (script_name, path_info)
        self.META = environ
        self.META['PATH_INFO'] = path_info
        self.META['SCRIPT_NAME'] = script_name
        self.method = environ['REQUEST_METHOD'].upper()
        self._post_parse_error = False
        if type(socket._fileobject) is type and isinstance(self.environ['wsgi.input'], socket._fileobject):
            # Under development server 'wsgi.input' is an instance of
            # socket._fileobject which hangs indefinitely on reading bytes past
            # available count. To prevent this it's wrapped in LimitedStream
            # that doesn't read past Content-Length bytes.
            #
            # This is not done for other kinds of inputs (like flup's FastCGI
            # streams) beacuse they don't suffer from this problem and we can
            # avoid using another wrapper with its own .read and .readline
            # implementation.
            #
            # The type check is done because for some reason, AppEngine
            # implements _fileobject as a function, not a class.
            try:
                content_length = int(self.environ.get('CONTENT_LENGTH', 0))
            except (ValueError, TypeError):
                content_length = 0
            self._stream = LimitedStream(self.environ['wsgi.input'], content_length)
        else:
            self._stream = self.environ['wsgi.input']
        self._read_started = False

    def __repr__(self):
        # Since this is called as part of error handling, we need to be very
        # robust against potentially malformed input.
        try:
            get = pformat(self.GET)
        except:
            get = '<could not parse>'
        if self._post_parse_error:
            post = '<could not parse>'
        else:
            try:
                post = pformat(self.POST)
            except:
                post = '<could not parse>'
        try:
            cookies = pformat(self.COOKIES)
        except:
            cookies = '<could not parse>'
        try:
            meta = pformat(self.META)
        except:
            meta = '<could not parse>'
        return '<WSGIRequest\nGET:%s,\nPOST:%s,\nCOOKIES:%s,\nMETA:%s>' % \
            (get, post, cookies, meta)

    def get_full_path(self):
        # RFC 3986 requires query string arguments to be in the ASCII range.
        # Rather than crash if this doesn't happen, we encode defensively.
        return '%s%s' % (self.path, self.environ.get('QUERY_STRING', '') and ('?' + iri_to_uri(self.environ.get('QUERY_STRING', ''))) or '')

    def is_secure(self):
        return 'wsgi.url_scheme' in self.environ \
            and self.environ['wsgi.url_scheme'] == 'https'

    def _get_request(self):
        if not hasattr(self, '_request'):
            self._request = datastructures.MergeDict(self.POST, self.GET)
        return self._request

    def _get_get(self):
        if not hasattr(self, '_get'):
            # The WSGI spec says 'QUERY_STRING' may be absent.
            self._get = http.QueryDict(self.environ.get('QUERY_STRING', ''), encoding=self._encoding)
        return self._get

    def _set_get(self, get):
        self._get = get

    def _get_post(self):
        if not hasattr(self, '_post'):
            self._load_post_and_files()
        return self._post

    def _set_post(self, post):
        self._post = post

    def _get_cookies(self):
        if not hasattr(self, '_cookies'):
            self._cookies = http.parse_cookie(self.environ.get('HTTP_COOKIE', ''))
        return self._cookies

    def _set_cookies(self, cookies):
        self._cookies = cookies

    def _get_files(self):
        if not hasattr(self, '_files'):
            self._load_post_and_files()
        return self._files

    GET = property(_get_get, _set_get)
    POST = property(_get_post, _set_post)
    COOKIES = property(_get_cookies, _set_cookies)
    FILES = property(_get_files)
    REQUEST = property(_get_request)

class WSGIHandler(base.BaseHandler):
    initLock = Lock()
    request_class = WSGIRequest

    def __call__(self, environ, start_response):
        from django.conf import settings

        # Set up middleware if needed. We couldn't do this earlier, because
        # settings weren't available.
        if self._request_middleware is None:
            self.initLock.acquire()
            try:
                try:
                    # Check that middleware is still uninitialised.
                    if self._request_middleware is None:
                        self.load_middleware()
                except:
                    # Unload whatever middleware we got
                    self._request_middleware = None
                    raise
            finally:
                self.initLock.release()

        set_script_prefix(base.get_script_name(environ))
        signals.request_started.send(sender=self.__class__)
        try:
            try:
                request = self.request_class(environ)
            except UnicodeDecodeError:
                logger.warning('Bad Request (UnicodeDecodeError): %s' % request.path,
                    exc_info=sys.exc_info(),
                    extra={
                        'status_code': 400,
                        'request': request
                    }
                )
                response = http.HttpResponseBadRequest()
            else:
                response = self.get_response(request)
        finally:
            signals.request_finished.send(sender=self.__class__)

        try:
            status_text = STATUS_CODE_TEXT[response.status_code]
        except KeyError:
            status_text = 'UNKNOWN STATUS CODE'
        status = '%s %s' % (response.status_code, status_text)
        response_headers = [(str(k), str(v)) for k, v in response.items()]
        for c in response.cookies.values():
            response_headers.append(('Set-Cookie', str(c.output(header=''))))
        start_response(status, response_headers)
        return response

