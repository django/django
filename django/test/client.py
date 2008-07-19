import urllib
import sys
import os
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.core.handlers.base import BaseHandler
from django.core.handlers.wsgi import WSGIRequest
from django.core.signals import got_request_exception
from django.dispatch import dispatcher
from django.http import SimpleCookie, HttpRequest
from django.template import TemplateDoesNotExist
from django.test import signals
from django.utils.functional import curry
from django.utils.encoding import smart_str
from django.utils.http import urlencode
from django.utils.itercompat import is_iterable

BOUNDARY = 'BoUnDaRyStRiNg'
MULTIPART_CONTENT = 'multipart/form-data; boundary=%s' % BOUNDARY


class FakePayload(object):
    """
    A wrapper around StringIO that restricts what can be read since data from
    the network can't be seeked and cannot be read outside of its content
    length. This makes sure that views can't do anything under the test client
    that wouldn't work in Real Life.
    """
    def __init__(self, content):
        self.__content = StringIO(content)
        self.__len = len(content)

    def read(self, num_bytes=None):
        if num_bytes is None:
            num_bytes = self.__len or 1
        assert self.__len >= num_bytes, "Cannot read more than the available bytes from the HTTP incoming data."
        content = self.__content.read(num_bytes)
        self.__len -= num_bytes
        return content


class ClientHandler(BaseHandler):
    """
    A HTTP Handler that can be used for testing purposes.
    Uses the WSGI interface to compose requests, but returns
    the raw HttpResponse object
    """
    def __call__(self, environ):
        from django.conf import settings
        from django.core import signals

        # Set up middleware if needed. We couldn't do this earlier, because
        # settings weren't available.
        if self._request_middleware is None:
            self.load_middleware()

        dispatcher.send(signal=signals.request_started)
        try:
            request = WSGIRequest(environ)
            response = self.get_response(request)

            # Apply response middleware.
            for middleware_method in self._response_middleware:
                response = middleware_method(request, response)
            response = self.apply_response_fixes(request, response)
        finally:
            dispatcher.send(signal=signals.request_finished)

        return response

def store_rendered_templates(store, signal, sender, template, context):
    """
    Stores templates and contexts that are rendered.
    """
    store.setdefault('template',[]).append(template)
    store.setdefault('context',[]).append(context)

def encode_multipart(boundary, data):
    """
    Encodes multipart POST data from a dictionary of form values.

    The key will be used as the form data name; the value will be transmitted
    as content. If the value is a file, the contents of the file will be sent
    as an application/octet-stream; otherwise, str(value) will be sent.
    """
    lines = []
    to_str = lambda s: smart_str(s, settings.DEFAULT_CHARSET)

    # Not by any means perfect, but good enough for our purposes.
    is_file = lambda thing: hasattr(thing, "read") and callable(thing.read)

    # Each bit of the multipart form data could be either a form value or a
    # file, or a *list* of form values and/or files. Remember that HTTP field
    # names can be duplicated!
    for (key, value) in data.items():
        if is_file(value):
            lines.extend(encode_file(boundary, key, value))
        elif not isinstance(value, basestring) and is_iterable(value):
            for item in value:
                if is_file(item):
                    lines.extend(encode_file(boundary, key, item))
                else:
                    lines.extend([
                        '--' + boundary,
                        'Content-Disposition: form-data; name="%s"' % to_str(key),
                        '',
                        to_str(item)
                    ])
        else:
            lines.extend([
                '--' + boundary,
                'Content-Disposition: form-data; name="%s"' % to_str(key),
                '',
                to_str(value)
            ])

    lines.extend([
        '--' + boundary + '--',
        '',
    ])
    return '\r\n'.join(lines)

def encode_file(boundary, key, file):
    to_str = lambda s: smart_str(s, settings.DEFAULT_CHARSET)
    return [
        '--' + boundary,
        'Content-Disposition: form-data; name="%s"; filename="%s"' \
            % (to_str(key), to_str(os.path.basename(file.name))),
        'Content-Type: application/octet-stream',
        '',
        file.read()
    ]
    
class Client:
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
    def __init__(self, **defaults):
        self.handler = ClientHandler()
        self.defaults = defaults
        self.cookies = SimpleCookie()
        self.exc_info = None

    def store_exc_info(self, *args, **kwargs):
        """
        Stores exceptions when they are generated by a view.
        """
        self.exc_info = sys.exc_info()

    def _session(self):
        """
        Obtains the current session variables.
        """
        if 'django.contrib.sessions' in settings.INSTALLED_APPS:
            engine = __import__(settings.SESSION_ENGINE, {}, {}, [''])
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
        environ = {
            'HTTP_COOKIE':      self.cookies,
            'PATH_INFO':         '/',
            'QUERY_STRING':      '',
            'REQUEST_METHOD':    'GET',
            'SCRIPT_NAME':       None,
            'SERVER_NAME':       'testserver',
            'SERVER_PORT':       80,
            'SERVER_PROTOCOL':   'HTTP/1.1',
        }
        environ.update(self.defaults)
        environ.update(request)

        # Curry a data dictionary into an instance of the template renderer
        # callback function.
        data = {}
        on_template_render = curry(store_rendered_templates, data)
        dispatcher.connect(on_template_render, signal=signals.template_rendered)

        # Capture exceptions created by the handler.
        dispatcher.connect(self.store_exc_info, signal=got_request_exception)

        try:
            response = self.handler(environ)
        except TemplateDoesNotExist, e:
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
            raise exc_info[1], None, exc_info[2]

        # Save the client and request that stimulated the response.
        response.client = self
        response.request = request

        # Add any rendered template detail to the response.
        # If there was only one template rendered (the most likely case),
        # flatten the list to a single element.
        for detail in ('template', 'context'):
            if data.get(detail):
                if len(data[detail]) == 1:
                    setattr(response, detail, data[detail][0]);
                else:
                    setattr(response, detail, data[detail])
            else:
                setattr(response, detail, None)

        # Update persistent cookie data.
        if response.cookies:
            self.cookies.update(response.cookies)

        return response

    def get(self, path, data={}, **extra):
        """
        Requests a response from the server using GET.
        """
        r = {
            'CONTENT_LENGTH':  None,
            'CONTENT_TYPE':    'text/html; charset=utf-8',
            'PATH_INFO':       urllib.unquote(path),
            'QUERY_STRING':    urlencode(data, doseq=True),
            'REQUEST_METHOD': 'GET',
        }
        r.update(extra)

        return self.request(**r)

    def post(self, path, data={}, content_type=MULTIPART_CONTENT, **extra):
        """
        Requests a response from the server using POST.
        """
        if content_type is MULTIPART_CONTENT:
            post_data = encode_multipart(BOUNDARY, data)
        else:
            post_data = data

        r = {
            'CONTENT_LENGTH': len(post_data),
            'CONTENT_TYPE':   content_type,
            'PATH_INFO':      urllib.unquote(path),
            'REQUEST_METHOD': 'POST',
            'wsgi.input':     FakePayload(post_data),
        }
        r.update(extra)

        return self.request(**r)

    def login(self, **credentials):
        """
        Sets the Client to appear as if it has successfully logged into a site.

        Returns True if login is possible; False if the provided credentials
        are incorrect, or the user is inactive, or if the sessions framework is
        not available.
        """
        user = authenticate(**credentials)
        if user and user.is_active \
                and 'django.contrib.sessions' in settings.INSTALLED_APPS:
            engine = __import__(settings.SESSION_ENGINE, {}, {}, [''])

            # Create a fake request to store login details.
            request = HttpRequest()
            request.session = engine.SessionStore()
            login(request, user)

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

            # Save the session values.
            request.session.save()

            return True
        else:
            return False

    def logout(self):
        """
        Removes the authenticated user's cookies.

        Causes the authenticated user to be logged out.
        """
        session = __import__(settings.SESSION_ENGINE, {}, {}, ['']).SessionStore()
        session.delete(session_key=self.cookies[settings.SESSION_COOKIE_NAME].value)
        self.cookies = SimpleCookie()
