from __future__ import unicode_literals

from django.utils import six

from channels import DEFAULT_CHANNEL_LAYER, channel_layers


class Channel(object):
    """
    Public interaction class for the channel layer.

    This is separate to the backends so we can:
     a) Hide receive_many from end-users, as it is only for interface servers
     b) Keep a stable-ish backend interface for third parties

    You can pass an alternate Channel Layer alias in, but it will use the
    "default" one by default.
    """

    def __init__(self, name, alias=DEFAULT_CHANNEL_LAYER, channel_layer=None):
        """
        Create an instance for the channel named "name"
        """
        if isinstance(name, six.binary_type):
            name = name.decode("ascii")
        self.name = name
        if channel_layer:
            self.channel_layer = channel_layer
        else:
            self.channel_layer = channel_layers[alias]

    def send(self, content):
        """
        Send a message over the channel - messages are always dicts.
        """
        if not isinstance(content, dict):
            raise ValueError("You can only send dicts as content on channels.")
        self.channel_layer.send(self.name, content)

    def __str__(self):
        return self.name


class Group(object):
    """
    A group of channels that can be messaged at once, and that expire out
    of the group after an expiry time (keep re-adding to keep them in).
    """

    def __init__(self, name, alias=DEFAULT_CHANNEL_LAYER, channel_layer=None):
        if isinstance(name, six.binary_type):
            name = name.decode("ascii")
        self.name = name
        if channel_layer:
            self.channel_layer = channel_layer
        else:
            self.channel_layer = channel_layers[alias]

    def add(self, channel):
        if isinstance(channel, Channel):
            channel = channel.name
        self.channel_layer.group_add(self.name, channel)

    def discard(self, channel):
        if isinstance(channel, Channel):
            channel = channel.name
        self.channel_layer.group_discard(self.name, channel)

    def send(self, content):
        if not isinstance(content, dict):
            raise ValueError("You can only send dicts as content on channels.")
        self.channel_layer.send_group(self.name, content)
