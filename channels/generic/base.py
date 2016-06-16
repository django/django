from __future__ import unicode_literals
from channels.sessions import channel_session
from channels.auth import channel_session_user


class BaseConsumer(object):
    """
    Base class-based consumer class. Provides the mechanisms to be a direct
    routing object and a few other things.

    Class-based consumers should be used with route_class in routing, like so::

        from channels import route_class
        routing = [
            route_class(JsonWebsocketConsumer, path=r"^/liveblog/(?P<slug>[^/]+)/"),
        ]
    """

    method_mapping = {}
    channel_session = False
    channel_session_user = False

    def __init__(self, message, **kwargs):
        """
        Constructor, called when a new message comes in (the consumer is
        the uninstantiated class, so calling it creates it)
        """
        self.message = message
        self.dispatch(message, **kwargs)

    @classmethod
    def channel_names(cls):
        """
        Returns a list of channels this consumer will respond to, in our case
        derived from the method_mapping class attribute.
        """
        return set(cls.method_mapping.keys())

    def get_handler(self, message, **kwargs):
        """
        Return handler uses method_mapping to return the right method to call.
        """
        handler = getattr(self, self.method_mapping[message.channel.name])
        if self.channel_session_user:
            return channel_session_user(handler)
        elif self.channel_session:
            return channel_session(handler)
        else:
            return handler

    def dispatch(self, message, **kwargs):
        """
        Call handler with the message and all keyword arguments.
        """
        return self.get_handler(message, **kwargs)(message, **kwargs)
