# Settings for channels specifically
from testproject.settings.base import *

INSTALLED_APPS += ('channels',)

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'asgi_rabbitmq.RabbitmqChannelLayer',
        'ROUTING': 'testproject.urls.channel_routing',
        'CONFIG': {
            'url': os.environ['RABBITMQ_URL'],
        },
    },
}
