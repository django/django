# Settings for channels specifically
from testproject.settings.base import *

INSTALLED_APPS += (
    'channels',
)

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "asgi_ipc.IPCChannelLayer",
        "ROUTING": "testproject.urls.channel_routing",
    },
}
