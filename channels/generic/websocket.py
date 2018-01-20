import json

from ..consumer import SyncConsumer
from ..exceptions import AcceptConnection, DenyConnection


class WebsocketConsumer(SyncConsumer):
    """
    Base WebSocket consumer. Provides a general encapsulation for the
    WebSocket handling model that other applications can build on.
    """

    def websocket_connect(self, message):
        """
        Called when a WebSocket connection is opened.
        """
        # TODO: group joining
        try:
            self.connect()
        except AcceptConnection:
            self.accept()
        except DenyConnection:
            self.close()

    def connect(self):
        self.accept()

    def accept(self):
        """
        Accepts an incoming socket
        """
        super(WebsocketConsumer, self).send({"type": "websocket.accept"})

    def websocket_receive(self, message):
        """
        Called when a WebSocket frame is received. Decodes it and passes it
        to receive().
        """
        if "text" in message:
            self.receive(text_data=message["text"])
        else:
            self.receive(bytes_data=message["bytes"])

    def receive(self, text_data=None, bytes_data=None):
        """
        Called with a decoded WebSocket frame.
        """
        pass

    def send(self, text_data=None, bytes_data=None, close=False):
        """
        Sends a reply back down the WebSocket
        """
        if text_data is not None:
            super(WebsocketConsumer, self).send(
                {"type": "websocket.send", "text": text_data},
            )
        elif bytes_data is not None:
            super(WebsocketConsumer, self).send(
                {"type": "websocket.send", "bytes": bytes_data},
            )
        else:
            raise ValueError("You must pass one of bytes_data or text_data")
        if close:
            self.close(close)

    def close(self, code=None):
        """
        Closes the WebSocket from the server end
        """
        if code is not None and code is not True:
            super(WebsocketConsumer, self).send(
                {"type": "websocket.close", "code": code}
            )
        else:
            super(WebsocketConsumer, self).send(
                {"type": "websocket.close"}
            )

    def websocket_disconnect(self, message):
        """
        Called when a WebSocket connection is closed. Base level so you don't
        need to call super() all the time.
        """
        # TODO: group leaving
        self.disconnect(message)

    def disconnect(self, message):
        """
        Called when a WebSocket connection is closed.
        """
        pass


class JsonWebsocketConsumer(WebsocketConsumer):
    """
    Variant of WebsocketConsumer that automatically JSON-encodes and decodes
    messages as they come in and go out. Expects everything to be text; will
    error on binary data.
    """

    def receive(self, text_data=None, bytes_data=None, **kwargs):
        if text_data:
            self.receive_json(self.decode_json(text_data), **kwargs)
        else:
            raise ValueError("No text section for incoming WebSocket frame!")

    def receive_json(self, content, **kwargs):
        """
        Called with decoded JSON content.
        """
        pass

    def send_json(self, content, close=False):
        """
        Encode the given content as JSON and send it to the client.
        """
        super(JsonWebsocketConsumer, self).send(
            text_data=self.encode_json(content),
            close=close,
        )

    @classmethod
    def decode_json(cls, text_data):
        return json.loads(text_data)

    @classmethod
    def encode_json(cls, content):
        return json.dumps(content)
