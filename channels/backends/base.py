import time
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
        Return the first message available on one of the
        channels passed, as a (channel, message) tuple, or return (None, None)
        if no channels are available.

        Should not block, but is allowed to be moderately slow/have a short
        timeout - it needs to return so we can refresh the list of channels,
        not because the rest of the process is waiting on it.

        Better performance can be achieved for interface servers by directly
        integrating the server and the backend code; this is merely for a
        generic support-everything pattern.
        """
        raise NotImplementedError()

    def receive_many_blocking(self, channels):
        """
        Blocking version of receive_many, if the calling context knows it
        doesn't ever want to change the channels list until something happens.

        This base class provides a default implementation; can be overridden
        to be more efficient by subclasses.
        """
        while True:
            channel, message = self.receive_many(channels)
            if channel is None:
                time.sleep(0.05)
                continue
            return channel, message

    def __str__(self):
        return self.__class__.__name__
