import random
import string

from django.utils import six

from channels import channel_backends, DEFAULT_CHANNEL_BACKEND


class Channel(object):
    """
    Public interaction class for the channel layer.

    This is separate to the backends so we can:
     a) Hide receive_many from end-users, as it is only for interface servers
     b) Keep a stable-ish backend interface for third parties

    You can pass an alternate Channel Layer alias in, but it will use the
    "default" one by default.
    """

    def __init__(self, name, alias=DEFAULT_CHANNEL_BACKEND):
        """
        Create an instance for the channel named "name"
        """
        self.name = name
        self.channel_layer = channel_backends[alias]

    def send(self, **kwargs):
        """
        Send a message over the channel, taken from the kwargs.
        """
        self.channel_layer.send(self.name, kwargs)

    @classmethod
    def new_name(self, prefix):
        """
        Returns a new channel name that's unique and not closed
        with the given prefix. Does not need to be called before sending
        on a channel name - just provides a way to avoid clashing for
        response channels.
        """
        return "%s.%s" % (prefix, "".join(random.choice(string.ascii_letters) for i in range(32)))

    def as_view(self):
        """
        Returns a view version of this channel - one that takes
        the request passed in and dispatches it to our channel,
        serialized.
        """
        from channels.adapters import view_producer
        return view_producer(self.name)

    @classmethod
    def consumer(self, channels, alias=DEFAULT_CHANNEL_BACKEND):
        """
        Decorator that registers a function as a consumer.
        """
        # Upconvert if you just pass in a string
        if isinstance(channels, six.string_types):
            channels = [channels]
        # Get the channel 
        channel_layer = channel_backends[alias]
        # Return a function that'll register whatever it wraps
        def inner(func):
            channel_layer.registry.add_consumer(func, channels)
            return func
        return inner
