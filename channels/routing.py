from __future__ import unicode_literals

import importlib

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.urls.exceptions import Resolver404

from channels.http import AsgiHandler

try:
    from django.urls.resolvers import URLResolver
except ImportError:  # Django 1.11
    from django.urls import RegexURLResolver as URLResolver


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


def route_pattern_match(route, path):
    """
    Backport of RegexPattern.match for Django versions before 2.0. Returns
    the remaining path and positional and keyword arguments matched.
    """
    if hasattr(route, "pattern"):
        match = route.pattern.match(path)
        if match:
            path, args, kwargs = match
            kwargs.update(route.default_args)
            return path, args, kwargs
        return match

    # Django<2.0. No converters... :-(
    match = route.regex.search(path)
    if match:
        # If there are any named groups, use those as kwargs, ignoring
        # non-named groups. Otherwise, pass all non-named arguments as
        # positional arguments.
        kwargs = match.groupdict()
        args = () if kwargs else match.groups()
        if kwargs is not None:
            kwargs.update(route.default_args)
        return path[match.end():], args, kwargs
    return None


class URLRouter:
    """
    Routes to different applications/consumers based on the URL path.

    Works with anything that has a ``path`` key, but intended for WebSocket
    and HTTP. Uses Django's django.conf.urls objects for resolution -
    url() or path().
    """

    #: This router wants to do routing based on scope[path] or
    #: scope[path_remaining]. ``path()`` entries in URLRouter should not be
    #: treated as endpoints (ended with ``$``), but similar to ``include()``.
    _path_routing = True

    def __init__(self, routes):
        self.routes = routes
        # Django 2 introduced path(); older routes have no "pattern" attribute
        if self.routes and hasattr(self.routes[0], "pattern"):
            for route in self.routes:
                # The inner ASGI app wants to do additional routing, route
                # must not be an endpoint
                if getattr(route.callback, "_path_routing", False) is True:
                    route.pattern._is_endpoint = False

        for route in self.routes:
            if not route.callback and isinstance(route, URLResolver):
                raise ImproperlyConfigured(
                    "%s: include() is not supported in URLRouter. Use nested"
                    " URLRouter instances instead." % (route,)
                )

    def __call__(self, scope):
        # Get the path
        path = scope.get("path_remaining", scope.get("path", None))
        if path is None:
            raise ValueError("No 'path' key in connection scope, cannot route URLs")
        # Remove leading / to match Django's handling
        path = path.lstrip("/")
        # Run through the routes we have until one matches
        for route in self.routes:
            try:
                match = route_pattern_match(route, path)
                if match:
                    new_path, args, kwargs = match
                    # Add args or kwargs into the scope
                    outer = scope.get("url_route", {})
                    return route.callback(dict(
                        scope,
                        path_remaining=new_path,
                        url_route={
                            "args": outer.get("args", ()) + args,
                            "kwargs": {**outer.get("kwargs", {}), **kwargs},
                        },
                    ))
            except Resolver404 as e:
                pass
        else:
            if "path_remaining" in scope:
                raise Resolver404("No route found for path %r." % path)
            # We are the outermost URLRouter
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
