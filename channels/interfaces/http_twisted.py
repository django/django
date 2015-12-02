import time

from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory
from twisted.python.compat import _PY3
from twisted.web.http import HTTPFactory, HTTPChannel, Request, _respondToBadRequestAndDisconnect, parse_qs, _parseHeader
from twisted.protocols.policies import ProtocolWrapper
from twisted.internet import reactor

from channels import Channel, channel_backends, DEFAULT_CHANNEL_BACKEND
from .websocket_autobahn import get_protocol, get_factory


WebsocketProtocol = get_protocol(WebSocketServerProtocol)


class WebRequest(Request):
    """
    Request that either hands off information to channels, or offloads
    to a WebSocket class.

    Does some extra processing over the normal Twisted Web request to separate
    GET and POST out.
    """

    def __init__(self, *args, **kwargs):
        Request.__init__(self, *args, **kwargs)
        self.reply_channel = Channel.new_name("!http.response")
        self.channel.factory.reply_protocols[self.reply_channel] = self

    def process(self):
        # Get upgrade header
        upgrade_header = None
        if self.requestHeaders.hasHeader("Upgrade"):
            upgrade_header = self.requestHeaders.getRawHeaders("Upgrade")[0]
        # Is it WebSocket? IS IT?!
        if upgrade_header == "websocket":
            # Make WebSocket protocol to hand off to
            protocol = self.channel.factory.ws_factory.buildProtocol(self.transport.getPeer())
            if not protocol:
                # If protocol creation fails, we signal "internal server error"
                self.setResponseCode(500)
                self.finish()
            # Port across transport
            transport, self.transport = self.transport, None
            if isinstance(transport, ProtocolWrapper):
                # i.e. TLS is a wrapping protocol
                transport.wrappedProtocol = protocol
            else:
                transport.protocol = protocol
            protocol.makeConnection(transport)
            # Re-inject request
            if _PY3:
                data = self.method + b' ' + self.uri + b' HTTP/1.1\x0d\x0a'
                for h in self.requestHeaders.getAllRawHeaders():
                    data += h[0] + b': ' + b",".join(h[1]) + b'\x0d\x0a'
                data += b"\x0d\x0a"
                data += self.content.read()
            else:
                data = "%s %s HTTP/1.1\x0d\x0a" % (self.method, self.uri)
                for h in self.requestHeaders.getAllRawHeaders():
                    data += "%s: %s\x0d\x0a" % (h[0], ",".join(h[1]))
                data += "\x0d\x0a"
            protocol.dataReceived(data)
            # Remove our HTTP reply channel association
            self.channel.factory.reply_protocols[self.reply_channel] = None
            self.reply_channel = None
        # Boring old HTTP.
        else:
            # Send request message
            Channel("http.request").send({
                "reply_channel": self.reply_channel,
                "method": self.method,
                "get": self.get,
                "post": self.post,
                "cookies": self.received_cookies,
                "headers": {k: v[0] for k, v in self.requestHeaders.getAllRawHeaders()},
                "client": [self.client.host, self.client.port],
                "server": [self.host.host, self.host.port],
                "path": self.path,
            })

    def connectionLost(self, reason):
        """
        Cleans up reply channel on close.
        """
        if self.reply_channel:
            del self.channel.factory.reply_protocols[self.reply_channel]
        Request.connectionLost(self, reason)

    def serverResponse(self, message):
        """
        Writes a received HTTP response back out to the transport.
        """
        # Write code
        self.setResponseCode(message['status'])
        # Write headers
        for header, value in message.get("headers", {}):
            self.setHeader(header.encode("utf8"), value.encode("utf8"))
        # Write cookies
        for cookie in message.get("cookies"):
            self.cookies.append(cookie.encode("utf8"))
        # Write out body
        if "content" in message:
            Request.write(self, message['content'].encode("utf8"))
        self.finish()

    def requestReceived(self, command, path, version):
        """
        Called by channel when all data has been received.
        Overridden because Twisted merges GET and POST into one thing by default.
        """
        self.content.seek(0,0)
        self.get = {}
        self.post = {}

        self.method, self.uri = command, path
        self.clientproto = version
        x = self.uri.split(b'?', 1)

        print self.method

        # URI and GET args assignment
        if len(x) == 1:
            self.path = self.uri
        else:
            self.path, argstring = x
            self.get = parse_qs(argstring, 1)

        # cache the client and server information, we'll need this later to be
        # serialized and sent with the request so CGIs will work remotely
        self.client = self.channel.transport.getPeer()
        self.host = self.channel.transport.getHost()

        # Argument processing
        ctype = self.requestHeaders.getRawHeaders(b'content-type')
        if ctype is not None:
            ctype = ctype[0]

        # Process POST data if present
        if self.method == b"POST" and ctype:
            mfd = b'multipart/form-data'
            key, pdict = _parseHeader(ctype)
            if key == b'application/x-www-form-urlencoded':
                self.post.update(parse_qs(self.content.read(), 1))
            elif key == mfd:
                try:
                    cgiArgs = cgi.parse_multipart(self.content, pdict)

                    if _PY3:
                        # parse_multipart on Python 3 decodes the header bytes
                        # as iso-8859-1 and returns a str key -- we want bytes
                        # so encode it back
                        self.post.update({x.encode('iso-8859-1'): y
                                          for x, y in cgiArgs.items()})
                    else:
                        self.post.update(cgiArgs)
                except:
                    # It was a bad request.
                    _respondToBadRequestAndDisconnect(self.channel.transport)
                    return
            self.content.seek(0, 0)

        # Continue with rest of request handling
        self.process()


class WebProtocol(HTTPChannel):
    
    requestFactory = WebRequest


class WebFactory(HTTPFactory):
    
    protocol = WebProtocol

    def __init__(self):
        HTTPFactory.__init__(self)
        # We track all sub-protocols for response channel mapping
        self.reply_protocols = {}
        # Make a factory for WebSocket protocols
        self.ws_factory = WebSocketServerFactory("ws://127.0.0.1:8000")
        self.ws_factory.protocol = WebsocketProtocol
        self.ws_factory.reply_protocols = self.reply_protocols

    def reply_channels(self):
        return self.reply_protocols.keys()

    def dispatch_reply(self, channel, message):
        if channel.startswith("!http") and isinstance(self.reply_protocols[channel], WebRequest):
            self.reply_protocols[channel].serverResponse(message)
        elif channel.startswith("!websocket") and isinstance(self.reply_protocols[channel], WebsocketProtocol):
            if message.get("content", None):
                self.reply_protocols[channel].serverSend(**message)
            if message.get("close", False):
                self.reply_protocols[channel].serverClose()
        else:
            raise ValueError("Cannot dispatch message on channel %r" % channel)


class HttpTwistedInterface(object):
    """
    Easy API to run a HTTP1 & WebSocket interface server using Twisted.
    Integrates the channel backend by running it in a separate thread, using
    the always-compatible polling style.
    """

    def __init__(self, channel_backend, port=8000):
        self.channel_backend = channel_backend
        self.port = port

    def run(self):
        self.factory = WebFactory()
        reactor.listenTCP(self.port, self.factory)
        reactor.callInThread(self.backend_reader)
        #reactor.callLater(1, self.keepalive_sender)
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
            self.factory.dispatch_reply(channel, message)

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
