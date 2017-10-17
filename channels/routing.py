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
    and HTTP.
    """

    def __init__(self, routes):
        self.routes = routes

    def __call__(self, scope):
        # Get the path
        path = scope.get("path", None)
        if path is None:
            raise ValueError("No 'path' key in connection scope, cannot route URLs")
        # Run through the routes we have until one matches
        for route in self.routes:
            match = route.match(path)
            if match is not None:
                return match(scope)
        else:
            raise ValueError("No route found for path %r." % path)


class URLRoute:
    """
    Represents a URL based route to an application
    """

    def __init__(self, regex, application):
        self.application = application
        self.regex = re.compile(regex)

    def match(self, url):
        if self.regex.match(url.lstrip("/")):
            return self.application

route = URLRoute
