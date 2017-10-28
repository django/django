from __future__ import unicode_literals

import re

from channels.http import AsgiHandler


"""
All Routing instances inside this file are also valid ASGI applications - with
new Channels routing, whatever you end up with as the top level object is just
served up as the "ASGI application".
"""


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
