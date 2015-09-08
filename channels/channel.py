import random
import string

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

    def __init__(self, name, alias=DEFAULT_CHANNEL_BACKEND, channel_backend=None):
        """
        Create an instance for the channel named "name"
        """
        self.name = name
        if channel_backend:
            self.channel_backend = channel_backend
        else:
            self.channel_backend = channel_backends[alias]

    def send(self, content):
        """
        Send a message over the channel - messages are always dicts.
        """
        if not isinstance(content, dict):
            raise ValueError("You can only send dicts as content on channels.")
        self.channel_backend.send(self.name, content)

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

    def __str__(self):
        return self.name


class Group(object):
    """
    A group of channels that can be messaged at once, and that expire out
    of the group after an expiry time (keep re-adding to keep them in).
    """

    def __init__(self, name, alias=DEFAULT_CHANNEL_BACKEND, channel_backend=None):
        self.name = name
        if channel_backend:
            self.channel_backend = channel_backend
        else:
            self.channel_backend = channel_backends[alias]

    def add(self, channel):
        if isinstance(channel, Channel):
            channel = channel.name
        self.channel_backend.group_add(self.name, channel)

    def discard(self, channel):
        if isinstance(channel, Channel):
            channel = channel.name
        self.channel_backend.group_discard(self.name, channel)

    def channels(self):
        self.channel_backend.group_channels(self.name)

    def send(self, content):
        if not isinstance(content, dict):
            raise ValueError("You can only send dicts as content on channels.")
        self.channel_backend.send_group(self.name, content)
