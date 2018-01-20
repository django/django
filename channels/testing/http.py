from asgiref.testing import ApplicationCommunicator


class HttpCommunicator(ApplicationCommunicator):
    """
    ApplicationCommunicator subclass that has HTTP shortcut methods.

    It will construct the scope for you, so you need to pass the application
    (uninstantiated) along with HTTP parameters.

    This does not support full chunking - for that, just use ApplicationCommunicator
    directly.
    """

    def __init__(self, application, method, path, body=b""):
        self.scope = {
            "type": "http",
            "http_version": "1.1",
            "method": method.upper(),
            "path": path,
        }
        assert isinstance(body, bytes)
        self.body = body
        self.sent_request = False
        super().__init__(application, self.scope)

    async def get_response(self, timeout=1):
        """
        Get the application's response. Returns a dict with keys of
        "body", "headers" and "status".
        """
        # If we've not sent the request yet, do so
        if not self.sent_request:
            self.sent_request = True
            await self.send_input({
                "type": "http.request",
                "body": self.body,
            })
        # Get the response start
        response_start = await self.receive_output(timeout)
        assert response_start["type"] == "http.response.start"
        # Get all body parts
        response_start["body"] = b""
        while True:
            chunk = await self.receive_output(timeout)
            assert chunk["type"] == "http.response.body"
            assert isinstance(chunk["body"], bytes)
            response_start["body"] += chunk["body"]
            if not chunk.get("more_body", False):
                break
        # Return structured info
        del response_start["type"]
        response_start.setdefault("headers", [])
        return response_start
