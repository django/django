import django
import time

from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory
from collections import deque
from twisted.internet import reactor

from channels import Channel, channel_backends, DEFAULT_CHANNEL_BACKEND


class InterfaceProtocol(WebSocketServerProtocol):
    """
    Protocol which supports WebSockets and forwards incoming messages to
    the django.websocket channels.
    """

    def onConnect(self, request):
        self.channel_backend = channel_backends[DEFAULT_CHANNEL_BACKEND]
        self.request_info = {
            "path": request.path,
        }

    def onOpen(self):
        # Make sending channel
        self.send_channel = Channel.new_name("!django.websocket.send")
        self.last_keepalive = time.time()
        self.factory.protocols[self.send_channel] = self
        # Send news that this channel is open
        Channel("django.websocket.connect").send(
            send_channel = self.send_channel,
            **self.request_info
        )

    def onMessage(self, payload, isBinary):
        if isBinary:
            Channel("django.websocket.receive").send(
                send_channel = self.send_channel,
                content = payload,
                binary = True,
                **self.request_info
            )
        else:
            Channel("django.websocket.receive").send(
                send_channel = self.send_channel,
                content = payload.decode("utf8"),
                binary = False,
                **self.request_info
            )

    def serverSend(self, content, binary=False, **kwargs):
        """
        Server-side channel message to send a message.
        """
        if binary:
            self.sendMessage(content, binary)
        else:
            self.sendMessage(content.encode("utf8"), binary)

    def serverClose(self):
        """
        Server-side channel message to close the socket
        """
        self.sendClose()

    def onClose(self, wasClean, code, reason):
        if hasattr(self, "send_channel"):
            del self.factory.protocols[self.send_channel]
            Channel("django.websocket.disconnect").send(
                send_channel = self.send_channel,
                **self.request_info
            )

    def sendKeepalive(self):
        """
        Sends a keepalive packet on the keepalive channel.
        """
        Channel("django.websocket.keepalive").send(
            send_channel = self.send_channel,
            **self.request_info
        )
        self.last_keepalive = time.time()


class InterfaceFactory(WebSocketServerFactory):
    """
    Factory which keeps track of its open protocols' receive channels
    and can dispatch to them.
    """

    # TODO: Clean up dead protocols if needed?

    def __init__(self, *args, **kwargs):
        super(InterfaceFactory, self).__init__(*args, **kwargs)
        self.protocols = {}

    def send_channels(self):
        return self.protocols.keys()

    def dispatch_send(self, channel, message):
        if message.get("close", False):
            self.protocols[channel].serverClose()
        else:
            self.protocols[channel].serverSend(**message)


class WebsocketTwistedInterface(object):
    """
    Easy API to run a WebSocket interface server using Twisted.
    Integrates the channel backend by running it in a separate thread, using
    the always-compatible polling style.
    """

    def __init__(self, channel_backend, port=9000):
        self.channel_backend = channel_backend
        self.port = port

    def run(self):
        self.factory = InterfaceFactory("ws://0.0.0.0:%i" % self.port, debug=False)
        self.factory.protocol = InterfaceProtocol
        reactor.listenTCP(self.port, self.factory)
        reactor.callInThread(self.backend_reader)
        reactor.callLater(1, self.keepalive_sender)
        reactor.run()

    def backend_reader(self):
        """
        Run in a separate thread; reads messages from the backend.
        """
        while True:
            channels = self.factory.send_channels()
            # TODO: Send keepalives
            # Quit if reactor is stopping
            if not reactor.running:
                return
            # Don't do anything if there's no channels to listen on
            if channels:
                channel, message = self.channel_backend.receive_many(channels)
            else:
                time.sleep(0.1)
                continue
            # Wait around if there's nothing received
            if channel is None:
                time.sleep(0.05)
                continue
            # Deal with the message
            self.factory.dispatch_send(channel, message)

    def keepalive_sender(self):
        """
        Sends keepalive messages for open WebSockets every
        (channel_backend expiry / 2) seconds.
        """
        expiry_window = int(self.channel_backend.expiry / 2)
        for protocol in self.factory.protocols.values():
            if time.time() - protocol.last_keepalive > expiry_window:
                protocol.sendKeepalive()
        reactor.callLater(1, self.keepalive_sender)
