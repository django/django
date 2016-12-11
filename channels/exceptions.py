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


class SendNotAvailableOnDemultiplexer(Exception):
    """
    Raised when trying to send with a WebsocketDemultiplexer. Use the multiplexer instead.
    """
    pass
