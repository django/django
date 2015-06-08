import random
import string


class Channel(object):
    """
    Public interaction class for the channel layer.

    This is separate to the backends so we can:
     a) Hide receive_many from end-users, as it is only for interface servers
     b) Keep a stable-ish backend interface for third parties

    You can pass an alternate Channel Layer alias in, but it will use the
    "default" one by default.
    """

    def __init__(self, name, alias=None):
        """
        Create an instance for the channel named "name"
        """
        from channels import channel_layers, DEFAULT_CHANNEL_LAYER
        self.name = name
        self.channel_layer = channel_layers[alias or DEFAULT_CHANNEL_LAYER]

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
