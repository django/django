# Settings for channels specifically
from testproject.settings.base import *

INSTALLED_APPS += (
    'channels',
)

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'asgi_rabbitmq.RabbitmqChannelLayer',
        'ROUTING': 'testproject.urls.channel_routing',
        'CONFIG': {
            'url': os.environ.get(
                'RABBITMQ_URL',
                'amqp://guest:guest@localhost:5672/%2F',
            ),
        },
    },
}
