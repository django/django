import os
from channels.asgi import get_channel_layer

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testproject.settings.channels")
channel_layer = get_channel_layer()
