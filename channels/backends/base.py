from channels.consumer_registry import ConsumerRegistry


class ChannelClosed(Exception):
    """
    Raised when you try to send to a closed channel.
    """
    pass


class BaseChannelBackend(object):
    """
    Base class for all channel layer implementations. Manages both sending
    and receving messages from the backend, and each comes with its own
    registry of consumers.
    """

    # Flags if this backend can only be used inside one process.
    # Causes errors if you try to run workers/interfaces separately with it.
    local_only = False

    def __init__(self, expiry=60):
        self.registry = ConsumerRegistry()
        self.expiry = expiry

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

    def __str__(self):
        return self.__class__.__name__
