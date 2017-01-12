from __future__ import unicode_literals
import six


class ConsumeLater(Exception):
    """
    Exception that says that the current message should be re-queued back
    onto its channel as it's not ready to be consumd yet (e.g. global order
    is being enforced)
    """
    pass


class ResponseLater(Exception):
    """
    Exception raised inside a Django view when the view has passed
    responsibility for the response to another consumer, and so is not
    returning a response.
    """
    pass


class RequestTimeout(Exception):
    """
    Raised when it takes too long to read a request body.
    """
    pass


class RequestAborted(Exception):
    """
    Raised when the incoming request tells us it's aborted partway through
    reading the body.
    """
    pass


class DenyConnection(Exception):
    """
    Raised during a websocket.connect (or other supported connection) handler
    to deny the connection.
    """
    pass


class ChannelSocketException(Exception):
    """
    Base Exception is intended to run some action ('run' method)
    when it is raised at a consumer body
    """

    def run(self, message):
        raise NotImplementedError


class WebsocketCloseException(ChannelSocketException):
    """
    ChannelSocketException based exceptions for close websocket connection with code
    """

    def __init__(self, code=None):
        if code is not None and not isinstance(code, six.integer_types) \
                and code != 1000 and not (3000 <= code <= 4999):
            raise ValueError("invalid close code {} (must be 1000 or from [3000, 4999])".format(code))
        self._code = code

    def run(self, message):
        if message.reply_channel.name.split('.')[0] != "websocket":
            raise ValueError("You cannot raise CloseWebsocketError from a non-websocket handler.")
        message.reply_channel.send({"close": self._code or True})


class SendNotAvailableOnDemultiplexer(Exception):
    """
    Raised when trying to send with a WebsocketDemultiplexer. Use the multiplexer instead.
    """
    pass
