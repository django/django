from __future__ import unicode_literals

import django
from django.conf import settings
from django.utils.module_loading import import_string

from .routing import Router
from .utils import name_that_thing


class InvalidChannelLayerError(ValueError):
    pass


class ChannelLayerManager(object):
    """
    Takes a settings dictionary of backends and initialises them on request.
    """

    def __init__(self):
        self.backends = {}

    @property
    def configs(self):
        # Lazy load settings so we can be imported
        return getattr(settings, "CHANNEL_LAYERS", {})

    def make_backend(self, name):
        # Load the backend class
        try:
            backend_class = import_string(self.configs[name]['BACKEND'])
        except KeyError:
            raise InvalidChannelLayerError("No BACKEND specified for %s" % name)
        except ImportError:
            raise InvalidChannelLayerError(
                "Cannot import BACKEND %r specified for %s" % (self.configs[name]['BACKEND'], name)
            )
        # Get routing
        try:
            routing = self.configs[name]['ROUTING']
        except KeyError:
            raise InvalidChannelLayerError("No ROUTING specified for %s" % name)
        # Initialise and pass config
        asgi_layer = backend_class(**self.configs[name].get("CONFIG", {}))
        return ChannelLayerWrapper(
            channel_layer=asgi_layer,
            alias=name,
            routing=routing,
        )

    def __getitem__(self, key):
        if key not in self.backends:
            self.backends[key] = self.make_backend(key)
        return self.backends[key]

    def __contains__(self, key):
        return key in self.configs


class ChannelLayerWrapper(object):
    """
    Top level channel layer wrapper, which contains both the ASGI channel
    layer object as well as alias and routing information specific to Django.
    """

    def __init__(self, channel_layer, alias, routing):
        self.channel_layer = channel_layer
        self.alias = alias
        self.routing = routing
        self.router = Router(self.routing)

    def __getattr__(self, name):
        return getattr(self.channel_layer, name)

    def __str__(self):
        return "%s (%s)" % (self.alias, name_that_thing(self.channel_layer))

    def local_only(self):
        # TODO: Can probably come up with a nicer check?
        return "inmemory" in self.channel_layer.__class__.__module__


def get_channel_layer(alias="default"):
    """
    Returns the raw ASGI channel layer for this project.
    """
    if django.VERSION[1] > 9:
        django.setup(set_prefix=False)
    else:
        django.setup()
    return channel_layers[alias].channel_layer


# Default global instance of the channel layer manager
channel_layers = ChannelLayerManager()
