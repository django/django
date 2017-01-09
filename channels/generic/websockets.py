from django.core.serializers.json import DjangoJSONEncoder, json

from ..auth import channel_session_user_from_http
from ..channel import Group
from ..sessions import enforce_ordering
from ..exceptions import SendNotAvailableOnDemultiplexer
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

    # Set to True if you want the class to enforce ordering for you
    slight_ordering = False
    strict_ordering = False

    groups = None

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
            raise ValueError("Slight ordering is now always on. Please remove `slight_ordering=True`.")
        else:
            return handler

    def connection_groups(self, **kwargs):
        """
        Group(s) to make people join when they connect and leave when they
        disconnect. Make sure to return a list/tuple, not a string!
        """
        return self.groups or []

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

    def send(self, text=None, bytes=None, close=False):
        """
        Sends a reply back down the WebSocket
        """
        message = {}
        if close:
            message["close"] = close
        if text is not None:
            message["text"] = text
        elif bytes is not None:
            message["bytes"] = bytes
        else:
            raise ValueError("You must pass text or bytes")
        self.message.reply_channel.send(message)

    @classmethod
    def group_send(cls, name, text=None, bytes=None, close=False):
        message = {}
        if close:
            message["close"] = close
        if text is not None:
            message["text"] = text
        elif bytes is not None:
            message["bytes"] = bytes
        else:
            raise ValueError("You must pass text or bytes")
        Group(name).send(message)

    def close(self, status=True):
        """
        Closes the WebSocket from the server end
        """
        self.message.reply_channel.send({"close": status})

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
        Called when a WebSocket connection is closed.
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

    def send(self, content, close=False):
        """
        Encode the given content as JSON and send it to the client.
        """
        super(JsonWebsocketConsumer, self).send(text=json.dumps(content), close=close)

    @classmethod
    def group_send(cls, name, content, close=False):
        WebsocketConsumer.group_send(name, json.dumps(content), close=close)


class WebsocketDemultiplexer(JsonWebsocketConsumer):
    """
    JSON-understanding WebSocket consumer subclass that handles demultiplexing
    streams using a "stream" key in a top-level dict and the actual payload
    in a sub-dict called "payload". This lets you run multiple streams over
    a single WebSocket connection in a standardised way.

    Incoming messages on streams are dispatched to consumers so you can
    just tie in consumers the normal way. The reply_channels are kept so
    sessions/auth continue to work. Payloads must be a dict at the top level,
    so they fulfill the Channels message spec.

    To answer with a multiplexed message, a multiplexer object
    with "send" and "group_send" methods is forwarded to the consumer as a kwargs
    "multiplexer".

    Set a mapping of streams to consumer classes in the "consumers" keyword.
    """

    # Put your JSON consumers here: {stream_name : consumer}
    consumers = {}

    def receive(self, content, **kwargs):
        """Forward messages to all consumers."""
        # Check the frame looks good
        if isinstance(content, dict) and "stream" in content and "payload" in content:
            # Match it to a channel
            for stream, consumer in self.consumers.items():
                if stream == content['stream']:
                    # Extract payload and add in reply_channel
                    payload = content['payload']
                    if not isinstance(payload, dict):
                        raise ValueError("Multiplexed frame payload is not a dict")
                    # The json consumer expects serialized JSON
                    self.message.content['text'] = json.dumps(payload)
                    # Send demultiplexer to the consumer, to be able to answer
                    kwargs['multiplexer'] = WebsocketMultiplexer(stream, self.message.reply_channel)
                    # Patch send to avoid sending not formated messages from the consumer
                    if hasattr(consumer, "send"):
                        consumer.send = self.send
                    # Dispatch message
                    consumer(self.message, **kwargs)
                    return

            raise ValueError("Invalid multiplexed frame received (stream not mapped)")
        else:
            raise ValueError("Invalid multiplexed **frame received (no channel/payload key)")

    def connect(self, message, **kwargs):
        """Forward connection to all consumers."""
        for stream, consumer in self.consumers.items():
            kwargs['multiplexer'] = WebsocketMultiplexer(stream, self.message.reply_channel)
            consumer(message, **kwargs)

    def disconnect(self, message, **kwargs):
        """Forward disconnection to all consumers."""
        for stream, consumer in self.consumers.items():
            kwargs['multiplexer'] = WebsocketMultiplexer(stream, self.message.reply_channel)
            consumer(message, **kwargs)

    def send(self, *args):
        raise SendNotAvailableOnDemultiplexer("Use multiplexer.send of the multiplexer kwarg.")

    @classmethod
    def group_send(cls, name, stream, payload, close=False):
        raise SendNotAvailableOnDemultiplexer("Use WebsocketMultiplexer.group_send")


class WebsocketMultiplexer(object):
    """
    The opposite of the demultiplexer, to send a message though a multiplexed channel.

    The multiplexer object is passed as a kwargs to the consumer when the message is dispatched.
    This pattern allows the consumer class to be independant of the stream name.
    """

    stream = None
    reply_channel = None

    def __init__(self, stream, reply_channel):
        self.stream = stream
        self.reply_channel = reply_channel

    def send(self, payload):
        """Multiplex the payload using the stream name and send it."""
        self.reply_channel.send(self.encode(self.stream, payload))

    @classmethod
    def encode(cls, stream, payload):
        """
        Encodes stream + payload for outbound sending.
        """
        return {"text": json.dumps({
            "stream": stream,
            "payload": payload,
        }, cls=DjangoJSONEncoder)}

    @classmethod
    def group_send(cls, name, stream, payload, close=False):
        message = WebsocketMultiplexer.encode(stream, payload)
        if close:
            message["close"] = True
        Group(name).send(message)
