from __future__ import unicode_literals

import sys
import os
import re
import mimetypes
from copy import copy
from io import BytesIO
try:
    from urllib.parse import unquote, urlparse, urlsplit
except ImportError:     # Python 2
    from urllib import unquote
    from urlparse import urlparse, urlsplit

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.core.handlers.base import BaseHandler
from django.core.handlers.wsgi import WSGIRequest
from django.core.signals import (request_started, request_finished,
    got_request_exception)
from django.db import close_connection
from django.http import SimpleCookie, HttpRequest, QueryDict
from django.template import TemplateDoesNotExist
from django.test import signals
from django.utils.functional import curry
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlencode
from django.utils.importlib import import_module
from django.utils.itercompat import is_iterable
from django.utils import six
from django.test.utils import ContextList

__all__ = ('Client', 'RequestFactory', 'encode_file', 'encode_multipart')


BOUNDARY = 'BoUnDaRyStRiNg'
MULTIPART_CONTENT = 'multipart/form-data; boundary=%s' % BOUNDARY
CONTENT_TYPE_RE = re.compile('.*; charset=([\w\d-]+);?')

class FakePayload(object):
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
        request_finished.disconnect(close_connection)
        close()                                 # will fire request_finished
        request_finished.connect(close_connection)


class ClientHandler(BaseHandler):
    """
    A HTTP Handler that can be used for testing purposes.
    Uses the WSGI interface to compose requests, but returns
    the raw HttpResponse object
    """
    def __init__(self, enforce_csrf_checks=True, *args, **kwargs):
        self.enforce_csrf_checks = enforce_csrf_checks
        super(ClientHandler, self).__init__(*args, **kwargs)

    def __call__(self, environ):
        from django.conf import settings

        # Set up middleware if needed. We couldn't do this earlier, because
        # settings weren't available.
        if self._request_middleware is None:
            self.load_middleware()

        request_started.send(sender=self.__class__)
        request = WSGIRequest(environ)
        # sneaky little hack so that we can easily get round
        # CsrfViewMiddleware.  This makes life easier, and is probably
        # required for backwards compatibility with external tests against
        # admin views.
        request._dont_enforce_csrf_checks = not self.enforce_csrf_checks
        response = self.get_response(request)
        # We're emulating a WSGI server; we must call the close method
        # on completion.
        if response.streaming:
            response.streaming_content = closing_iterator_wrapper(
                response.streaming_content, response.close)
        else:
            request_finished.disconnect(close_connection)
            response.close()                    # will fire request_finished
            request_finished.connect(close_connection)

        return response

def store_rendered_templates(store, signal, sender, template, context, **kwargs):
    """
    Stores templates and contexts that are rendered.

    The context is copied so that it is an accurate representation at the time
    of rendering.
    """
    store.setdefault('templates', []).append(template)
    store.setdefault('context', ContextList()).append(copy(context))

def encode_multipart(boundary, data):
    """
    Encodes multipart POST data from a dictionary of form values.

    The key will be used as the form data name; the value will be transmitted
    as content. If the value is a file, the contents of the file will be sent
    as an application/octet-stream; otherwise, str(value) will be sent.
    """
    lines = []
    to_bytes = lambda s: force_bytes(s, settings.DEFAULT_CHARSET)

    # Not by any means perfect, but good enough for our purposes.
    is_file = lambda thing: hasattr(thing, "read") and callable(thing.read)

    # Each bit of the multipart form data could be either a form value or a
    # file, or a *list* of form values and/or files. Remember that HTTP field
    # names can be duplicated!
    for (key, value) in data.items():
        if is_file(value):
            lines.extend(encode_file(boundary, key, value))
        elif not isinstance(value, six.string_types) and is_iterable(value):
            for item in value:
                if is_file(item):
                    lines.extend(encode_file(boundary, key, item))
                else:
                    lines.extend([to_bytes(val) for val in [
                        '--%s' % boundary,
                        'Content-Disposition: form-data; name="%s"' % key,
                        '',
                        item
                    ]])
        else:
            lines.extend([to_bytes(val) for val in [
                '--%s' % boundary,
                'Content-Disposition: form-data; name="%s"' % key,
                '',
                value
            ]])

    lines.extend([
        to_bytes('--%s--' % boundary),
        b'',
    ])
    return b'\r\n'.join(lines)

def encode_file(boundary, key, file):
    to_bytes = lambda s: force_bytes(s, settings.DEFAULT_CHARSET)
    content_type = mimetypes.guess_type(file.name)[0]
    if content_type is None:
        content_type = 'application/octet-stream'
    return [
        to_bytes('--%s' % boundary),
        to_bytes('Content-Disposition: form-data; name="%s"; filename="%s"' \
            % (key, os.path.basename(file.name))),
        to_bytes('Content-Type: %s' % content_type),
        b'',
        file.read()
    ]


class RequestFactory(object):
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
            'HTTP_COOKIE':       self.cookies.output(header='', sep='; '),
            'PATH_INFO':         str('/'),
            'REMOTE_ADDR':       str('127.0.0.1'),
            'REQUEST_METHOD':    str('GET'),
            'SCRIPT_NAME':       str(''),
            'SERVER_NAME':       str('testserver'),
            'SERVER_PORT':       str('80'),
            'SERVER_PROTOCOL':   str('HTTP/1.1'),
            'wsgi.version':      (1, 0),
            'wsgi.url_scheme':   str('http'),
            'wsgi.input':        FakePayload(b''),
            'wsgi.errors':       self.errors,
            'wsgi.multiprocess': True,
            'wsgi.multithread':  False,
            'wsgi.run_once':     False,
        }
        environ.update(self.defaults)
        environ.update(request)
        return environ

    def request(self, **request):
        "Construct a generic request object."
        return WSGIRequest(self._base_environ(**request))

    def _encode_data(self, data, content_type, ):
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
        path = force_str(parsed[2])
        # If there are parameters, add them
        if parsed[3]:
            path += str(";") + force_str(parsed[3])
        path = unquote(path)
        # WSGI requires latin-1 encoded strings. See get_path_info().
        if six.PY3:
            path = path.encode('utf-8').decode('iso-8859-1')
        return path

    def get(self, path, data={}, **extra):
        "Construct a GET request."

        parsed = urlparse(path)
        r = {
            'CONTENT_TYPE':    str('text/html; charset=utf-8'),
            'PATH_INFO':       self._get_path(parsed),
            'QUERY_STRING':    urlencode(data, doseq=True) or force_str(parsed[4]),
            'REQUEST_METHOD':  str('GET'),
        }
        r.update(extra)
        return self.request(**r)

    def post(self, path, data={}, content_type=MULTIPART_CONTENT,
             **extra):
        "Construct a POST request."

        post_data = self._encode_data(data, content_type)

        parsed = urlparse(path)
        r = {
            'CONTENT_LENGTH': len(post_data),
            'CONTENT_TYPE':   content_type,
            'PATH_INFO':      self._get_path(parsed),
            'QUERY_STRING':   force_str(parsed[4]),
            'REQUEST_METHOD': str('POST'),
            'wsgi.input':     FakePayload(post_data),
        }
        r.update(extra)
        return self.request(**r)

    def head(self, path, data={}, **extra):
        "Construct a HEAD request."

        parsed = urlparse(path)
        r = {
            'CONTENT_TYPE':    str('text/html; charset=utf-8'),
            'PATH_INFO':       self._get_path(parsed),
            'QUERY_STRING':    urlencode(data, doseq=True) or force_str(parsed[4]),
            'REQUEST_METHOD':  str('HEAD'),
        }
        r.update(extra)
        return self.request(**r)

    def options(self, path, data='', content_type='application/octet-stream',
            **extra):
        "Construct an OPTIONS request."
        return self.generic('OPTIONS', path, data, content_type, **extra)

    def put(self, path, data='', content_type='application/octet-stream',
            **extra):
        "Construct a PUT request."
        return self.generic('PUT', path, data, content_type, **extra)

    def delete(self, path, data='', content_type='application/octet-stream',
            **extra):
        "Construct a DELETE request."
        return self.generic('DELETE', path, data, content_type, **extra)

    def generic(self, method, path,
                data='', content_type='application/octet-stream', **extra):
        parsed = urlparse(path)
        data = force_bytes(data, settings.DEFAULT_CHARSET)
        r = {
            'PATH_INFO':      self._get_path(parsed),
            'QUERY_STRING':   force_str(parsed[4]),
            'REQUEST_METHOD': str(method),
        }
        if data:
            r.update({
                'CONTENT_LENGTH': len(data),
                'CONTENT_TYPE':   str(content_type),
                'wsgi.input':     FakePayload(data),
            })
        r.update(extra)
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
        super(Client, self).__init__(**defaults)
        self.handler = ClientHandler(enforce_csrf_checks)
        self.exc_info = None

    def store_exc_info(self, **kwargs):
        """
        Stores exceptions when they are generated by a view.
        """
        self.exc_info = sys.exc_info()

    def _session(self):
        """
        Obtains the current session variables.
        """
        if 'django.contrib.sessions' in settings.INSTALLED_APPS:
            engine = import_module(settings.SESSION_ENGINE)
            cookie = self.cookies.get(settings.SESSION_COOKIE_NAME, None)
            if cookie:
                return engine.SessionStore(cookie.value)
        return {}
    session = property(_session)


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
        signals.template_rendered.connect(on_template_render, dispatch_uid="template-render")
        # Capture exceptions created by the handler.
        got_request_exception.connect(self.store_exc_info, dispatch_uid="request-exception")
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
                six.reraise(*exc_info)

            # Save the client and request that stimulated the response.
            response.client = self
            response.request = request

            # Add any rendered template detail to the response.
            response.templates = data.get("templates", [])
            response.context = data.get("context")

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
            signals.template_rendered.disconnect(dispatch_uid="template-render")
            got_request_exception.disconnect(dispatch_uid="request-exception")

    def get(self, path, data={}, follow=False, **extra):
        """
        Requests a response from the server using GET.
        """
        response = super(Client, self).get(path, data=data, **extra)
        if follow:
            response = self._handle_redirects(response, **extra)
        return response

    def post(self, path, data={}, content_type=MULTIPART_CONTENT,
             follow=False, **extra):
        """
        Requests a response from the server using POST.
        """
        response = super(Client, self).post(path, data=data, content_type=content_type, **extra)
        if follow:
            response = self._handle_redirects(response, **extra)
        return response

    def head(self, path, data={}, follow=False, **extra):
        """
        Request a response from the server using HEAD.
        """
        response = super(Client, self).head(path, data=data, **extra)
        if follow:
            response = self._handle_redirects(response, **extra)
        return response

    def options(self, path, data='', content_type='application/octet-stream',
            follow=False, **extra):
        """
        Request a response from the server using OPTIONS.
        """
        response = super(Client, self).options(path,
                data=data, content_type=content_type, **extra)
        if follow:
            response = self._handle_redirects(response, **extra)
        return response

    def put(self, path, data='', content_type='application/octet-stream',
            follow=False, **extra):
        """
        Send a resource to the server using PUT.
        """
        response = super(Client, self).put(path,
                data=data, content_type=content_type, **extra)
        if follow:
            response = self._handle_redirects(response, **extra)
        return response

    def delete(self, path, data='', content_type='application/octet-stream',
            follow=False, **extra):
        """
        Send a DELETE request to the server.
        """
        response = super(Client, self).delete(path,
                data=data, content_type=content_type, **extra)
        if follow:
            response = self._handle_redirects(response, **extra)
        return response

    def login(self, **credentials):
        """
        Sets the Factory to appear as if it has successfully logged into a site.

        Returns True if login is possible; False if the provided credentials
        are incorrect, or the user is inactive, or if the sessions framework is
        not available.
        """
        user = authenticate(**credentials)
        if user and user.is_active \
                and 'django.contrib.sessions' in settings.INSTALLED_APPS:
            engine = import_module(settings.SESSION_ENGINE)

            # Create a fake request to store login details.
            request = HttpRequest()
            if self.session:
                request.session = self.session
            else:
                request.session = engine.SessionStore()
            login(request, user)

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

            return True
        else:
            return False

    def logout(self):
        """
        Removes the authenticated user's cookies and session object.

        Causes the authenticated user to be logged out.
        """
        session = import_module(settings.SESSION_ENGINE).SessionStore()
        session_cookie = self.cookies.get(settings.SESSION_COOKIE_NAME)
        if session_cookie:
            session.delete(session_key=session_cookie.value)
        self.cookies = SimpleCookie()

    def _handle_redirects(self, response, **extra):
        "Follows any redirects by requesting responses from the server using GET."

        response.redirect_chain = []
        while response.status_code in (301, 302, 303, 307):
            url = response['Location']
            redirect_chain = response.redirect_chain
            redirect_chain.append((url, response.status_code))

            url = urlsplit(url)
            if url.scheme:
                extra['wsgi.url_scheme'] = url.scheme
            if url.hostname:
                extra['SERVER_NAME'] = url.hostname
            if url.port:
                extra['SERVER_PORT'] = str(url.port)

            response = self.get(url.path, QueryDict(url.query), follow=False, **extra)
            response.redirect_chain = redirect_chain

            # Prevent loops
            if response.redirect_chain[-1] in response.redirect_chain[0:-1]:
                break
        return response
