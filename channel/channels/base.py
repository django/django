class Channel(object):
    """
    Base class for all channel layer implementations.
    """

    class ClosedError(Exception):
        """
        Raised when you try to send to a closed channel.
        """
        pass

    def __init__(self, name):
        """
        Create an instance for the channel named "name"
        """
        self.name = name

    def send(self, **kwargs):
        """
        Send a message over the channel, taken from the kwargs.
        """
        raise NotImplementedError()

    def close(self):
        """
        Closes the channel, allowing no more messages to be sent over it.
        """
        raise NotImplementedError()

    @property
    def closed(self):
        """
        Says if the channel is closed.
        """
        raise NotImplementedError()

    @classmethod
    def receive_many(self, channel_names):
        """
        Block and return the first message available on one of the
        channels passed, as a (channel_name, message) tuple.
        """
        raise NotImplementedError()

    @classmethod
    def new_name(self, prefix):
        """
        Returns a new channel name that's unique and not closed
        with the given prefix. Does not need to be called before sending
        on a channel name - just provides a way to avoid clashing for
        response channels.
        """
        raise NotImplementedError()
