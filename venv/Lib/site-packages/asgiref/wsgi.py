import sys
from collections import defaultdict
from tempfile import SpooledTemporaryFile

from asgiref.sync import AsyncToSync, sync_to_async


class WsgiToAsgi:
    """
    Wraps a WSGI application to make it into an ASGI application.
    """

    def __init__(self, wsgi_application, duplicate_header_limit=100):
        self.wsgi_application = wsgi_application
        self.duplicate_header_limit = duplicate_header_limit

    async def __call__(self, scope, receive, send):
        """
        ASGI application instantiation point.
        We return a new WsgiToAsgiInstance here with the WSGI app
        and the scope, ready to respond when it is __call__ed.
        """
        await WsgiToAsgiInstance(self.wsgi_application, self.duplicate_header_limit)(
            scope, receive, send
        )


class WsgiToAsgiInstance:
    """
    Per-socket instance of a wrapped WSGI application
    """

    def __init__(self, wsgi_application, duplicate_header_limit=100):
        self.wsgi_application = wsgi_application
        self.duplicate_header_limit = duplicate_header_limit
        self.response_started = False
        self.response_content_length = None

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            raise ValueError("WSGI wrapper received a non-HTTP scope")
        self.scope = scope
        with SpooledTemporaryFile(max_size=65536) as body:
            # Alright, wait for the http.request messages
            while True:
                message = await receive()
                if message["type"] != "http.request":
                    raise ValueError("WSGI wrapper received a non-HTTP-request message")
                body.write(message.get("body", b""))
                if not message.get("more_body"):
                    break
            body.seek(0)
            # Wrap send so it can be called from the subthread
            self.sync_send = AsyncToSync(send)
            # Call the WSGI app
            await self.run_wsgi_app(body)

    def build_environ(self, scope, body):
        """
        Builds a scope and request body into a WSGI environ object.
        """
        script_name = scope.get("root_path", "").encode("utf8").decode("latin1")
        path_info = scope["path"].encode("utf8").decode("latin1")
        if path_info.startswith(script_name):
            path_info = path_info[len(script_name) :]
        environ = {
            "REQUEST_METHOD": scope["method"],
            "SCRIPT_NAME": script_name,
            "PATH_INFO": path_info,
            "QUERY_STRING": scope["query_string"].decode("ascii"),
            "SERVER_PROTOCOL": "HTTP/%s" % scope["http_version"],
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": scope.get("scheme", "http"),
            "wsgi.input": body,
            "wsgi.errors": sys.stderr,
            "wsgi.multithread": True,
            "wsgi.multiprocess": True,
            "wsgi.run_once": False,
        }
        # Get server name and port - required in WSGI, not in ASGI
        if "server" in scope:
            environ["SERVER_NAME"] = scope["server"][0]
            environ["SERVER_PORT"] = str(scope["server"][1])
        else:
            environ["SERVER_NAME"] = "localhost"
            environ["SERVER_PORT"] = "80"

        if scope.get("client") is not None:
            environ["REMOTE_ADDR"] = scope["client"][0]

        # Go through headers and make them into environ entries
        _headers = defaultdict(list)
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
            if (
                self.duplicate_header_limit
                and len(_headers[corrected_name]) >= self.duplicate_header_limit
            ):
                raise ValueError(
                    f"Too many duplicate headers: {corrected_name} exceeds limit of"
                    f"{self.duplicate_header_limit}"
                )
            _headers[corrected_name].append(value)
        for name, values in _headers.items():
            environ[name] = ",".join(values)
        return environ

    def start_response(self, status, response_headers, exc_info=None):
        """
        WSGI start_response callable.
        """
        # Don't allow re-calling once response has begun
        if self.response_started:
            raise exc_info[1].with_traceback(exc_info[2])
        # Don't allow re-calling without exc_info
        if hasattr(self, "response_start") and exc_info is None:
            raise ValueError(
                "You cannot call start_response a second time without exc_info"
            )
        # Extract status code
        status_code, _ = status.split(" ", 1)
        status_code = int(status_code)
        # Extract headers
        headers = [
            (name.lower().encode("ascii"), value.encode("ascii"))
            for name, value in response_headers
        ]
        # Extract content-length
        self.response_content_length = None
        for name, value in response_headers:
            if name.lower() == "content-length":
                self.response_content_length = int(value)
        # Build and send response start message.
        self.response_start = {
            "type": "http.response.start",
            "status": status_code,
            "headers": headers,
        }

    @sync_to_async
    def run_wsgi_app(self, body):
        """
        Called in a subthread to run the WSGI app. We encapsulate like
        this so that the start_response callable is called in the same thread.
        """
        # Translate the scope and incoming request body into a WSGI environ
        try:
            environ = self.build_environ(self.scope, body)
        except ValueError:
            # Return 400 Bad Request if header limit exceeded
            self.sync_send(
                {
                    "type": "http.response.start",
                    "status": 400,
                    "headers": [(b"content-type", b"text/plain")],
                }
            )
            self.sync_send(
                {
                    "type": "http.response.body",
                    "body": b"Bad Request: Too many duplicate headers",
                }
            )
            return
        # Run the WSGI app
        bytes_sent = 0
        for output in self.wsgi_application(environ, self.start_response):
            # If this is the first response, include the response headers
            if not self.response_started:
                self.response_started = True
                self.sync_send(self.response_start)
            # If the application supplies a Content-Length header
            if self.response_content_length is not None:
                # The server should not transmit more bytes to the client than the header allows
                bytes_allowed = self.response_content_length - bytes_sent
                if len(output) > bytes_allowed:
                    output = output[:bytes_allowed]
            self.sync_send(
                {"type": "http.response.body", "body": output, "more_body": True}
            )
            bytes_sent += len(output)
            # The server should stop iterating over the response when enough data has been sent
            if bytes_sent == self.response_content_length:
                break
        # Close connection
        if not self.response_started:
            self.response_started = True
            self.sync_send(self.response_start)
        self.sync_send({"type": "http.response.body"})
