from django.core.serializers.json import DjangoJSONEncoder, json

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
            self.connect(message)
        except AcceptConnection:
            self.accept()
        except DenyConnection:
            self.close()

    def connect(self, message):
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
            self.receive(text_data=message['text'])
        else:
            self.receive(bytes_data=message['bytes'])

    def receive(self, text_data=None, bytes_data=None):
        """
        Called with a decoded WebSocket frame.
        """
        pass

    def send(self, text_data=None, bytes_data=None, close=False):
        """
        Sends a reply back down the WebSocket
        """
        if text is not None:
            super(WebsocketConsumer, self).send(
                {"type": "websocket.send", "text": text_data},
            )
        elif bytes_data is not None:
            super(WebsocketConsumer, self).send(
                {"type": "websocket.send", "bytes": bytes_data},
            )
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

    def raw_receive(self, message, **kwargs):
        if "text" in message:
            self.receive(self.decode_json(message['text']), **kwargs)
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


class WebsocketMultiplexer(object):
    """
    The opposite of the demultiplexer, to send a message though a multiplexed channel.

    The multiplexer object is passed as a kwargs to the consumer when the message is dispatched.
    This pattern allows the consumer class to be independent of the stream name.
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
    def encode_json(cls, content):
        return json.dumps(content, cls=DjangoJSONEncoder)

    @classmethod
    def encode(cls, stream, payload):
        """
        Encodes stream + payload for outbound sending.
        """
        content = {"stream": stream, "payload": payload}
        return {"text": cls.encode_json(content)}

    @classmethod
    def group_send(cls, name, stream, payload, close=False):
        message = cls.encode(stream, payload)
        if close:
            message["close"] = True
        Group(name).send(message)


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

    # Optionally use a custom multiplexer class
    multiplexer_class = WebsocketMultiplexer

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
                    self.message.content['text'] = self.encode_json(payload)
                    # Send demultiplexer to the consumer, to be able to answer
                    kwargs['multiplexer'] = self.multiplexer_class(stream, self.message.reply_channel)
                    # Patch send to avoid sending not formatted messages from the consumer
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
        self.message.reply_channel.send({"accept": True})
        for stream, consumer in self.consumers.items():
            kwargs['multiplexer'] = self.multiplexer_class(stream, self.message.reply_channel)
            consumer(message, **kwargs)

    def disconnect(self, message, **kwargs):
        """Forward disconnection to all consumers."""
        for stream, consumer in self.consumers.items():
            kwargs['multiplexer'] = self.multiplexer_class(stream, self.message.reply_channel)
            consumer(message, **kwargs)

    def send(self, *args):
        raise SendNotAvailableOnDemultiplexer("Use multiplexer.send of the multiplexer kwarg.")

    @classmethod
    def group_send(cls, name, stream, payload, close=False):
        raise SendNotAvailableOnDemultiplexer("Use WebsocketMultiplexer.group_send")
