from __future__ import unicode_literals

import re
import importlib

from django.core.exceptions import ImproperlyConfigured
from django.utils import six

from .handler import ViewConsumer
from .utils import name_that_thing


class Router(object):
    """
    Manages the available consumers in the project and which channels they
    listen to.

    Generally this is attached to a backend instance as ".router"
    """

    def __init__(self, routing):
        # Resolve routing into a list if it's a dict or string
        routing = self.resolve_routing(routing)
        # Expand those entries recursively into a flat list of Routes
        self.routing = []
        for entry in routing:
            self.routing.extend(entry.expand_routes())
        # Now go through that list and collect channel names into a set
        self.channels = {
            route.channel
            for route in self.routing
        }

    def add_route(self, route):
        """
        Adds a single raw Route to us at the end of the resolution list.
        """
        self.routing.append(route)
        self.channels.add(route.channel)

    def match(self, message):
        """
        Runs through our routing and tries to find a consumer that matches
        the message/channel. Returns (consumer, extra_kwargs) if it does,
        and None if it doesn't.
        """
        # TODO: Maybe we can add some kind of caching in here if we can hash
        # the message with only matchable keys faster than the search?
        for route in self.routing:
            match = route.match(message)
            if match is not None:
                return match
        return None

    def check_default(self, http_consumer=None):
        """
        Adds default handlers for Django's default handling of channels.
        """
        # We just add the default Django route to the bottom; if the user
        # has defined another http.request handler, it'll get hit first and run.
        self.add_route(Route("http.request", http_consumer or ViewConsumer()))

    @classmethod
    def resolve_routing(cls, routing):
        """
        Takes a routing - if it's a string, it imports it, and if it's a
        dict, converts it to a list of route()s. Used by this class and Include.
        """
        # If the routing was a string, import it
        if isinstance(routing, six.string_types):
            module_name, variable_name = routing.rsplit(".", 1)
            try:
                routing = getattr(importlib.import_module(module_name), variable_name)
            except (ImportError, AttributeError) as e:
                raise ImproperlyConfigured("Cannot import channel routing %r: %s" % (routing, e))
        # If the routing is a dict, convert it
        if isinstance(routing, dict):
            routing = [
                Route(channel, consumer)
                for channel, consumer in routing.items()
            ]
        return routing


class Route(object):
    """
    Represents a route to a single consumer, with a channel name
    and optional message parameter matching.
    """

    def __init__(self, channel, consumer, **kwargs):
        # Get channel, make sure it's a unicode string
        self.channel = channel
        if isinstance(self.channel, six.binary_type):
            self.channel = self.channel.decode("ascii")
        # Get consumer, optionally importing it
        if isinstance(consumer, six.string_types):
            module_name, variable_name = consumer.rsplit(".", 1)
            try:
                consumer = getattr(importlib.import_module(module_name), variable_name)
            except (ImportError, AttributeError):
                raise ImproperlyConfigured("Cannot import consumer %r" % consumer)
        self.consumer = consumer
        # Compile filter regexes up front
        self.filters = {
            name: re.compile(value)
            for name, value in kwargs.items()
        }
        # Check filters don't use positional groups
        for name, regex in self.filters.items():
            if regex.groups != len(regex.groupindex):
                raise ValueError(
                    "Filter for %s on %s contains positional groups; "
                    "only named groups are allowed." % (
                        name,
                        self,
                    )
                )

    def match(self, message):
        """
        Checks to see if we match the Message object. Returns
        (consumer, kwargs dict) if it matches, None otherwise
        """
        # Check for channel match first of all
        if message.channel.name != self.channel:
            return None
        # Check each message filter and build consumer kwargs as we go
        call_args = {}
        for name, value in self.filters.items():
            if name not in message:
                return None
            match = re.match(value, message[name])
            # Any match failure means we pass
            if match:
                call_args.update(match.groupdict())
            else:
                return None
        return self.consumer, call_args

    def expand_routes(self):
        """
        Expands this route into a list of just itself.
        """
        return [self]

    def add_prefixes(self, prefixes):
        """
        Returns a new Route with the given prefixes added to our filters.
        """
        new_filters = {}
        # Copy over our filters adding any prefixes
        for name, value in self.filters.items():
            if name in prefixes:
                if not value.pattern.startswith("^"):
                    raise ValueError("Cannot add prefix for %s on %s as inner value does not start with ^" % (
                        name,
                        self,
                    ))
                if "$" in prefixes[name]:
                    raise ValueError("Cannot add prefix for %s on %s as prefix contains $ (end of line match)" % (
                        name,
                        self,
                    ))
                new_filters[name] = re.compile(prefixes[name] + value.pattern.lstrip("^"))
            else:
                new_filters[name] = value
        # Now add any prefixes that are by themselves so they're still enforced
        for name, prefix in prefixes.items():
            if name not in new_filters:
                new_filters[name] = prefix
        # Return new copy
        return self.__class__(
            self.channel,
            self.consumer,
            **new_filters
        )

    def __str__(self):
        return "%s %s -> %s" % (
            self.channel,
            "" if not self.filters else "(%s)" % (
                ", ".join("%s=%s" % (n, v.pattern) for n, v in self.filters.items())
            ),
            name_that_thing(self.consumer),
        )


class Include(object):
    """
    Represents an inclusion of another routing list in another file.
    Will automatically modify message match filters to add prefixes,
    if specified.
    """

    def __init__(self, routing, **kwargs):
        self.routing = Router.resolve_routing(routing)
        self.prefixes = kwargs
        # Sanity check prefix regexes
        for name, value in self.prefixes.items():
            if not value.startswith("^"):
                raise ValueError("Include prefix for %s must start with the ^ character." % name)

    def expand_routes(self):
        """
        Expands this Include into a list of routes, first recursively expanding
        and then adding on prefixes to filters if specified.
        """
        # First, expand our own subset of routes, to get a list of Route objects
        routes = []
        for entry in self.routing:
            routes.extend(entry.expand_routes())
        # Then, go through those and add any prefixes we have.
        routes = [route.add_prefixes(self.prefixes) for route in routes]
        return routes


# Lowercase standard to match urls.py
route = Route
include = Include
