class ChannelClosed(Exception):
    """
    Raised when you try to send to a closed channel.
    """
    pass


class BaseChannelBackend(object):
    """
    Base class for all channel layer implementations.
    """

    def send(self, channel, message):
        """
        Send a message over the channel, taken from the kwargs.
        """
        raise NotImplementedError()

    def receive_many(self, channels):
        """
        Block and return the first message available on one of the
        channels passed, as a (channel, message) tuple.
        """
        raise NotImplementedError()
