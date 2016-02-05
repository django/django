from __future__ import unicode_literals

from .channel import Channel


class Message(object):
    """
    Represents a message sent over a Channel.

    The message content is a dict called .content, while
    reply_channel is an optional extra attribute representing a channel
    to use to reply to this message's end user, if that makes sense.
    """

    def __init__(self, content, channel, channel_layer):
        self.content = content
        self.channel = channel
        self.channel_layer = channel_layer
        if content.get("reply_channel", None):
            self.reply_channel = Channel(
                content["reply_channel"],
                channel_layer=self.channel_layer,
            )
        else:
            self.reply_channel = None

    def __getitem__(self, key):
        return self.content[key]

    def get(self, key, default=None):
        return self.content.get(key, default)
