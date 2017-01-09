from __future__ import unicode_literals

import copy
import threading

from .channel import Channel
from .signals import consumer_finished


class Message(object):
    """
    Represents a message sent over a Channel.

    The message content is a dict called .content, while
    reply_channel is an optional extra attribute representing a channel
    to use to reply to this message's end user, if that makes sense.
    """

    def __init__(self, content, channel_name, channel_layer):
        self.content = content
        self.channel = Channel(
            channel_name,
            channel_layer=channel_layer,
        )
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

    def __setitem__(self, key, value):
        self.content[key] = value

    def __contains__(self, key):
        return key in self.content

    def keys(self):
        return self.content.keys()

    def values(self):
        return self.content.values()

    def items(self):
        return self.content.items()

    def get(self, key, default=None):
        return self.content.get(key, default)

    def copy(self):
        """
        Returns a safely content-mutable copy of this Message.
        """
        return self.__class__(
            copy.deepcopy(self.content),
            self.channel.name,
            self.channel_layer,
        )


class PendingMessageStore(object):
    """
    Singleton object used for storing pending messages that should be sent
    to a channel or group when a consumer finishes.
    """

    threadlocal = threading.local()

    def append(self, sender, message):
        if not hasattr(self.threadlocal, "messages"):
            self.threadlocal.messages = []
        self.threadlocal.messages.append((sender, message))

    def send_and_flush(self, **kwargs):
        for sender, message in getattr(self.threadlocal, "messages", []):
            sender.send(message, immediately=True)
        self.threadlocal.messages = []


pending_message_store = PendingMessageStore()
consumer_finished.connect(pending_message_store.send_and_flush)
