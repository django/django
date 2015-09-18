import asyncio
import time

from autobahn.asyncio.websocket import WebSocketServerProtocol, WebSocketServerFactory

from .websocket_autobahn import get_protocol, get_factory


class WebsocketAsyncioInterface(object):
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
        self.loop = asyncio.get_event_loop()
        coro = self.loop.create_server(self.factory, '0.0.0.0', self.port)
        server = self.loop.run_until_complete(coro)
        self.loop.run_in_executor(None, self.backend_reader)
        self.loop.call_later(1, self.keepalive_sender)
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.close()
            self.loop.close()

    def backend_reader(self):
        """
        Run in a separate thread; reads messages from the backend.
        """
        # Wait for main loop to start
        time.sleep(0.5)
        while True:
            channels = self.factory.reply_channels()
            # Quit if reactor is stopping
            if not self.loop.is_running():
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
        self.loop.call_later(1, self.keepalive_sender)
