import asyncio
import logging
import sys
import tempfile
import traceback
from contextlib import aclosing

from asgiref.sync import ThreadSensitiveContext, sync_to_async

from django.conf import settings
from django.core import signals
from django.core.exceptions import RequestAborted, RequestDataTooBig
from django.core.handlers import base
from django.http import (
    FileResponse,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseServerError,
    QueryDict,
    parse_cookie,
)
from django.urls import set_script_prefix
from django.utils.functional import cached_property

logger = logging.getLogger("django.request")


def get_script_prefix(scope):
    """
    Return the script prefix to use from either the scope or a setting.
    """
    if settings.FORCE_SCRIPT_NAME:
        return settings.FORCE_SCRIPT_NAME
    return scope.get("root_path", "") or ""


class ASGIRequest(HttpRequest):
    """
    Custom request subclass that decodes from an ASGI-standard request dict
    and wraps request body handling.
    """

    # Number of seconds until a Request gives up on trying to read a request
    # body and aborts.
    body_receive_timeout = 60

    def __init__(self, scope, body_file):
        self.scope = scope
        self._post_parse_error = False
        self._read_started = False
        self.resolver_match = None
        self.script_name = get_script_prefix(scope)
        if self.script_name:
            # TODO: Better is-prefix checking, slash handling?
            self.path_info = scope["path"].removeprefix(self.script_name)
        else:
            self.path_info = scope["path"]
        # The Django path is different from ASGI scope path args, it should
        # combine with script name.
        if self.script_name:
            self.path = "%s/%s" % (
                self.script_name.rstrip("/"),
                self.path_info.replace("/", "", 1),
            )
        else:
            self.path = scope["path"]
        # HTTP basics.
        self.method = self.scope["method"].upper()
        # Ensure query string is encoded correctly.
        query_string = self.scope.get("query_string", "")
        if isinstance(query_string, bytes):
            query_string = query_string.decode()
        self.META = {
            "REQUEST_METHOD": self.method,
            "QUERY_STRING": query_string,
            "SCRIPT_NAME": self.script_name,
            "PATH_INFO": self.path_info,
            # WSGI-expecting code will need these for a while
            "wsgi.multithread": True,
            "wsgi.multiprocess": True,
        }
        if self.scope.get("client"):
            self.META["REMOTE_ADDR"] = self.scope["client"][0]
            self.META["REMOTE_HOST"] = self.META["REMOTE_ADDR"]
            self.META["REMOTE_PORT"] = self.scope["client"][1]
        if self.scope.get("server"):
            self.META["SERVER_NAME"] = self.scope["server"][0]
            self.META["SERVER_PORT"] = str(self.scope["server"][1])
        else:
            self.META["SERVER_NAME"] = "unknown"
            self.META["SERVER_PORT"] = "0"
        # Headers go into META.
        for name, value in self.scope.get("headers", []):
            name = name.decode("latin1")
            if name == "content-length":
                corrected_name = "CONTENT_LENGTH"
            elif name == "content-type":
                corrected_name = "CONTENT_TYPE"
            else:
                corrected_name = "HTTP_%s" % name.upper().replace("-", "_")
            # HTTP/2 say only ASCII chars are allowed in headers, but decode
            # latin1 just in case.
            value = value.decode("latin1")
            if corrected_name in self.META:
                value = self.META[corrected_name] + "," + value
            self.META[corrected_name] = value
        # Pull out request encoding, if provided.
        self._set_content_type_params(self.META)
        # Directly assign the body file to be our stream.
        self._stream = body_file
        # Other bits.
        self.resolver_match = None

    @cached_property
    def GET(self):
        return QueryDict(self.META["QUERY_STRING"])

    def _get_scheme(self):
        return self.scope.get("scheme") or super()._get_scheme()

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
        return parse_cookie(self.META.get("HTTP_COOKIE", ""))

    def close(self):
        super().close()
        self._stream.close()


class ASGIHandler(base.BaseHandler):
    """Handler for ASGI requests."""

    request_class = ASGIRequest
    # Size to chunk response bodies into for multiple response messages.
    chunk_size = 2**16

    def __init__(self):
        super().__init__()
        self.load_middleware(is_async=True)

    async def __call__(self, scope, receive, send):
        """
        Async entrypoint - parses the request and hands off to get_response.
        """
        # Serve only HTTP connections.
        # FIXME: Allow to override this.
        if scope["type"] != "http":
            raise ValueError(
                "Django can only handle ASGI/HTTP connections, not %s." % scope["type"]
            )

        async with ThreadSensitiveContext():
            await self.handle(scope, receive, send)

    async def handle(self, scope, receive, send):
        """
        Handles the ASGI request. Called via the __call__ method.
        """
        # Receive the HTTP request body as a stream object.
        try:
            body_file = await self.read_body(receive)
        except RequestAborted:
            return
        # Request is complete and can be served.
        set_script_prefix(get_script_prefix(scope))
        await signals.request_started.asend(sender=self.__class__, scope=scope)
        # Get the request and check for basic issues.
        request, error_response = self.create_request(scope, body_file)
        if request is None:
            body_file.close()
            await self.send_response(error_response, send)
            await sync_to_async(error_response.close)()
            return

        async def process_request(request, send):
            response = await self.run_get_response(request)
            try:
                await self.send_response(response, send)
            except asyncio.CancelledError:
                # Client disconnected during send_response (ignore exception).
                pass

            return response

        # Try to catch a disconnect while getting response.
        tasks = [
            # Check the status of these tasks and (optionally) terminate them
            # in this order. The listen_for_disconnect() task goes first
            # because it should not raise unexpected errors that would prevent
            # us from cancelling process_request().
            asyncio.create_task(self.listen_for_disconnect(receive)),
            asyncio.create_task(process_request(request, send)),
        ]
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        # Now wait on both tasks (they may have both finished by now).
        for task in tasks:
            if task.done():
                try:
                    task.result()
                except RequestAborted:
                    # Ignore client disconnects.
                    pass
                except AssertionError:
                    body_file.close()
                    raise
            else:
                # Allow views to handle cancellation.
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    # Task re-raised the CancelledError as expected.
                    pass

        try:
            response = tasks[1].result()
        except asyncio.CancelledError:
            await signals.request_finished.asend(sender=self.__class__)
        else:
            await sync_to_async(response.close)()

        body_file.close()

    async def listen_for_disconnect(self, receive):
        """Listen for disconnect from the client."""
        message = await receive()
        if message["type"] == "http.disconnect":
            raise RequestAborted()
        # This should never happen.
        assert False, "Invalid ASGI message after request body: %s" % message["type"]

    async def run_get_response(self, request):
        """Get async response."""
        # Use the async mode of BaseHandler.
        response = await self.get_response_async(request)
        response._handler_class = self.__class__
        # Increase chunk size on file responses (ASGI servers handles low-level
        # chunking).
        if isinstance(response, FileResponse):
            response.block_size = self.chunk_size
        return response

    async def read_body(self, receive):
        """Reads an HTTP body from an ASGI connection."""
        # Use the tempfile that auto rolls-over to a disk file as it fills up.
        body_file = tempfile.SpooledTemporaryFile(
            max_size=settings.FILE_UPLOAD_MAX_MEMORY_SIZE, mode="w+b"
        )
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                body_file.close()
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

    def create_request(self, scope, body_file):
        """
        Create the Request object and returns either (request, None) or
        (None, response) if there is an error response.
        """
        try:
            return self.request_class(scope, body_file), None
        except UnicodeDecodeError:
            logger.warning(
                "Bad Request (UnicodeDecodeError)",
                exc_info=sys.exc_info(),
                extra={"status_code": 400},
            )
            return None, HttpResponseBadRequest()
        except RequestDataTooBig:
            return None, HttpResponse("413 Payload too large", status=413)

    def handle_uncaught_exception(self, request, resolver, exc_info):
        """Last-chance handler for exceptions."""
        # There's no WSGI server to catch the exception further up
        # if this fails, so translate it into a plain text response.
        try:
            return super().handle_uncaught_exception(request, resolver, exc_info)
        except Exception:
            return HttpResponseServerError(
                traceback.format_exc() if settings.DEBUG else "Internal Server Error",
                content_type="text/plain",
            )

    async def send_response(self, response, send):
        """Encode and send a response out over ASGI."""
        # Collect cookies into headers. Have to preserve header case as there
        # are some non-RFC compliant clients that require e.g. Content-Type.
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
        # Initial response message.
        await send(
            {
                "type": "http.response.start",
                "status": response.status_code,
                "headers": response_headers,
            }
        )
        # Streaming responses need to be pinned to their iterator.
        if response.streaming:
            # - Consume via `__aiter__` and not `streaming_content` directly, to
            #   allow mapping of a sync iterator.
            # - Use aclosing() when consuming aiter.
            #   See https://github.com/python/cpython/commit/6e8dcda
            async with aclosing(aiter(response)) as content:
                async for part in content:
                    for chunk, _ in self.chunk_bytes(part):
                        await send(
                            {
                                "type": "http.response.body",
                                "body": chunk,
                                # Ignore "more" as there may be more parts; instead,
                                # use an empty final closing message with False.
                                "more_body": True,
                            }
                        )
            # Final closing message.
            await send({"type": "http.response.body"})
        # Other responses just need chunking.
        else:
            # Yield chunks of response.
            for chunk, last in self.chunk_bytes(response.content):
                await send(
                    {
                        "type": "http.response.body",
                        "body": chunk,
                        "more_body": not last,
                    }
                )

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
