from __future__ import unicode_literals

import importlib
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from channels.http import AsgiHandler


"""
All Routing instances inside this file are also valid ASGI applications - with
new Channels routing, whatever you end up with as the top level object is just
served up as the "ASGI application".
"""


def get_default_application():
    """
    Gets the default application, set in the ASGI_APPLICATION setting.
    """
    try:
        path, name = settings.ASGI_APPLICATION.rsplit(".", 1)
    except (ValueError, AttributeError):
        raise ImproperlyConfigured("Cannot find ASGI_APPLICATION setting.")
    try:
        module = importlib.import_module(path)
    except ImportError:
        raise ImproperlyConfigured("Cannot import ASGI_APPLICATION module %r" % path)
    try:
        value = getattr(module, name)
    except AttributeError:
        raise ImproperlyConfigured("Cannot find %r in ASGI_APPLICATION module %s" % (name, path))
    return value


class ProtocolTypeRouter:
    """
    Takes a mapping of protocol type names to other Application instances,
    and dispatches to the right one based on protocol name (or raises an error)
    """

    def __init__(self, application_mapping):
        self.application_mapping = application_mapping
        if "http" not in self.application_mapping:
            self.application_mapping["http"] = AsgiHandler

    def __call__(self, scope):
        if scope["type"] in self.application_mapping:
            return self.application_mapping[scope["type"]](scope)
        else:
            raise ValueError("No application configured for scope type %r" % scope["type"])


class URLRouter:
    """
    Routes to different applications/consumers based on the URL path.

    Works with anything that has a ``path`` key, but intended for WebSocket
    and HTTP. Uses Django's django.conf.urls objects for resolution -
    url() or path().
    """

    def __init__(self, routes):
        self.routes = routes

    def __call__(self, scope):
        # Get the path
        path = scope.get("path", None)
        if path is None:
            raise ValueError("No 'path' key in connection scope, cannot route URLs")
        # Remove leading / to match Django's handling
        path = path.lstrip("/")
        # Run through the routes we have until one matches
        for route in self.routes:
            match = route.resolve(path)
            if match is not None:
                # Add args or kwargs into the scope
                scope["url_route"] = {
                    "args": match.args,
                    "kwargs": match.kwargs,
                }
                return match.func(scope)
        else:
            raise ValueError("No route found for path %r." % path)


class ChannelNameRouter:
    """
    Maps to different applications based on a "channel" key in the scope
    (intended for the Channels worker mode)
    """

    def __init__(self, application_mapping):
        self.application_mapping = application_mapping

    def __call__(self, scope):
        if "channel" not in scope:
            raise ValueError(
                "ChannelNameRouter got a scope without a 'channel' key. " +
                "Did you make sure it's only being used for 'channel' type messages?"
            )
        if scope["channel"] in self.application_mapping:
            return self.application_mapping[scope["channel"]](scope)
        else:
            raise ValueError("No application configured for channel name %r" % scope["channel"])
