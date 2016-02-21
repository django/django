__version__ = "0.9"

default_app_config = 'channels.apps.ChannelsConfig'
DEFAULT_CHANNEL_LAYER = 'default'

from .asgi import channel_layers  # NOQA isort:skip
from .channel import Channel, Group  # NOQA isort:skip
