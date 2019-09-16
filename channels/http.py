import cgi
import codecs
import logging
import sys
import tempfile
import traceback

from django import http
from django.conf import settings
from django.core import signals
from django.core.exceptions import RequestDataTooBig
from django.core.handlers import base
from django.http import FileResponse, HttpResponse, HttpResponseServerError
from django.urls import set_script_prefix
from django.utils.functional import cached_property

from asgiref.sync import async_to_sync, sync_to_async
from channels.exceptions import RequestAborted, RequestTimeout

logger = logging.getLogger("django.request")


class AsgiRequest(http.HttpRequest):
    """
    Custom request subclass that decodes from an ASGI-standard request
    dict, and wraps request body handling.
    """

    # Number of seconds until a Request gives up on trying to read a request
    # body and aborts.
    body_receive_timeout = 60

    def __init__(self, scope, stream):
        self.scope = scope
        self._content_length = 0
        self._post_parse_error = False
        self._read_started = False
        self.resolver_match = None
        self.script_name = self.scope.get("root_path", "")
        if self.script_name and scope["path"].startswith(self.script_name):
            # TODO: Better is-prefix checking, slash handling?
            self.path_info = scope["path"][len(self.script_name) :]
        else:
            self.path_info = scope["path"]

        # django path is different from asgi scope path args, it should combine with script name
        if self.script_name:
            self.path = "%s/%s" % (
                self.script_name.rstrip("/"),
                self.path_info.replace("/", "", 1),
            )
        else:
            self.path = scope["path"]

        # HTTP basics
        self.method = self.scope["method"].upper()
        # fix https://github.com/django/channels/issues/622
        query_string = self.scope.get("query_string", "")
        if isinstance(query_string, bytes):
            query_string = query_string.decode("utf-8")
        self.META = {
            "REQUEST_METHOD": self.method,
            "QUERY_STRING": query_string,
            "SCRIPT_NAME": self.script_name,
            "PATH_INFO": self.path_info,
            # Old code will need these for a while
            "wsgi.multithread": True,
            "wsgi.multiprocess": True,
        }
        if self.scope.get("client", None):
            self.META["REMOTE_ADDR"] = self.scope["client"][0]
            self.META["REMOTE_HOST"] = self.META["REMOTE_ADDR"]
            self.META["REMOTE_PORT"] = self.scope["client"][1]
        if self.scope.get("server", None):
            self.META["SERVER_NAME"] = self.scope["server"][0]
            self.META["SERVER_PORT"] = str(self.scope["server"][1])
        else:
            self.META["SERVER_NAME"] = "unknown"
            self.META["SERVER_PORT"] = "0"
        # Handle old style-headers for a transition period
        if "headers" in self.scope and isinstance(self.scope["headers"], dict):
            self.scope["headers"] = [
                (x.encode("latin1"), y) for x, y in self.scope["headers"].items()
            ]
        # Headers go into META
        for name, value in self.scope.get("headers", []):
            name = name.decode("latin1")
            if name == "content-length":
                corrected_name = "CONTENT_LENGTH"
            elif name == "content-type":
                corrected_name = "CONTENT_TYPE"
            else:
                corrected_name = "HTTP_%s" % name.upper().replace("-", "_")
            # HTTPbis say only ASCII chars are allowed in headers, but we latin1 just in case
            value = value.decode("latin1")
            if corrected_name in self.META:
                value = self.META[corrected_name] + "," + value
            self.META[corrected_name] = value
        # Pull out request encoding if we find it
        if "CONTENT_TYPE" in self.META:
            self.content_type, self.content_params = cgi.parse_header(
                self.META["CONTENT_TYPE"]
            )
            if "charset" in self.content_params:
                try:
                    codecs.lookup(self.content_params["charset"])
                except LookupError:
                    pass
                else:
                    self.encoding = self.content_params["charset"]
        else:
            self.content_type, self.content_params = "", {}
        # Pull out content length info
        if self.META.get("CONTENT_LENGTH", None):
            try:
                self._content_length = int(self.META["CONTENT_LENGTH"])
            except (ValueError, TypeError):
                pass
        # Body handling
        self._stream = stream
        # Other bits
        self.resolver_match = None

    @cached_property
    def GET(self):
        return http.QueryDict(self.scope.get("query_string", ""))

    def _get_scheme(self):
        return self.scope.get("scheme", "http")

    def _get_post(self):
        if not hasattr(self, "_post"):
            self._load_post_and_files()
        return self._post

    def _set_post(self, post):
        self._post = post

    def _get_files(self):
        if not hasattr(self, "_files"):
            self._load_post_and_files()
        return self._files

    POST = property(_get_post, _set_post)
    FILES = property(_get_files)

    @cached_property
    def COOKIES(self):
        return http.parse_cookie(self.META.get("HTTP_COOKIE", ""))


class AsgiHandler(base.BaseHandler):
    """
    Handler for ASGI requests for the view system only (it will have got here
    after traversing the dispatch-by-channel-name system, which decides it's
    a HTTP request)

    You can also manually construct it with a get_response callback if you
    want to run a single Django view yourself. If you do this, though, it will
    not do any URL routing or middleware (Channels uses it for staticfiles'
    serving code)
    """

    request_class = AsgiRequest

    # Size to chunk response bodies into for multiple response messages
    chunk_size = 512 * 1024

    def __init__(self, scope):
        if scope["type"] != "http":
            raise ValueError(
                "The AsgiHandler can only handle HTTP connections, not %s"
                % scope["type"]
            )
        super(AsgiHandler, self).__init__()
        self.scope = scope
        self.load_middleware()

    async def __call__(self, receive, send):
        """
        Async entrypoint - uses the sync_to_async wrapper to run things in a
        threadpool.
        """
        self.send = async_to_sync(send)

        # Receive the HTTP request body as a stream object.
        try:
            body_stream = await self.read_body(receive)
        except RequestAborted:
            return
        # Launch into body handling (and a synchronous subthread).
        await self.handle(body_stream)

    async def read_body(self, receive):
        """Reads a HTTP body from an ASGI connection."""
        # Use the tempfile that auto rolls-over to a disk file as it fills up.
        body_file = tempfile.SpooledTemporaryFile(
            max_size=settings.FILE_UPLOAD_MAX_MEMORY_SIZE, mode="w+b"
        )
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                # Early client disconnect.
                raise RequestAborted()
            # Add a body chunk from the message, if provided.
            if "body" in message:
                body_file.write(message["body"])
            # Quit out if that's the end.
            if not message.get("more_body", False):
                break
        body_file.seek(0)
        return body_file

    @sync_to_async
    def handle(self, body):
        """
        Synchronous message processing.
        """
        # Set script prefix from message root_path, turning None into empty string
        script_prefix = self.scope.get("root_path", "") or ""
        if settings.FORCE_SCRIPT_NAME:
            script_prefix = settings.FORCE_SCRIPT_NAME
        set_script_prefix(script_prefix)
        signals.request_started.send(sender=self.__class__, scope=self.scope)
        # Run request through view system
        try:
            request = self.request_class(self.scope, body)
        except UnicodeDecodeError:
            logger.warning(
                "Bad Request (UnicodeDecodeError)",
                exc_info=sys.exc_info(),
                extra={"status_code": 400},
            )
            response = http.HttpResponseBadRequest()
        except RequestTimeout:
            # Parsing the request failed, so the response is a Request Timeout error
            response = HttpResponse("408 Request Timeout (upload too slow)", status=408)
        except RequestAborted:
            # Client closed connection on us mid request. Abort!
            return
        except RequestDataTooBig:
            response = HttpResponse("413 Payload too large", status=413)
        else:
            response = self.get_response(request)
            # Fix chunk size on file responses
            if isinstance(response, FileResponse):
                response.block_size = 1024 * 512
        # Transform response into messages, which we yield back to caller
        for response_message in self.encode_response(response):
            self.send(response_message)
        # Close the response now we're done with it
        response.close()

    def handle_uncaught_exception(self, request, resolver, exc_info):
        """
        Last-chance handler for exceptions.
        """
        # There's no WSGI server to catch the exception further up if this fails,
        # so translate it into a plain text response.
        try:
            return super(AsgiHandler, self).handle_uncaught_exception(
                request, resolver, exc_info
            )
        except Exception:
            return HttpResponseServerError(
                traceback.format_exc() if settings.DEBUG else "Internal Server Error",
                content_type="text/plain",
            )

    def load_middleware(self):
        """
        Loads the Django middleware chain and caches it on the class.
        """
        # Because we create an AsgiHandler on every HTTP request
        # we need to preserve the Django middleware chain once we load it.
        if (
            hasattr(self.__class__, "_middleware_chain")
            and self.__class__._middleware_chain
        ):
            self._middleware_chain = self.__class__._middleware_chain
            self._view_middleware = self.__class__._view_middleware
            self._template_response_middleware = (
                self.__class__._template_response_middleware
            )
            self._exception_middleware = self.__class__._exception_middleware

            # Support additional arguments for Django 1.11 and 2.0.
            if hasattr(self.__class__, "_request_middleware"):
                self._request_middleware = self.__class__._request_middleware
                self._response_middleware = self.__class__._response_middleware

        else:
            super(AsgiHandler, self).load_middleware()
            self.__class__._middleware_chain = self._middleware_chain
            self.__class__._view_middleware = self._view_middleware
            self.__class__._template_response_middleware = (
                self._template_response_middleware
            )
            self.__class__._exception_middleware = self._exception_middleware

            # Support additional arguments for Django 1.11 and 2.0.
            if hasattr(self, "_request_middleware"):
                self.__class__._request_middleware = self._request_middleware
                self.__class__._response_middleware = self._response_middleware

    @classmethod
    def encode_response(cls, response):
        """
        Encodes a Django HTTP response into ASGI http.response message(s).
        """
        # Collect cookies into headers.
        # Note that we have to preserve header case as there are some non-RFC
        # compliant clients that want things like Content-Type correct. Ugh.
        response_headers = []
        for header, value in response.items():
            if isinstance(header, str):
                header = header.encode("ascii")
            if isinstance(value, str):
                value = value.encode("latin1")
            response_headers.append((bytes(header), bytes(value)))
        for c in response.cookies.values():
            response_headers.append(
                (b"Set-Cookie", c.output(header="").encode("ascii").strip())
            )
        # Make initial response message
        yield {
            "type": "http.response.start",
            "status": response.status_code,
            "headers": response_headers,
        }
        # Streaming responses need to be pinned to their iterator
        if response.streaming:
            # Access `__iter__` and not `streaming_content` directly in case
            # it has been overridden in a subclass.
            for part in response:
                for chunk, _ in cls.chunk_bytes(part):
                    yield {
                        "type": "http.response.body",
                        "body": chunk,
                        # We ignore "more" as there may be more parts; instead,
                        # we use an empty final closing message with False.
                        "more_body": True,
                    }
            # Final closing message
            yield {"type": "http.response.body"}
        # Other responses just need chunking
        else:
            # Yield chunks of response
            for chunk, last in cls.chunk_bytes(response.content):
                yield {
                    "type": "http.response.body",
                    "body": chunk,
                    "more_body": not last,
                }

    @classmethod
    def chunk_bytes(cls, data):
        """
        Chunks some data up so it can be sent in reasonable size messages.
        Yields (chunk, last_chunk) tuples.
        """
        position = 0
        if not data:
            yield data, True
            return
        while position < len(data):
            yield (
                data[position : position + cls.chunk_size],
                (position + cls.chunk_size) >= len(data),
            )
            position += cls.chunk_size
