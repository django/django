from .channel import Channel


class Message(object):
    """
    Represents a message sent over a Channel.

    The message content is a dict called .content, while
    reply_channel is an optional extra attribute representing a channel
    to use to reply to this message's end user, if that makes sense.
    """

    class Requeue(Exception):
        """
        Raise this while processing a message to requeue it back onto the
        channel. Useful if you're manually ensuring partial ordering, etc.
        """
        pass

    def __init__(self, content, channel, channel_backend, reply_channel=None):
        self.content = content
        self.channel = channel
        self.channel_backend = channel_backend
        if reply_channel:
            self.reply_channel = Channel(reply_channel, channel_backend=self.channel_backend)
