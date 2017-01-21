import json
import mimetypes
import os
import re
import sys
from copy import copy
from importlib import import_module
from io import BytesIO
from urllib.parse import urljoin, urlparse, urlsplit

from django.conf import settings
from django.core.handlers.base import BaseHandler
from django.core.handlers.wsgi import ISO_8859_1, UTF_8, WSGIRequest
from django.core.signals import (
    got_request_exception, request_finished, request_started,
)
from django.db import close_old_connections
from django.http import HttpRequest, QueryDict, SimpleCookie
from django.template import TemplateDoesNotExist
from django.test import signals
from django.test.utils import ContextList
from django.urls import resolve
from django.utils.encoding import force_bytes, uri_to_iri
from django.utils.functional import SimpleLazyObject, curry
from django.utils.http import urlencode
from django.utils.itercompat import is_iterable

__all__ = ('Client', 'RedirectCycleError', 'RequestFactory', 'encode_file', 'encode_multipart')


BOUNDARY = 'BoUnDaRyStRiNg'
MULTIPART_CONTENT = 'multipart/form-data; boundary=%s' % BOUNDARY
CONTENT_TYPE_RE = re.compile(r'.*; charset=([\w\d-]+);?')
# JSON Vendor Tree spec: https://tools.ietf.org/html/rfc6838#section-3.2
JSON_CONTENT_TYPE_RE = re.compile(r'^application\/(vnd\..+\+)?json$')


class RedirectCycleError(Exception):
    """
    The test client has been asked to follow a redirect loop.
    """
    def __init__(self, message, last_response):
        super().__init__(message)
        self.last_response = last_response
        self.redirect_chain = last_response.redirect_chain


class FakePayload:
    """
    A wrapper around BytesIO that restricts what can be read since data from
    the network can't be seeked and cannot be read outside of its content
    length. This makes sure that views can't do anything under the test client
    that wouldn't work in Real Life.
    """
    def __init__(self, content=None):
        self.__content = BytesIO()
        self.__len = 0
        self.read_started = False
        if content is not None:
            self.write(content)

    def __len__(self):
        return self.__len

    def read(self, num_bytes=None):
        if not self.read_started:
            self.__content.seek(0)
            self.read_started = True
        if num_bytes is None:
            num_bytes = self.__len or 0
        assert self.__len >= num_bytes, "Cannot read more than the available bytes from the HTTP incoming data."
        content = self.__content.read(num_bytes)
        self.__len -= num_bytes
        return content

    def write(self, content):
        if self.read_started:
            raise ValueError("Unable to write a payload after he's been read")
        content = force_bytes(content)
        self.__content.write(content)
        self.__len += len(content)


def closing_iterator_wrapper(iterable, close):
    try:
        for item in iterable:
            yield item
    finally:
        request_finished.disconnect(close_old_connections)
        close()                                 # will fire request_finished
        request_finished.connect(close_old_connections)


def conditional_content_removal(request, response):
    """
    Simulate the behavior of most Web servers by removing the content of
    responses for HEAD requests, 1xx, 204, and 304 responses. Ensures
    compliance with RFC 7230, section 3.3.3.
    """
    if 100 <= response.status_code < 200 or response.status_code in (204, 304):
        if response.streaming:
            response.streaming_content = []
        else:
            response.content = b''
        response['Content-Length'] = '0'
    if request.method == 'HEAD':
        if response.streaming:
            response.streaming_content = []
        else:
            response.content = b''
    return response


class ClientHandler(BaseHandler):
    """
    A HTTP Handler that can be used for testing purposes. Uses the WSGI
    interface to compose requests, but returns the raw HttpResponse object with
    the originating WSGIRequest attached to its ``wsgi_request`` attribute.
    """
    def __init__(self, enforce_csrf_checks=True, *args, **kwargs):
        self.enforce_csrf_checks = enforce_csrf_checks
        super().__init__(*args, **kwargs)

    def __call__(self, environ):
        # Set up middleware if needed. We couldn't do this earlier, because
        # settings weren't available.
        if self._middleware_chain is None:
            self.load_middleware()

        request_started.disconnect(close_old_connections)
        request_started.send(sender=self.__class__, environ=environ)
        request_started.connect(close_old_connections)
        request = WSGIRequest(environ)
        # sneaky little hack so that we can easily get round
        # CsrfViewMiddleware.  This makes life easier, and is probably
        # required for backwards compatibility with external tests against
        # admin views.
        request._dont_enforce_csrf_checks = not self.enforce_csrf_checks

        # Request goes through middleware.
        response = self.get_response(request)

        # Simulate behaviors of most Web servers.
        conditional_content_removal(request, response)

        # Attach the originating request to the response so that it could be
        # later retrieved.
        response.wsgi_request = request

        # We're emulating a WSGI server; we must call the close method
        # on completion.
        if response.streaming:
            response.streaming_content = closing_iterator_wrapper(
                response.streaming_content, response.close)
        else:
            request_finished.disconnect(close_old_connections)
            response.close()                    # will fire request_finished
            request_finished.connect(close_old_connections)

        return response


def store_rendered_templates(store, signal, sender, template, context, **kwargs):
    """
    Stores templates and contexts that are rendered.

    The context is copied so that it is an accurate representation at the time
    of rendering.
    """
    store.setdefault('templates', []).append(template)
    if 'context' not in store:
        store['context'] = ContextList()
    store['context'].append(copy(context))


def encode_multipart(boundary, data):
    """
    Encodes multipart POST data from a dictionary of form values.

    The key will be used as the form data name; the value will be transmitted
    as content. If the value is a file, the contents of the file will be sent
    as an application/octet-stream; otherwise, str(value) will be sent.
    """
    lines = []

    def to_bytes(s):
        return force_bytes(s, settings.DEFAULT_CHARSET)

    # Not by any means perfect, but good enough for our purposes.
    def is_file(thing):
        return hasattr(thing, "read") and callable(thing.read)

    # Each bit of the multipart form data could be either a form value or a
    # file, or a *list* of form values and/or files. Remember that HTTP field
    # names can be duplicated!
    for (key, value) in data.items():
        if is_file(value):
            lines.extend(encode_file(boundary, key, value))
        elif not isinstance(value, str) and is_iterable(value):
            for item in value:
                if is_file(item):
                    lines.extend(encode_file(boundary, key, item))
                else:
                    lines.extend(to_bytes(val) for val in [
                        '--%s' % boundary,
                        'Content-Disposition: form-data; name="%s"' % key,
                        '',
                        item
                    ])
        else:
            lines.extend(to_bytes(val) for val in [
                '--%s' % boundary,
                'Content-Disposition: form-data; name="%s"' % key,
                '',
                value
            ])

    lines.extend([
        to_bytes('--%s--' % boundary),
        b'',
    ])
    return b'\r\n'.join(lines)


def encode_file(boundary, key, file):
    def to_bytes(s):
        return force_bytes(s, settings.DEFAULT_CHARSET)

    # file.name might not be a string. For example, it's an int for
    # tempfile.TemporaryFile().
    file_has_string_name = hasattr(file, 'name') and isinstance(file.name, str)
    filename = os.path.basename(file.name) if file_has_string_name else ''

    if hasattr(file, 'content_type'):
        content_type = file.content_type
    elif filename:
        content_type = mimetypes.guess_type(filename)[0]
    else:
        content_type = None

    if content_type is None:
        content_type = 'application/octet-stream'
    if not filename:
        filename = key
    return [
        to_bytes('--%s' % boundary),
        to_bytes('Content-Disposition: form-data; name="%s"; filename="%s"'
                 % (key, filename)),
        to_bytes('Content-Type: %s' % content_type),
        b'',
        to_bytes(file.read())
    ]


class RequestFactory:
    """
    Class that lets you create mock Request objects for use in testing.

    Usage:

    rf = RequestFactory()
    get_request = rf.get('/hello/')
    post_request = rf.post('/submit/', {'foo': 'bar'})

    Once you have a request object you can pass it to any view function,
    just as if that view had been hooked up using a URLconf.
    """
    def __init__(self, **defaults):
        self.defaults = defaults
        self.cookies = SimpleCookie()
        self.errors = BytesIO()

    def _base_environ(self, **request):
        """
        The base environment for a request.
        """
        # This is a minimal valid WSGI environ dictionary, plus:
        # - HTTP_COOKIE: for cookie support,
        # - REMOTE_ADDR: often useful, see #8551.
        # See http://www.python.org/dev/peps/pep-3333/#environ-variables
        environ = {
            'HTTP_COOKIE': self.cookies.output(header='', sep='; '),
            'PATH_INFO': '/',
            'REMOTE_ADDR': '127.0.0.1',
            'REQUEST_METHOD': 'GET',
            'SCRIPT_NAME': '',
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': '80',
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'http',
            'wsgi.input': FakePayload(b''),
            'wsgi.errors': self.errors,
            'wsgi.multiprocess': True,
            'wsgi.multithread': False,
            'wsgi.run_once': False,
        }
        environ.update(self.defaults)
        environ.update(request)
        return environ

    def request(self, **request):
        "Construct a generic request object."
        return WSGIRequest(self._base_environ(**request))

    def _encode_data(self, data, content_type):
        if content_type is MULTIPART_CONTENT:
            return encode_multipart(BOUNDARY, data)
        else:
            # Encode the content so that the byte representation is correct.
            match = CONTENT_TYPE_RE.match(content_type)
            if match:
                charset = match.group(1)
            else:
                charset = settings.DEFAULT_CHARSET
            return force_bytes(data, encoding=charset)

    def _get_path(self, parsed):
        path = parsed.path
        # If there are parameters, add them
        if parsed.params:
            path += ";" + parsed.params
        path = uri_to_iri(path).encode(UTF_8)
        # Replace the behavior where non-ASCII values in the WSGI environ are
        # arbitrarily decoded with ISO-8859-1.
        # Refs comment in `get_bytes_from_wsgi()`.
        return path.decode(ISO_8859_1)

    def get(self, path, data=None, secure=False, **extra):
        "Construct a GET request."

        data = {} if data is None else data
        r = {
            'QUERY_STRING': urlencode(data, doseq=True),
        }
        r.update(extra)
        return self.generic('GET', path, secure=secure, **r)

    def post(self, path, data=None, content_type=MULTIPART_CONTENT,
             secure=False, **extra):
        "Construct a POST request."

        data = {} if data is None else data
        post_data = self._encode_data(data, content_type)

        return self.generic('POST', path, post_data, content_type,
                            secure=secure, **extra)

    def head(self, path, data=None, secure=False, **extra):
        "Construct a HEAD request."

        data = {} if data is None else data
        r = {
            'QUERY_STRING': urlencode(data, doseq=True),
        }
        r.update(extra)
        return self.generic('HEAD', path, secure=secure, **r)

    def trace(self, path, secure=False, **extra):
        "Construct a TRACE request."
        return self.generic('TRACE', path, secure=secure, **extra)

    def options(self, path, data='', content_type='application/octet-stream',
                secure=False, **extra):
        "Construct an OPTIONS request."
        return self.generic('OPTIONS', path, data, content_type,
                            secure=secure, **extra)

    def put(self, path, data='', content_type='application/octet-stream',
            secure=False, **extra):
        "Construct a PUT request."
        return self.generic('PUT', path, data, content_type,
                            secure=secure, **extra)

    def patch(self, path, data='', content_type='application/octet-stream',
              secure=False, **extra):
        "Construct a PATCH request."
        return self.generic('PATCH', path, data, content_type,
                            secure=secure, **extra)

    def delete(self, path, data='', content_type='application/octet-stream',
               secure=False, **extra):
        "Construct a DELETE request."
        return self.generic('DELETE', path, data, content_type,
                            secure=secure, **extra)

    def generic(self, method, path, data='',
                content_type='application/octet-stream', secure=False,
                **extra):
        """Constructs an arbitrary HTTP request."""
        parsed = urlparse(str(path))  # path can be lazy
        data = force_bytes(data, settings.DEFAULT_CHARSET)
        r = {
            'PATH_INFO': self._get_path(parsed),
            'REQUEST_METHOD': method,
            'SERVER_PORT': '443' if secure else '80',
            'wsgi.url_scheme': 'https' if secure else 'http',
        }
        if data:
            r.update({
                'CONTENT_LENGTH': len(data),
                'CONTENT_TYPE': content_type,
                'wsgi.input': FakePayload(data),
            })
        r.update(extra)
        # If QUERY_STRING is absent or empty, we want to extract it from the URL.
        if not r.get('QUERY_STRING'):
            # WSGI requires latin-1 encoded strings. See get_path_info().
            query_string = force_bytes(parsed[4]).decode('iso-8859-1')
            r['QUERY_STRING'] = query_string
        return self.request(**r)


class Client(RequestFactory):
    """
    A class that can act as a client for testing purposes.

    It allows the user to compose GET and POST requests, and
    obtain the response that the server gave to those requests.
    The server Response objects are annotated with the details
    of the contexts and templates that were rendered during the
    process of serving the request.

    Client objects are stateful - they will retain cookie (and
    thus session) details for the lifetime of the Client instance.

    This is not intended as a replacement for Twill/Selenium or
    the like - it is here to allow testing against the
    contexts and templates produced by a view, rather than the
    HTML rendered to the end-user.
    """
    def __init__(self, enforce_csrf_checks=False, **defaults):
        super().__init__(**defaults)
        self.handler = ClientHandler(enforce_csrf_checks)
        self.exc_info = None

    def store_exc_info(self, **kwargs):
        """
        Stores exceptions when they are generated by a view.
        """
        self.exc_info = sys.exc_info()

    @property
    def session(self):
        """
        Obtains the current session variables.
        """
        engine = import_module(settings.SESSION_ENGINE)
        cookie = self.cookies.get(settings.SESSION_COOKIE_NAME)
        if cookie:
            return engine.SessionStore(cookie.value)

        session = engine.SessionStore()
        session.save()
        self.cookies[settings.SESSION_COOKIE_NAME] = session.session_key
        return session

    def request(self, **request):
        """
        The master request method. Composes the environment dictionary
        and passes to the handler, returning the result of the handler.
        Assumes defaults for the query environment, which can be overridden
        using the arguments to the request.
        """
        environ = self._base_environ(**request)

        # Curry a data dictionary into an instance of the template renderer
        # callback function.
        data = {}
        on_template_render = curry(store_rendered_templates, data)
        signal_uid = "template-render-%s" % id(request)
        signals.template_rendered.connect(on_template_render, dispatch_uid=signal_uid)
        # Capture exceptions created by the handler.
        exception_uid = "request-exception-%s" % id(request)
        got_request_exception.connect(self.store_exc_info, dispatch_uid=exception_uid)
        try:
            try:
                response = self.handler(environ)
            except TemplateDoesNotExist as e:
                # If the view raises an exception, Django will attempt to show
                # the 500.html template. If that template is not available,
                # we should ignore the error in favor of re-raising the
                # underlying exception that caused the 500 error. Any other
                # template found to be missing during view error handling
                # should be reported as-is.
                if e.args != ('500.html',):
                    raise

            # Look for a signalled exception, clear the current context
            # exception data, then re-raise the signalled exception.
            # Also make sure that the signalled exception is cleared from
            # the local cache!
            if self.exc_info:
                exc_info = self.exc_info
                self.exc_info = None
                raise exc_info[0](exc_info[1]).with_traceback(exc_info[2])

            # Save the client and request that stimulated the response.
            response.client = self
            response.request = request

            # Add any rendered template detail to the response.
            response.templates = data.get("templates", [])
            response.context = data.get("context")

            response.json = curry(self._parse_json, response)

            # Attach the ResolverMatch instance to the response
            response.resolver_match = SimpleLazyObject(lambda: resolve(request['PATH_INFO']))

            # Flatten a single context. Not really necessary anymore thanks to
            # the __getattr__ flattening in ContextList, but has some edge-case
            # backwards-compatibility implications.
            if response.context and len(response.context) == 1:
                response.context = response.context[0]

            # Update persistent cookie data.
            if response.cookies:
                self.cookies.update(response.cookies)

            return response
        finally:
            signals.template_rendered.disconnect(dispatch_uid=signal_uid)
            got_request_exception.disconnect(dispatch_uid=exception_uid)

    def get(self, path, data=None, follow=False, secure=False, **extra):
        """
        Requests a response from the server using GET.
        """
        response = super().get(path, data=data, secure=secure, **extra)
        if follow:
            response = self._handle_redirects(response, **extra)
        return response

    def post(self, path, data=None, content_type=MULTIPART_CONTENT,
             follow=False, secure=False, **extra):
        """
        Requests a response from the server using POST.
        """
        response = super().post(path, data=data, content_type=content_type, secure=secure, **extra)
        if follow:
            response = self._handle_redirects(response, **extra)
        return response

    def head(self, path, data=None, follow=False, secure=False, **extra):
        """
        Request a response from the server using HEAD.
        """
        response = super().head(path, data=data, secure=secure, **extra)
        if follow:
            response = self._handle_redirects(response, **extra)
        return response

    def options(self, path, data='', content_type='application/octet-stream',
                follow=False, secure=False, **extra):
        """
        Request a response from the server using OPTIONS.
        """
        response = super().options(path, data=data, content_type=content_type, secure=secure, **extra)
        if follow:
            response = self._handle_redirects(response, **extra)
        return response

    def put(self, path, data='', content_type='application/octet-stream',
            follow=False, secure=False, **extra):
        """
        Send a resource to the server using PUT.
        """
        response = super().put(path, data=data, content_type=content_type, secure=secure, **extra)
        if follow:
            response = self._handle_redirects(response, **extra)
        return response

    def patch(self, path, data='', content_type='application/octet-stream',
              follow=False, secure=False, **extra):
        """
        Send a resource to the server using PATCH.
        """
        response = super().patch(path, data=data, content_type=content_type, secure=secure, **extra)
        if follow:
            response = self._handle_redirects(response, **extra)
        return response

    def delete(self, path, data='', content_type='application/octet-stream',
               follow=False, secure=False, **extra):
        """
        Send a DELETE request to the server.
        """
        response = super().delete(path, data=data, content_type=content_type, secure=secure, **extra)
        if follow:
            response = self._handle_redirects(response, **extra)
        return response

    def trace(self, path, data='', follow=False, secure=False, **extra):
        """
        Send a TRACE request to the server.
        """
        response = super().trace(path, data=data, secure=secure, **extra)
        if follow:
            response = self._handle_redirects(response, **extra)
        return response

    def login(self, **credentials):
        """
        Sets the Factory to appear as if it has successfully logged into a site.

        Returns True if login is possible; False if the provided credentials
        are incorrect.
        """
        from django.contrib.auth import authenticate
        user = authenticate(**credentials)
        if user:
            self._login(user)
            return True
        else:
            return False

    def force_login(self, user, backend=None):
        def get_backend():
            from django.contrib.auth import load_backend
            for backend_path in settings.AUTHENTICATION_BACKENDS:
                backend = load_backend(backend_path)
                if hasattr(backend, 'get_user'):
                    return backend_path
        if backend is None:
            backend = get_backend()
        user.backend = backend
        self._login(user, backend)

    def _login(self, user, backend=None):
        from django.contrib.auth import login
        engine = import_module(settings.SESSION_ENGINE)

        # Create a fake request to store login details.
        request = HttpRequest()

        if self.session:
            request.session = self.session
        else:
            request.session = engine.SessionStore()
        login(request, user, backend)

        # Save the session values.
        request.session.save()

        # Set the cookie to represent the session.
        session_cookie = settings.SESSION_COOKIE_NAME
        self.cookies[session_cookie] = request.session.session_key
        cookie_data = {
            'max-age': None,
            'path': '/',
            'domain': settings.SESSION_COOKIE_DOMAIN,
            'secure': settings.SESSION_COOKIE_SECURE or None,
            'expires': None,
        }
        self.cookies[session_cookie].update(cookie_data)

    def logout(self):
        """
        Removes the authenticated user's cookies and session object.

        Causes the authenticated user to be logged out.
        """
        from django.contrib.auth import get_user, logout

        request = HttpRequest()
        engine = import_module(settings.SESSION_ENGINE)
        if self.session:
            request.session = self.session
            request.user = get_user(request)
        else:
            request.session = engine.SessionStore()
        logout(request)
        self.cookies = SimpleCookie()

    def _parse_json(self, response, **extra):
        if not hasattr(response, '_json'):
            if not JSON_CONTENT_TYPE_RE.match(response.get('Content-Type')):
                raise ValueError(
                    'Content-Type header is "{0}", not "application/json"'
                    .format(response.get('Content-Type'))
                )
            response._json = json.loads(response.content.decode(), **extra)
        return response._json

    def _handle_redirects(self, response, **extra):
        "Follows any redirects by requesting responses from the server using GET."

        response.redirect_chain = []
        while response.status_code in (301, 302, 303, 307):
            response_url = response.url
            redirect_chain = response.redirect_chain
            redirect_chain.append((response_url, response.status_code))

            url = urlsplit(response_url)
            if url.scheme:
                extra['wsgi.url_scheme'] = url.scheme
            if url.hostname:
                extra['SERVER_NAME'] = url.hostname
            if url.port:
                extra['SERVER_PORT'] = str(url.port)

            # Prepend the request path to handle relative path redirects
            path = url.path
            if not path.startswith('/'):
                path = urljoin(response.request['PATH_INFO'], path)

            response = self.get(path, QueryDict(url.query), follow=False, **extra)
            response.redirect_chain = redirect_chain

            if redirect_chain[-1] in redirect_chain[:-1]:
                # Check that we're not redirecting to somewhere we've already
                # been to, to prevent loops.
                raise RedirectCycleError("Redirect loop detected.", last_response=response)
            if len(redirect_chain) > 20:
                # Such a lengthy chain likely also means a loop, but one with
                # a growing path, changing view, or changing query argument;
                # 20 is the value of "network.http.redirection-limit" from Firefox.
                raise RedirectCycleError("Too many redirects.", last_response=response)

        return response
