__version__ = "2.0a1"

default_app_config = 'channels.apps.ChannelsConfig'
DEFAULT_CHANNEL_LAYER = 'default'

try:
    from .asgi import channel_layers  # NOQA isort:skip
    from .channel import Channel, Group  # NOQA isort:skip
    from .routing import route, route_class, include  # NOQA isort:skip
except ImportError:  # No django installed, allow vars to be read
    pass
