import json

from ..channel import Group
from ..auth import channel_session_user_from_http
from ..sessions import enforce_ordering
from .base import BaseConsumer


class WebsocketConsumer(BaseConsumer):
    """
    Base WebSocket consumer. Provides a general encapsulation for the
    WebSocket handling model that other applications can build on.
    """

    # You shouldn't need to override this
    method_mapping = {
        "websocket.connect": "raw_connect",
        "websocket.receive": "raw_receive",
        "websocket.disconnect": "raw_disconnect",
    }

    # Turning this on passes the user over from the HTTP session on connect,
    # implies channel_session_user
    http_user = False

    # Set one to True if you want the class to enforce ordering for you
    slight_ordering = False
    strict_ordering = False

    def get_handler(self, message, **kwargs):
        """
        Pulls out the path onto an instance variable, and optionally
        adds the ordering decorator.
        """
        # HTTP user implies channel session user
        if self.http_user:
            self.channel_session_user = True
        # Get super-handler
        self.path = message['path']
        handler = super(WebsocketConsumer, self).get_handler(message, **kwargs)
        # Optionally apply HTTP transfer
        if self.http_user:
            handler = channel_session_user_from_http(handler)
        # Ordering decorators
        if self.strict_ordering:
            return enforce_ordering(handler, slight=False)
        elif self.slight_ordering:
            return enforce_ordering(handler, slight=True)
        else:
            return handler

    def connection_groups(self, **kwargs):
        """
        Group(s) to make people join when they connect and leave when they
        disconnect. Make sure to return a list/tuple, not a string!
        """
        return []

    def raw_connect(self, message, **kwargs):
        """
        Called when a WebSocket connection is opened. Base level so you don't
        need to call super() all the time.
        """
        for group in self.connection_groups(**kwargs):
            Group(group, channel_layer=message.channel_layer).add(message.reply_channel)
        self.connect(message, **kwargs)

    def connect(self, message, **kwargs):
        """
        Called when a WebSocket connection is opened.
        """
        pass

    def raw_receive(self, message, **kwargs):
        """
        Called when a WebSocket frame is received. Decodes it and passes it
        to receive().
        """
        if "text" in message:
            self.receive(text=message['text'], **kwargs)
        else:
            self.receive(bytes=message['bytes'], **kwargs)

    def receive(self, text=None, bytes=None, **kwargs):
        """
        Called with a decoded WebSocket frame.
        """
        pass

    def send(self, text=None, bytes=None):
        """
        Sends a reply back down the WebSocket
        """
        if text is not None:
            self.message.reply_channel.send({"text": text})
        elif bytes is not None:
            self.message.reply_channel.send({"bytes": bytes})
        else:
            raise ValueError("You must pass text or bytes")

    def group_send(self, name, text=None, bytes=None):
        if text is not None:
            Group(name, channel_layer=self.message.channel_layer).send({"text": text})
        elif bytes is not None:
            Group(name, channel_layer=self.message.channel_layer).send({"bytes": bytes})
        else:
            raise ValueError("You must pass text or bytes")

    def close(self):
        """
        Closes the WebSocket from the server end
        """
        self.message.reply_channel.send({"close": True})

    def raw_disconnect(self, message, **kwargs):
        """
        Called when a WebSocket connection is closed. Base level so you don't
        need to call super() all the time.
        """
        for group in self.connection_groups(**kwargs):
            Group(group, channel_layer=message.channel_layer).discard(message.reply_channel)
        self.disconnect(message, **kwargs)

    def disconnect(self, message, **kwargs):
        """
        Called when a WebSocket connection is opened.
        """
        pass


class JsonWebsocketConsumer(WebsocketConsumer):
    """
    Variant of WebsocketConsumer that automatically JSON-encodes and decodes
    messages as they come in and go out. Expects everything to be text; will
    error on binary data.
    """

    def raw_receive(self, message, **kwargs):
        if "text" in message:
            self.receive(json.loads(message['text']), **kwargs)
        else:
            raise ValueError("No text section for incoming WebSocket frame!")

    def receive(self, content, **kwargs):
        """
        Called with decoded JSON content.
        """
        pass

    def send(self, content):
        """
        Encode the given content as JSON and send it to the client.
        """
        super(JsonWebsocketConsumer, self).send(text=json.dumps(content))

    def group_send(self, name, content):
        super(JsonWebsocketConsumer, self).group_send(name, json.dumps(content))
