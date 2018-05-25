from channels.consumer import AsyncConsumer


class AsyncHttpConsumer(AsyncConsumer):
    """
    Async HTTP consumer. Provides basic primitives for building asynchronous
    HTTP endpoints.
    """

    async def __call__(self, receive, send):
        """
        Async entrypoint - concatenates body fragments and hands off control
        to ``self.handle`` when the body has been completely received.
        """
        self.send = send
        body = []
        try:
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                else:
                    if "body" in message:
                        body.append(message["body"])
                    if not message.get("more_body"):
                        await self.handle(b"".join(body))
        finally:
            await self.disconnect()

    async def send_headers(self, *, status=200, headers=None):
        """
        Sets the HTTP response status and headers. Headers may be provided as
        a list of tuples or as a dictionary.

        Note that the ASGI spec requires that the protocol server only starts
        sending the response to the client after ``self.send_body`` has been
        called the first time.
        """
        if headers is None:
            headers = []
        elif isinstance(headers, dict):
            headers = list(headers.items())

        await self.send({
            "type": "http.response.start",
            "status": status,
            "headers": headers,
        })

    async def send_body(self, body, *, more_body=False):
        """
        Sends a response body to the client. The method expects a bytestring.

        Set ``more_body=True`` if you want to send more body content later.
        The default behavior closes the response, and further messages on
        the channel will be ignored.
        """
        assert isinstance(body, bytes), "Body is not bytes"
        await self.send({
            "type": "http.response.body",
            "body": body,
            "more_body": more_body,
        })

    async def send_response(self, status, body, **kwargs):
        """
        Sends a response to the client. This is a thin wrapper over
        ``self.send_headers`` and ``self.send_body``, and everything said
        above applies here as well. This method may only be called once.
        """
        await self.send_headers(status=status, **kwargs)
        await self.send_body(body)

    async def handle(self, body):
        """
        Receives the request body as a bytestring. Response may be composed
        using the ``self.send*`` methods; the return value of this method is
        thrown away.
        """
        raise NotImplementedError(
            "Subclasses of AsyncHttpConsumer must provide a handle() method."
        )

    async def disconnect(self):
        """
        Overrideable place to run disconnect handling. Do not send anything
        from here.
        """
        pass
