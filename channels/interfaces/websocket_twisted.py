import time

from autobahn.twisted.websocket import (
    WebSocketServerFactory, WebSocketServerProtocol,
)
from twisted.internet import reactor

from .websocket_autobahn import get_factory, get_protocol


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
        self.factory = get_factory(WebSocketServerFactory)("ws://0.0.0.0:%i" % self.port, debug=False)
        self.factory.protocol = get_protocol(WebSocketServerProtocol)
        reactor.listenTCP(self.port, self.factory)
        reactor.callInThread(self.backend_reader)
        reactor.callLater(1, self.keepalive_sender)
        reactor.run()

    def backend_reader(self):
        """
        Run in a separate thread; reads messages from the backend.
        """
        while True:
            channels = self.factory.reply_channels()
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
        for protocol in self.factory.reply_protocols.values():
            if time.time() - protocol.last_keepalive > expiry_window:
                protocol.sendKeepalive()
        reactor.callLater(1, self.keepalive_sender)
