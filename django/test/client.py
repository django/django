import json
import mimetypes
import os
import sys
from collections.abc import Iterable
from copy import copy
from functools import partial
from http import HTTPStatus
from importlib import import_module
from io import BytesIO, IOBase
from urllib.parse import unquote_to_bytes, urljoin, urlsplit

from asgiref.sync import sync_to_async

from django.conf import settings
from django.core.handlers.asgi import ASGIRequest
from django.core.handlers.base import BaseHandler
from django.core.handlers.wsgi import LimitedStream, WSGIRequest
from django.core.serializers.json import DjangoJSONEncoder
from django.core.signals import got_request_exception, request_finished, request_started
from django.db import close_old_connections
from django.http import HttpHeaders, HttpRequest, QueryDict, SimpleCookie
from django.test import signals
from django.test.utils import ContextList
from django.urls import resolve
from django.utils.encoding import force_bytes
from django.utils.functional import SimpleLazyObject
from django.utils.http import urlencode
from django.utils.regex_helper import _lazy_re_compile

__all__ = (
    "AsyncClient",
    "AsyncRequestFactory",
    "Client",
    "RedirectCycleError",
    "RequestFactory",
    "encode_file",
    "encode_multipart",
)


BOUNDARY = "BoUnDaRyStRiNg"
MULTIPART_CONTENT = "multipart/form-data; boundary=%s" % BOUNDARY
CONTENT_TYPE_RE = _lazy_re_compile(r".*; charset=([\w-]+);?")
# Structured suffix spec: https://tools.ietf.org/html/rfc6838#section-4.2.8
JSON_CONTENT_TYPE_RE = _lazy_re_compile(r"^application\/(.+\+)?json")

REDIRECT_STATUS_CODES = frozenset(
    [
        HTTPStatus.MOVED_PERMANENTLY,
        HTTPStatus.FOUND,
        HTTPStatus.SEE_OTHER,
        HTTPStatus.TEMPORARY_REDIRECT,
        HTTPStatus.PERMANENT_REDIRECT,
    ]
)


class RedirectCycleError(Exception):
    """The test client has been asked to follow a redirect loop."""

    def __init__(self, message, last_response):
        super().__init__(message)
        self.last_response = last_response
        self.redirect_chain = last_response.redirect_chain


class FakePayload(IOBase):
    """
    A wrapper around BytesIO that restricts what can be read since data from
    the network can't be sought and cannot be read outside of its content
    length. This makes sure that views can't do anything under the test client
    that wouldn't work in real life.
    """

    def __init__(self, initial_bytes=None):
        self.__content = BytesIO()
        self.__len = 0
        self.read_started = False
        if initial_bytes is not None:
            self.write(initial_bytes)

    def __len__(self):
        return self.__len

    def read(self, size=-1, /):
        if not self.read_started:
            self.__content.seek(0)
            self.read_started = True
        if size == -1 or size is None:
            size = self.__len
        assert (
            self.__len >= size
        ), "Cannot read more than the available bytes from the HTTP incoming data."
        content = self.__content.read(size)
        self.__len -= len(content)
        return content

    def readline(self, size=-1, /):
        if not self.read_started:
            self.__content.seek(0)
            self.read_started = True
        if size == -1 or size is None:
            size = self.__len
        assert (
            self.__len >= size
        ), "Cannot read more than the available bytes from the HTTP incoming data."
        content = self.__content.readline(size)
        self.__len -= len(content)
        return content

    def write(self, b, /):
        if self.read_started:
            raise ValueError("Unable to write a payload after it's been read")
        content = force_bytes(b)
        self.__content.write(content)
        self.__len += len(content)


def closing_iterator_wrapper(iterable, close):
    try:
        yield from iterable
    finally:
        request_finished.disconnect(close_old_connections)
        close()  # will fire request_finished
        request_finished.connect(close_old_connections)


async def aclosing_iterator_wrapper(iterable, close):
    try:
        async for chunk in iterable:
            yield chunk
    finally:
        request_finished.disconnect(close_old_connections)
        close()  # will fire request_finished
        request_finished.connect(close_old_connections)


def conditional_content_removal(request, response):
    """
    Simulate the behavior of most web servers by removing the content of
    responses for HEAD requests, 1xx, 204, and 304 responses. Ensure
    compliance with RFC 9112 Section 6.3.
    """
    if 100 <= response.status_code < 200 or response.status_code in (204, 304):
        if response.streaming:
            response.streaming_content = []
        else:
            response.content = b""
    if request.method == "HEAD":
        if response.streaming:
            response.streaming_content = []
        else:
            response.content = b""
    return response


class ClientHandler(BaseHandler):
    """
    An HTTP Handler that can be used for testing purposes. Use the WSGI
    interface to compose requests, but return the raw HttpResponse object with
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

        # Simulate behaviors of most web servers.
        conditional_content_removal(request, response)

        # Attach the originating request to the response so that it could be
        # later retrieved.
        response.wsgi_request = request

        # Emulate a WSGI server by calling the close method on completion.
        if response.streaming:
            if response.is_async:
                response.streaming_content = aclosing_iterator_wrapper(
                    response.streaming_content, response.close
                )
            else:
                response.streaming_content = closing_iterator_wrapper(
                    response.streaming_content, response.close
                )
        else:
            request_finished.disconnect(close_old_connections)
            response.close()  # will fire request_finished
            request_finished.connect(close_old_connections)

        return response


class AsyncClientHandler(BaseHandler):
    """An async version of ClientHandler."""

    def __init__(self, enforce_csrf_checks=True, *args, **kwargs):
        self.enforce_csrf_checks = enforce_csrf_checks
        super().__init__(*args, **kwargs)

    async def __call__(self, scope):
        # Set up middleware if needed. We couldn't do this earlier, because
        # settings weren't available.
        if self._middleware_chain is None:
            self.load_middleware(is_async=True)
        # Extract body file from the scope, if provided.
        if "_body_file" in scope:
            body_file = scope.pop("_body_file")
        else:
            body_file = FakePayload("")

        request_started.disconnect(close_old_connections)
        await request_started.asend(sender=self.__class__, scope=scope)
        request_started.connect(close_old_connections)
        # Wrap FakePayload body_file to allow large read() in test environment.
        request = ASGIRequest(scope, LimitedStream(body_file, len(body_file)))
        # Sneaky little hack so that we can easily get round
        # CsrfViewMiddleware. This makes life easier, and is probably required
        # for backwards compatibility with external tests against admin views.
        request._dont_enforce_csrf_checks = not self.enforce_csrf_checks
        # Request goes through middleware.
        response = await self.get_response_async(request)
        # Simulate behaviors of most web servers.
        conditional_content_removal(request, response)
        # Attach the originating ASGI request to the response so that it could
        # be later retrieved.
        response.asgi_request = request
        # Emulate a server by calling the close method on completion.
        if response.streaming:
            if response.is_async:
                response.streaming_content = aclosing_iterator_wrapper(
                    response.streaming_content, response.close
                )
            else:
                response.streaming_content = closing_iterator_wrapper(
                    response.streaming_content, response.close
                )
        else:
            request_finished.disconnect(close_old_connections)
            # Will fire request_finished.
            await sync_to_async(response.close, thread_sensitive=False)()
            request_finished.connect(close_old_connections)
        return response


def store_rendered_templates(store, signal, sender, template, context, **kwargs):
    """
    Store templates and contexts that are rendered.

    The context is copied so that it is an accurate representation at the time
    of rendering.
    """
    store.setdefault("templates", []).append(template)
    if "context" not in store:
        store["context"] = ContextList()
    store["context"].append(copy(context))


def encode_multipart(boundary, data):
    """
    Encode multipart POST data from a dictionary of form values.

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
    for key, value in data.items():
        if value is None:
            raise TypeError(
                "Cannot encode None for key '%s' as POST data. Did you mean "
                "to pass an empty string or omit the value?" % key
            )
        elif is_file(value):
            lines.extend(encode_file(boundary, key, value))
        elif not isinstance(value, str) and isinstance(value, Iterable):
            for item in value:
                if is_file(item):
                    lines.extend(encode_file(boundary, key, item))
                else:
                    lines.extend(
                        to_bytes(val)
                        for val in [
                            "--%s" % boundary,
                            'Content-Disposition: form-data; name="%s"' % key,
                            "",
                            item,
                        ]
                    )
        else:
            lines.extend(
                to_bytes(val)
                for val in [
                    "--%s" % boundary,
                    'Content-Disposition: form-data; name="%s"' % key,
                    "",
                    value,
                ]
            )

    lines.extend(
        [
            to_bytes("--%s--" % boundary),
            b"",
        ]
    )
    return b"\r\n".join(lines)


def encode_file(boundary, key, file):
    def to_bytes(s):
        return force_bytes(s, settings.DEFAULT_CHARSET)

    # file.name might not be a string. For example, it's an int for
    # tempfile.TemporaryFile().
    file_has_string_name = hasattr(file, "name") and isinstance(file.name, str)
    filename = os.path.basename(file.name) if file_has_string_name else ""

    if hasattr(file, "content_type"):
        content_type = file.content_type
    elif filename:
        content_type = mimetypes.guess_type(filename)[0]
    else:
        content_type = None

    if content_type is None:
        content_type = "application/octet-stream"
    filename = filename or key
    return [
        to_bytes("--%s" % boundary),
        to_bytes(
            'Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename)
        ),
        to_bytes("Content-Type: %s" % content_type),
        b"",
        to_bytes(file.read()),
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

    def __init__(
        self,
        *,
        json_encoder=DjangoJSONEncoder,
        headers=None,
        query_params=None,
        **defaults,
    ):
        self.json_encoder = json_encoder
        self.defaults = defaults
        self.cookies = SimpleCookie()
        self.errors = BytesIO()
        if headers:
            self.defaults.update(HttpHeaders.to_wsgi_names(headers))
        if query_params:
            self.defaults["QUERY_STRING"] = urlencode(query_params, doseq=True)

    def _base_environ(self, **request):
        """
        The base environment for a request.
        """
        # This is a minimal valid WSGI environ dictionary, plus:
        # - HTTP_COOKIE: for cookie support,
        # - REMOTE_ADDR: often useful, see #8551.
        # See https://www.python.org/dev/peps/pep-3333/#environ-variables
        return {
            "HTTP_COOKIE": "; ".join(
                sorted(
                    "%s=%s" % (morsel.key, morsel.coded_value)
                    for morsel in self.cookies.values()
                )
            ),
            "PATH_INFO": "/",
            "REMOTE_ADDR": "127.0.0.1",
            "REQUEST_METHOD": "GET",
            "SCRIPT_NAME": "",
            "SERVER_NAME": "testserver",
            "SERVER_PORT": "80",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.input": FakePayload(b""),
            "wsgi.errors": self.errors,
            "wsgi.multiprocess": True,
            "wsgi.multithread": False,
            "wsgi.run_once": False,
            **self.defaults,
            **request,
        }

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
                charset = match[1]
            else:
                charset = settings.DEFAULT_CHARSET
            return force_bytes(data, encoding=charset)

    def _encode_json(self, data, content_type):
        """
        Return encoded JSON if data is a dict, list, or tuple and content_type
        is application/json.
        """
        should_encode = JSON_CONTENT_TYPE_RE.match(content_type) and isinstance(
            data, (dict, list, tuple)
        )
        return json.dumps(data, cls=self.json_encoder) if should_encode else data

    def _get_path(self, parsed):
        path = unquote_to_bytes(parsed.path)
        # Replace the behavior where non-ASCII values in the WSGI environ are
        # arbitrarily decoded with ISO-8859-1.
        # Refs comment in `get_bytes_from_wsgi()`.
        return path.decode("iso-8859-1")

    def get(
        self, path, data=None, secure=False, *, headers=None, query_params=None, **extra
    ):
        """Construct a GET request."""
        if query_params and data:
            raise ValueError("query_params and data arguments are mutually exclusive.")
        query_params = data or query_params
        query_params = {} if query_params is None else query_params
        return self.generic(
            "GET",
            path,
            secure=secure,
            headers=headers,
            query_params=query_params,
            **extra,
        )

    def post(
        self,
        path,
        data=None,
        content_type=MULTIPART_CONTENT,
        secure=False,
        *,
        headers=None,
        query_params=None,
        **extra,
    ):
        """Construct a POST request."""
        data = self._encode_json({} if data is None else data, content_type)
        post_data = self._encode_data(data, content_type)

        return self.generic(
            "POST",
            path,
            post_data,
            content_type,
            secure=secure,
            headers=headers,
            query_params=query_params,
            **extra,
        )

    def head(
        self, path, data=None, secure=False, *, headers=None, query_params=None, **extra
    ):
        """Construct a HEAD request."""
        if query_params and data:
            raise ValueError("query_params and data arguments are mutually exclusive.")
        query_params = data or query_params
        query_params = {} if query_params is None else query_params
        return self.generic(
            "HEAD",
            path,
            secure=secure,
            headers=headers,
            query_params=query_params,
            **extra,
        )

    def trace(self, path, secure=False, *, headers=None, query_params=None, **extra):
        """Construct a TRACE request."""
        return self.generic(
            "TRACE",
            path,
            secure=secure,
            headers=headers,
            query_params=query_params,
            **extra,
        )

    def options(
        self,
        path,
        data="",
        content_type="application/octet-stream",
        secure=False,
        *,
        headers=None,
        query_params=None,
        **extra,
    ):
        "Construct an OPTIONS request."
        return self.generic(
            "OPTIONS",
            path,
            data,
            content_type,
            secure=secure,
            headers=headers,
            query_params=query_params,
            **extra,
        )

    def put(
        self,
        path,
        data="",
        content_type="application/octet-stream",
        secure=False,
        *,
        headers=None,
        query_params=None,
        **extra,
    ):
        """Construct a PUT request."""
        data = self._encode_json(data, content_type)
        return self.generic(
            "PUT",
            path,
            data,
            content_type,
            secure=secure,
            headers=headers,
            query_params=query_params,
            **extra,
        )

    def patch(
        self,
        path,
        data="",
        content_type="application/octet-stream",
        secure=False,
        *,
        headers=None,
        query_params=None,
        **extra,
    ):
        """Construct a PATCH request."""
        data = self._encode_json(data, content_type)
        return self.generic(
            "PATCH",
            path,
            data,
            content_type,
            secure=secure,
            headers=headers,
            query_params=query_params,
            **extra,
        )

    def delete(
        self,
        path,
        data="",
        content_type="application/octet-stream",
        secure=False,
        *,
        headers=None,
        query_params=None,
        **extra,
    ):
        """Construct a DELETE request."""
        data = self._encode_json(data, content_type)
        return self.generic(
            "DELETE",
            path,
            data,
            content_type,
            secure=secure,
            headers=headers,
            query_params=query_params,
            **extra,
        )

    def generic(
        self,
        method,
        path,
        data="",
        content_type="application/octet-stream",
        secure=False,
        *,
        headers=None,
        query_params=None,
        **extra,
    ):
        """Construct an arbitrary HTTP request."""
        parsed = urlsplit(str(path))  # path can be lazy
        data = force_bytes(data, settings.DEFAULT_CHARSET)
        r = {
            "PATH_INFO": self._get_path(parsed),
            "REQUEST_METHOD": method,
            "SERVER_PORT": "443" if secure else "80",
            "wsgi.url_scheme": "https" if secure else "http",
        }
        if data:
            r.update(
                {
                    "CONTENT_LENGTH": str(len(data)),
                    "CONTENT_TYPE": content_type,
                    "wsgi.input": FakePayload(data),
                }
            )
        if headers:
            extra.update(HttpHeaders.to_wsgi_names(headers))
        if query_params:
            extra["QUERY_STRING"] = urlencode(query_params, doseq=True)
        r.update(extra)
        # If QUERY_STRING is absent or empty, we want to extract it from the URL.
        if not r.get("QUERY_STRING"):
            # WSGI requires latin-1 encoded strings. See get_path_info().
            r["QUERY_STRING"] = parsed.query.encode().decode("iso-8859-1")
        return self.request(**r)


class AsyncRequestFactory(RequestFactory):
    """
    Class that lets you create mock ASGI-like Request objects for use in
    testing. Usage:

    rf = AsyncRequestFactory()
    get_request = rf.get("/hello/")
    post_request = rf.post("/submit/", {"foo": "bar"})

    Once you have a request object you can pass it to any view function,
    including synchronous ones. The reason we have a separate class here is:
    a) this makes ASGIRequest subclasses, and
    b) AsyncClient can subclass it.
    """

    def _base_scope(self, **request):
        """The base scope for a request."""
        # This is a minimal valid ASGI scope, plus:
        # - headers['cookie'] for cookie support,
        # - 'client' often useful, see #8551.
        scope = {
            "asgi": {"version": "3.0"},
            "type": "http",
            "http_version": "1.1",
            "client": ["127.0.0.1", 0],
            "server": ("testserver", "80"),
            "scheme": "http",
            "method": "GET",
            "headers": [],
            **self.defaults,
            **request,
        }
        scope["headers"].append(
            (
                b"cookie",
                b"; ".join(
                    sorted(
                        ("%s=%s" % (morsel.key, morsel.coded_value)).encode("ascii")
                        for morsel in self.cookies.values()
                    )
                ),
            )
        )
        return scope

    def request(self, **request):
        """Construct a generic request object."""
        # This is synchronous, which means all methods on this class are.
        # AsyncClient, however, has an async request function, which makes all
        # its methods async.
        if "_body_file" in request:
            body_file = request.pop("_body_file")
        else:
            body_file = FakePayload("")
        # Wrap FakePayload body_file to allow large read() in test environment.
        return ASGIRequest(
            self._base_scope(**request), LimitedStream(body_file, len(body_file))
        )

    def generic(
        self,
        method,
        path,
        data="",
        content_type="application/octet-stream",
        secure=False,
        *,
        headers=None,
        query_params=None,
        **extra,
    ):
        """Construct an arbitrary HTTP request."""
        parsed = urlsplit(str(path))  # path can be lazy.
        data = force_bytes(data, settings.DEFAULT_CHARSET)
        s = {
            "method": method,
            "path": self._get_path(parsed),
            "server": ("127.0.0.1", "443" if secure else "80"),
            "scheme": "https" if secure else "http",
            "headers": [(b"host", b"testserver")],
        }
        if self.defaults:
            extra = {**self.defaults, **extra}
        if data:
            s["headers"].extend(
                [
                    (b"content-length", str(len(data)).encode("ascii")),
                    (b"content-type", content_type.encode("ascii")),
                ]
            )
            s["_body_file"] = FakePayload(data)
        if query_params:
            s["query_string"] = urlencode(query_params, doseq=True)
        elif query_string := extra.pop("QUERY_STRING", None):
            s["query_string"] = query_string
        else:
            # If QUERY_STRING is absent or empty, we want to extract it from
            # the URL.
            s["query_string"] = parsed.query
        if headers:
            extra.update(HttpHeaders.to_asgi_names(headers))
        s["headers"] += [
            (key.lower().encode("ascii"), value.encode("latin1"))
            for key, value in extra.items()
        ]
        return self.request(**s)


class ClientMixin:
    """
    Mixin with common methods between Client and AsyncClient.
    """

    def store_exc_info(self, **kwargs):
        """Store exceptions when they are generated by a view."""
        self.exc_info = sys.exc_info()

    def check_exception(self, response):
        """
        Look for a signaled exception, clear the current context exception
        data, re-raise the signaled exception, and clear the signaled exception
        from the local cache.
        """
        response.exc_info = self.exc_info
        if self.exc_info:
            _, exc_value, _ = self.exc_info
            self.exc_info = None
            if self.raise_request_exception:
                raise exc_value

    @property
    def session(self):
        """Return the current session variables."""
        engine = import_module(settings.SESSION_ENGINE)
        cookie = self.cookies.get(settings.SESSION_COOKIE_NAME)
        if cookie:
            return engine.SessionStore(cookie.value)
        session = engine.SessionStore()
        session.save()
        self.cookies[settings.SESSION_COOKIE_NAME] = session.session_key
        return session

    async def asession(self):
        engine = import_module(settings.SESSION_ENGINE)
        cookie = self.cookies.get(settings.SESSION_COOKIE_NAME)
        if cookie:
            return engine.SessionStore(cookie.value)
        session = engine.SessionStore()
        await session.asave()
        self.cookies[settings.SESSION_COOKIE_NAME] = session.session_key
        return session

    def login(self, **credentials):
        """
        Set the Factory to appear as if it has successfully logged into a site.

        Return True if login is possible or False if the provided credentials
        are incorrect.
        """
        from django.contrib.auth import authenticate

        user = authenticate(**credentials)
        if user:
            self._login(user)
            return True
        return False

    async def alogin(self, **credentials):
        """See login()."""
        from django.contrib.auth import aauthenticate

        user = await aauthenticate(**credentials)
        if user:
            await self._alogin(user)
            return True
        return False

    def force_login(self, user, backend=None):
        if backend is None:
            backend = self._get_backend()
        user.backend = backend
        self._login(user, backend)

    async def aforce_login(self, user, backend=None):
        if backend is None:
            backend = self._get_backend()
        user.backend = backend
        await self._alogin(user, backend)

    def _get_backend(self):
        from django.contrib.auth import load_backend

        for backend_path in settings.AUTHENTICATION_BACKENDS:
            backend = load_backend(backend_path)
            if hasattr(backend, "get_user"):
                return backend_path

    def _login(self, user, backend=None):
        from django.contrib.auth import login

        # Create a fake request to store login details.
        request = HttpRequest()
        if self.session:
            request.session = self.session
        else:
            engine = import_module(settings.SESSION_ENGINE)
            request.session = engine.SessionStore()
        login(request, user, backend)
        # Save the session values.
        request.session.save()
        self._set_login_cookies(request)

    async def _alogin(self, user, backend=None):
        from django.contrib.auth import alogin

        # Create a fake request to store login details.
        request = HttpRequest()
        session = await self.asession()
        if session:
            request.session = session
        else:
            engine = import_module(settings.SESSION_ENGINE)
            request.session = engine.SessionStore()

        await alogin(request, user, backend)
        # Save the session values.
        await request.session.asave()
        self._set_login_cookies(request)

    def _set_login_cookies(self, request):
        # Set the cookie to represent the session.
        session_cookie = settings.SESSION_COOKIE_NAME
        self.cookies[session_cookie] = request.session.session_key
        cookie_data = {
            "max-age": None,
            "path": "/",
            "domain": settings.SESSION_COOKIE_DOMAIN,
            "secure": settings.SESSION_COOKIE_SECURE or None,
            "expires": None,
        }
        self.cookies[session_cookie].update(cookie_data)

    def logout(self):
        """Log out the user by removing the cookies and session object."""
        from django.contrib.auth import get_user, logout

        request = HttpRequest()
        if self.session:
            request.session = self.session
            request.user = get_user(request)
        else:
            engine = import_module(settings.SESSION_ENGINE)
            request.session = engine.SessionStore()
        logout(request)
        self.cookies = SimpleCookie()

    async def alogout(self):
        """See logout()."""
        from django.contrib.auth import aget_user, alogout

        request = HttpRequest()
        session = await self.asession()
        if session:
            request.session = session
            request.user = await aget_user(request)
        else:
            engine = import_module(settings.SESSION_ENGINE)
            request.session = engine.SessionStore()
        await alogout(request)
        self.cookies = SimpleCookie()

    def _parse_json(self, response, **extra):
        if not hasattr(response, "_json"):
            if not JSON_CONTENT_TYPE_RE.match(response.get("Content-Type")):
                raise ValueError(
                    'Content-Type header is "%s", not "application/json"'
                    % response.get("Content-Type")
                )
            response._json = json.loads(response.text, **extra)
        return response._json

    def _follow_redirect(
        self,
        response,
        *,
        data="",
        content_type="",
        headers=None,
        query_params=None,
        **extra,
    ):
        """Follow a single redirect contained in response using GET."""
        response_url = response.url
        redirect_chain = response.redirect_chain
        redirect_chain.append((response_url, response.status_code))

        url = urlsplit(response_url)
        if url.scheme:
            extra["wsgi.url_scheme"] = url.scheme
        if url.hostname:
            extra["SERVER_NAME"] = url.hostname
            extra["HTTP_HOST"] = url.hostname
        if url.port:
            extra["SERVER_PORT"] = str(url.port)

        path = url.path
        # RFC 3986 Section 6.2.3: Empty path should be normalized to "/".
        if not path and url.netloc:
            path = "/"
        # Prepend the request path to handle relative path redirects
        if not path.startswith("/"):
            path = urljoin(response.request["PATH_INFO"], path)

        if response.status_code in (
            HTTPStatus.TEMPORARY_REDIRECT,
            HTTPStatus.PERMANENT_REDIRECT,
        ):
            # Preserve request method and query string (if needed)
            # post-redirect for 307/308 responses.
            request_method = response.request["REQUEST_METHOD"].lower()
            if request_method not in ("get", "head"):
                extra["QUERY_STRING"] = url.query
            request_method = getattr(self, request_method)
        else:
            request_method = self.get
            data = QueryDict(url.query)
            content_type = None

        return request_method(
            path,
            data=data,
            content_type=content_type,
            follow=False,
            headers=headers,
            query_params=query_params,
            **extra,
        )

    def _ensure_redirects_not_cyclic(self, response):
        """
        Raise a RedirectCycleError if response contains too many redirects.
        """
        redirect_chain = response.redirect_chain
        if redirect_chain[-1] in redirect_chain[:-1]:
            # Check that we're not redirecting to somewhere we've already been
            # to, to prevent loops.
            raise RedirectCycleError("Redirect loop detected.", last_response=response)
        if len(redirect_chain) > 20:
            # Such a lengthy chain likely also means a loop, but one with a
            # growing path, changing view, or changing query argument. 20 is
            # the value of "network.http.redirection-limit" from Firefox.
            raise RedirectCycleError("Too many redirects.", last_response=response)


class Client(ClientMixin, RequestFactory):
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

    def __init__(
        self,
        enforce_csrf_checks=False,
        raise_request_exception=True,
        *,
        headers=None,
        query_params=None,
        **defaults,
    ):
        super().__init__(headers=headers, query_params=query_params, **defaults)
        self.handler = ClientHandler(enforce_csrf_checks)
        self.raise_request_exception = raise_request_exception
        self.exc_info = None
        self.extra = None
        self.headers = None

    def request(self, **request):
        """
        Make a generic request. Compose the environment dictionary and pass
        to the handler, return the result of the handler. Assume defaults for
        the query environment, which can be overridden using the arguments to
        the request.
        """
        environ = self._base_environ(**request)

        # Curry a data dictionary into an instance of the template renderer
        # callback function.
        data = {}
        on_template_render = partial(store_rendered_templates, data)
        signal_uid = "template-render-%s" % id(request)
        signals.template_rendered.connect(on_template_render, dispatch_uid=signal_uid)
        # Capture exceptions created by the handler.
        exception_uid = "request-exception-%s" % id(request)
        got_request_exception.connect(self.store_exc_info, dispatch_uid=exception_uid)
        try:
            response = self.handler(environ)
        finally:
            signals.template_rendered.disconnect(dispatch_uid=signal_uid)
            got_request_exception.disconnect(dispatch_uid=exception_uid)
        # Check for signaled exceptions.
        self.check_exception(response)
        # Save the client and request that stimulated the response.
        response.client = self
        response.request = request
        # Add any rendered template detail to the response.
        response.templates = data.get("templates", [])
        response.context = data.get("context")
        response.json = partial(self._parse_json, response)
        # Attach the ResolverMatch instance to the response.
        urlconf = getattr(response.wsgi_request, "urlconf", None)
        response.resolver_match = SimpleLazyObject(
            lambda: resolve(request["PATH_INFO"], urlconf=urlconf),
        )
        # Flatten a single context. Not really necessary anymore thanks to the
        # __getattr__ flattening in ContextList, but has some edge case
        # backwards compatibility implications.
        if response.context and len(response.context) == 1:
            response.context = response.context[0]
        # Update persistent cookie data.
        if response.cookies:
            self.cookies.update(response.cookies)
        return response

    def get(
        self,
        path,
        data=None,
        follow=False,
        secure=False,
        *,
        headers=None,
        query_params=None,
        **extra,
    ):
        """Request a response from the server using GET."""
        self.extra = extra
        self.headers = headers
        response = super().get(
            path,
            data=data,
            secure=secure,
            headers=headers,
            query_params=query_params,
            **extra,
        )
        if follow:
            response = self._handle_redirects(
                response, data=data, headers=headers, query_params=query_params, **extra
            )
        return response

    def post(
        self,
        path,
        data=None,
        content_type=MULTIPART_CONTENT,
        follow=False,
        secure=False,
        *,
        headers=None,
        query_params=None,
        **extra,
    ):
        """Request a response from the server using POST."""
        self.extra = extra
        self.headers = headers
        response = super().post(
            path,
            data=data,
            content_type=content_type,
            secure=secure,
            headers=headers,
            query_params=query_params,
            **extra,
        )
        if follow:
            response = self._handle_redirects(
                response,
                data=data,
                content_type=content_type,
                headers=headers,
                query_params=query_params,
                **extra,
            )
        return response

    def head(
        self,
        path,
        data=None,
        follow=False,
        secure=False,
        *,
        headers=None,
        query_params=None,
        **extra,
    ):
        """Request a response from the server using HEAD."""
        self.extra = extra
        self.headers = headers
        response = super().head(
            path,
            data=data,
            secure=secure,
            headers=headers,
            query_params=query_params,
            **extra,
        )
        if follow:
            response = self._handle_redirects(
                response, data=data, headers=headers, query_params=query_params, **extra
            )
        return response

    def options(
        self,
        path,
        data="",
        content_type="application/octet-stream",
        follow=False,
        secure=False,
        *,
        headers=None,
        query_params=None,
        **extra,
    ):
        """Request a response from the server using OPTIONS."""
        self.extra = extra
        self.headers = headers
        response = super().options(
            path,
            data=data,
            content_type=content_type,
            secure=secure,
            headers=headers,
            query_params=query_params,
            **extra,
        )
        if follow:
            response = self._handle_redirects(
                response,
                data=data,
                content_type=content_type,
                headers=headers,
                query_params=query_params,
                **extra,
            )
        return response

    def put(
        self,
        path,
        data="",
        content_type="application/octet-stream",
        follow=False,
        secure=False,
        *,
        headers=None,
        query_params=None,
        **extra,
    ):
        """Send a resource to the server using PUT."""
        self.extra = extra
        self.headers = headers
        response = super().put(
            path,
            data=data,
            content_type=content_type,
            secure=secure,
            headers=headers,
            query_params=query_params,
            **extra,
        )
        if follow:
            response = self._handle_redirects(
                response,
                data=data,
                content_type=content_type,
                headers=headers,
                query_params=query_params,
                **extra,
            )
        return response

    def patch(
        self,
        path,
        data="",
        content_type="application/octet-stream",
        follow=False,
        secure=False,
        *,
        headers=None,
        query_params=None,
        **extra,
    ):
        """Send a resource to the server using PATCH."""
        self.extra = extra
        self.headers = headers
        response = super().patch(
            path,
            data=data,
            content_type=content_type,
            secure=secure,
            headers=headers,
            query_params=query_params,
            **extra,
        )
        if follow:
            response = self._handle_redirects(
                response,
                data=data,
                content_type=content_type,
                headers=headers,
                query_params=query_params,
                **extra,
            )
        return response

    def delete(
        self,
        path,
        data="",
        content_type="application/octet-stream",
        follow=False,
        secure=False,
        *,
        headers=None,
        query_params=None,
        **extra,
    ):
        """Send a DELETE request to the server."""
        self.extra = extra
        self.headers = headers
        response = super().delete(
            path,
            data=data,
            content_type=content_type,
            secure=secure,
            headers=headers,
            query_params=query_params,
            **extra,
        )
        if follow:
            response = self._handle_redirects(
                response,
                data=data,
                content_type=content_type,
                headers=headers,
                query_params=query_params,
                **extra,
            )
        return response

    def trace(
        self,
        path,
        data="",
        follow=False,
        secure=False,
        *,
        headers=None,
        query_params=None,
        **extra,
    ):
        """Send a TRACE request to the server."""
        self.extra = extra
        self.headers = headers
        response = super().trace(
            path,
            data=data,
            secure=secure,
            headers=headers,
            query_params=query_params,
            **extra,
        )
        if follow:
            response = self._handle_redirects(
                response, data=data, headers=headers, query_params=query_params, **extra
            )
        return response

    def _handle_redirects(
        self,
        response,
        data="",
        content_type="",
        headers=None,
        query_params=None,
        **extra,
    ):
        """
        Follow any redirects by requesting responses from the server using GET.
        """
        response.redirect_chain = []
        while response.status_code in REDIRECT_STATUS_CODES:
            redirect_chain = response.redirect_chain
            response = self._follow_redirect(
                response,
                data=data,
                content_type=content_type,
                headers=headers,
                query_params=query_params,
                **extra,
            )
            response.redirect_chain = redirect_chain
            self._ensure_redirects_not_cyclic(response)
        return response


class AsyncClient(ClientMixin, AsyncRequestFactory):
    """
    An async version of Client that creates ASGIRequests and calls through an
    async request path.

    Does not currently support "follow" on its methods.
    """

    def __init__(
        self,
        enforce_csrf_checks=False,
        raise_request_exception=True,
        *,
        headers=None,
        query_params=None,
        **defaults,
    ):
        super().__init__(headers=headers, query_params=query_params, **defaults)
        self.handler = AsyncClientHandler(enforce_csrf_checks)
        self.raise_request_exception = raise_request_exception
        self.exc_info = None
        self.extra = None
        self.headers = None

    async def request(self, **request):
        """
        Make a generic request. Compose the scope dictionary and pass to the
        handler, return the result of the handler. Assume defaults for the
        query environment, which can be overridden using the arguments to the
        request.
        """
        scope = self._base_scope(**request)
        # Curry a data dictionary into an instance of the template renderer
        # callback function.
        data = {}
        on_template_render = partial(store_rendered_templates, data)
        signal_uid = "template-render-%s" % id(request)
        signals.template_rendered.connect(on_template_render, dispatch_uid=signal_uid)
        # Capture exceptions created by the handler.
        exception_uid = "request-exception-%s" % id(request)
        got_request_exception.connect(self.store_exc_info, dispatch_uid=exception_uid)
        try:
            response = await self.handler(scope)
        finally:
            signals.template_rendered.disconnect(dispatch_uid=signal_uid)
            got_request_exception.disconnect(dispatch_uid=exception_uid)
        # Check for signaled exceptions.
        self.check_exception(response)
        # Save the client and request that stimulated the response.
        response.client = self
        response.request = request
        # Add any rendered template detail to the response.
        response.templates = data.get("templates", [])
        response.context = data.get("context")
        response.json = partial(self._parse_json, response)
        # Attach the ResolverMatch instance to the response.
        urlconf = getattr(response.asgi_request, "urlconf", None)
        response.resolver_match = SimpleLazyObject(
            lambda: resolve(request["path"], urlconf=urlconf),
        )
        # Flatten a single context. Not really necessary anymore thanks to the
        # __getattr__ flattening in ContextList, but has some edge case
        # backwards compatibility implications.
        if response.context and len(response.context) == 1:
            response.context = response.context[0]
        # Update persistent cookie data.
        if response.cookies:
            self.cookies.update(response.cookies)
        return response

    async def get(
        self,
        path,
        data=None,
        follow=False,
        secure=False,
        *,
        headers=None,
        query_params=None,
        **extra,
    ):
        """Request a response from the server using GET."""
        self.extra = extra
        self.headers = headers
        response = await super().get(
            path,
            data=data,
            secure=secure,
            headers=headers,
            query_params=query_params,
            **extra,
        )
        if follow:
            response = await self._ahandle_redirects(
                response, data=data, headers=headers, query_params=query_params, **extra
            )
        return response

    async def post(
        self,
        path,
        data=None,
        content_type=MULTIPART_CONTENT,
        follow=False,
        secure=False,
        *,
        headers=None,
        query_params=None,
        **extra,
    ):
        """Request a response from the server using POST."""
        self.extra = extra
        self.headers = headers
        response = await super().post(
            path,
            data=data,
            content_type=content_type,
            secure=secure,
            headers=headers,
            query_params=query_params,
            **extra,
        )
        if follow:
            response = await self._ahandle_redirects(
                response,
                data=data,
                content_type=content_type,
                headers=headers,
                query_params=query_params,
                **extra,
            )
        return response

    async def head(
        self,
        path,
        data=None,
        follow=False,
        secure=False,
        *,
        headers=None,
        query_params=None,
        **extra,
    ):
        """Request a response from the server using HEAD."""
        self.extra = extra
        self.headers = headers
        response = await super().head(
            path,
            data=data,
            secure=secure,
            headers=headers,
            query_params=query_params,
            **extra,
        )
        if follow:
            response = await self._ahandle_redirects(
                response, data=data, headers=headers, query_params=query_params, **extra
            )
        return response

    async def options(
        self,
        path,
        data="",
        content_type="application/octet-stream",
        follow=False,
        secure=False,
        *,
        headers=None,
        query_params=None,
        **extra,
    ):
        """Request a response from the server using OPTIONS."""
        self.extra = extra
        self.headers = headers
        response = await super().options(
            path,
            data=data,
            content_type=content_type,
            secure=secure,
            headers=headers,
            query_params=query_params,
            **extra,
        )
        if follow:
            response = await self._ahandle_redirects(
                response,
                data=data,
                content_type=content_type,
                headers=headers,
                query_params=query_params,
                **extra,
            )
        return response

    async def put(
        self,
        path,
        data="",
        content_type="application/octet-stream",
        follow=False,
        secure=False,
        *,
        headers=None,
        query_params=None,
        **extra,
    ):
        """Send a resource to the server using PUT."""
        self.extra = extra
        self.headers = headers
        response = await super().put(
            path,
            data=data,
            content_type=content_type,
            secure=secure,
            headers=headers,
            query_params=query_params,
            **extra,
        )
        if follow:
            response = await self._ahandle_redirects(
                response,
                data=data,
                content_type=content_type,
                headers=headers,
                query_params=query_params,
                **extra,
            )
        return response

    async def patch(
        self,
        path,
        data="",
        content_type="application/octet-stream",
        follow=False,
        secure=False,
        *,
        headers=None,
        query_params=None,
        **extra,
    ):
        """Send a resource to the server using PATCH."""
        self.extra = extra
        self.headers = headers
        response = await super().patch(
            path,
            data=data,
            content_type=content_type,
            secure=secure,
            headers=headers,
            query_params=query_params,
            **extra,
        )
        if follow:
            response = await self._ahandle_redirects(
                response,
                data=data,
                content_type=content_type,
                headers=headers,
                query_params=query_params,
                **extra,
            )
        return response

    async def delete(
        self,
        path,
        data="",
        content_type="application/octet-stream",
        follow=False,
        secure=False,
        *,
        headers=None,
        query_params=None,
        **extra,
    ):
        """Send a DELETE request to the server."""
        self.extra = extra
        self.headers = headers
        response = await super().delete(
            path,
            data=data,
            content_type=content_type,
            secure=secure,
            headers=headers,
            query_params=query_params,
            **extra,
        )
        if follow:
            response = await self._ahandle_redirects(
                response,
                data=data,
                content_type=content_type,
                headers=headers,
                query_params=query_params,
                **extra,
            )
        return response

    async def trace(
        self,
        path,
        data="",
        follow=False,
        secure=False,
        *,
        headers=None,
        query_params=None,
        **extra,
    ):
        """Send a TRACE request to the server."""
        self.extra = extra
        self.headers = headers
        response = await super().trace(
            path,
            data=data,
            secure=secure,
            headers=headers,
            query_params=query_params,
            **extra,
        )
        if follow:
            response = await self._ahandle_redirects(
                response, data=data, headers=headers, query_params=query_params, **extra
            )
        return response

    async def _ahandle_redirects(
        self,
        response,
        data="",
        content_type="",
        headers=None,
        query_params=None,
        **extra,
    ):
        """
        Follow any redirects by requesting responses from the server using GET.
        """
        response.redirect_chain = []
        while response.status_code in REDIRECT_STATUS_CODES:
            redirect_chain = response.redirect_chain
            response = await self._follow_redirect(
                response,
                data=data,
                content_type=content_type,
                headers=headers,
                query_params=query_params,
                **extra,
            )
            response.redirect_chain = redirect_chain
            self._ensure_redirects_not_cyclic(response)
        return response
