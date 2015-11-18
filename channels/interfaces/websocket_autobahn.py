import time

from django.http import parse_cookie

from channels import DEFAULT_CHANNEL_BACKEND, Channel, channel_backends


def get_protocol(base):

    class InterfaceProtocol(base):
        """
        Protocol which supports WebSockets and forwards incoming messages to
        the websocket channels.
        """

        def onConnect(self, request):
            self.channel_backend = channel_backends[DEFAULT_CHANNEL_BACKEND]
            self.request_info = {
                "path": request.path,
                "get": request.params,
                "cookies": parse_cookie(request.headers.get('cookie', ''))
            }

        def onOpen(self):
            # Make sending channel
            self.reply_channel = Channel.new_name("!websocket.send")
            self.request_info["reply_channel"] = self.reply_channel
            self.last_keepalive = time.time()
            self.factory.protocols[self.reply_channel] = self
            # Send news that this channel is open
            Channel("websocket.connect").send(self.request_info)

        def onMessage(self, payload, isBinary):
            if isBinary:
                Channel("websocket.receive").send({
                    "reply_channel": self.reply_channel,
                    "content": payload,
                    "binary": True,
                })
            else:
                Channel("websocket.receive").send({
                    "reply_channel": self.reply_channel,
                    "content": payload.decode("utf8"),
                    "binary": False,
                })

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
            if hasattr(self, "reply_channel"):
                del self.factory.protocols[self.reply_channel]
                Channel("websocket.disconnect").send({
                    "reply_channel": self.reply_channel,
                })

        def sendKeepalive(self):
            """
            Sends a keepalive packet on the keepalive channel.
            """
            Channel("websocket.keepalive").send({
                "reply_channel": self.reply_channel,
            })
            self.last_keepalive = time.time()

    return InterfaceProtocol


def get_factory(base):

    class InterfaceFactory(base):
        """
        Factory which keeps track of its open protocols' receive channels
        and can dispatch to them.
        """

        # TODO: Clean up dead protocols if needed?

        def __init__(self, *args, **kwargs):
            super(InterfaceFactory, self).__init__(*args, **kwargs)
            self.protocols = {}

        def reply_channels(self):
            return self.protocols.keys()

        def dispatch_send(self, channel, message):
            if message.get("content", None):
                self.protocols[channel].serverSend(**message)
            if message.get("close", False):
                self.protocols[channel].serverClose()

    return InterfaceFactory
