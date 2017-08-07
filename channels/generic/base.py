from __future__ import unicode_literals

from ..auth import channel_session_user
from ..routing import route_class
from ..sessions import channel_session


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

    def __init__(self, type, reply, channel_layer, consumer_channel, **kwargs):
        """
        Constructor, called when the socket is established.
        """
        self.type = type
        self.reply = reply
        self.channel_layer = channel_layer
        self.consumer_channel = consumer_channel
        self.kwargs = kwargs

    def __call__(self, message):
        handler = getattr(self, self.method_mapping[message['type']])
        handler(message)

    @classmethod
    def as_route(cls, attrs=None, **kwargs):
        """
        Shortcut function to create route with filters (kwargs)
        to direct to a class-based consumer with given class attributes (attrs)
        """
        _cls = cls
        if attrs:
            assert isinstance(attrs, dict), 'attrs must be a dict'
            _cls = type(cls.__name__, (cls,), attrs)
        return route_class(_cls, **kwargs)
