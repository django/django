from __future__ import unicode_literals

import copy
import threading
import time

from .channel import Channel
from .signals import consumer_finished, consumer_started


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

    Will retry when it sees ChannelFull up to a limit; if you want more control
    over this, change to `immediately=True` in your send method and handle it
    yourself.
    """

    threadlocal = threading.local()

    retry_time = 2  # seconds
    retry_interval = 0.2  # seconds

    def prepare(self, **kwargs):
        """
        Sets the message store up to receive messages.
        """
        self.threadlocal.messages = []

    @property
    def active(self):
        """
        Returns if the pending message store can be used or not
        (it can only be used inside consumers)
        """
        return hasattr(self.threadlocal, "messages")

    def append(self, sender, message):
        self.threadlocal.messages.append((sender, message))

    def send_and_flush(self, **kwargs):
        for sender, message in getattr(self.threadlocal, "messages", []):
            # Loop until the retry time limit is hit
            started = time.time()
            while time.time() - started < self.retry_time:
                try:
                    sender.send(message, immediately=True)
                except sender.channel_layer.ChannelFull:
                    time.sleep(self.retry_interval)
                    continue
                else:
                    break
            # If we didn't break out, we failed to send, so do a nice exception
            else:
                raise RuntimeError(
                    "Failed to send queued message to %s after retrying for %.2fs.\n"
                    "You need to increase the consumption rate on this channel, its capacity,\n"
                    "or handle the ChannelFull exception yourself after adding\n"
                    "immediately=True to send()." % (sender, self.retry_time)
                )
        delattr(self.threadlocal, "messages")


pending_message_store = PendingMessageStore()
consumer_started.connect(pending_message_store.prepare)
consumer_finished.connect(pending_message_store.send_and_flush)
