from __future__ import unicode_literals

import re
import importlib

from django.core.exceptions import ImproperlyConfigured
from django.utils import six

from .utils import name_that_thing


class Router(object):
    """
    Manages the available consumers in the project and which channels they
    listen to.

    Generally this is attached to a backend instance as ".router"
    """

    def __init__(self, routing):
        # Use a blank include as the root item
        self.root = Include(routing)
        # Cache channel names
        self.channels = self.root.channel_names()

    def add_route(self, route):
        """
        Adds a single raw Route to us at the end of the resolution list.
        """
        self.root.routing.append(route)
        self.channels = self.root.channel_names()

    def match(self, message):
        """
        Runs through our routing and tries to find a consumer that matches
        the message/channel. Returns (consumer, extra_kwargs) if it does,
        and None if it doesn't.
        """
        # TODO: Maybe we can add some kind of caching in here if we can hash
        # the message with only matchable keys faster than the search?
        return self.root.match(message)

    def check_default(self, http_consumer=None):
        """
        Adds default handlers for Django's default handling of channels.
        """
        # We just add the default Django route to the bottom; if the user
        # has defined another http.request handler, it'll get hit first and run.
        # Inner import here to avoid circular import; this function only gets
        # called once, thankfully.
        from .handler import ViewConsumer
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

    @classmethod
    def normalise_re_arg(cls, value):
        """
        Normalises regular expression patterns and string inputs to Unicode.
        """
        if isinstance(value, six.binary_type):
            return value.decode("ascii")
        else:
            return value


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
            name: re.compile(Router.normalise_re_arg(value))
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
            match = value.match(Router.normalise_re_arg(message[name]))
            # Any match failure means we pass
            if match:
                call_args.update(match.groupdict())
            else:
                return None
        return self.consumer, call_args

    def channel_names(self):
        """
        Returns the channel names this route listens on
        """
        return {self.channel, }

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
        self.prefixes = {
            name: re.compile(Router.normalise_re_arg(value))
            for name, value in kwargs.items()
        }

    def match(self, message):
        """
        Tries to match the message against our own prefixes, possibly modifying
        what we send to included things, then tries all included items.
        """
        # Check our prefixes match. Do this against a copy of the message so
        # we can write back any changed values.
        message = message.copy()
        call_args = {}
        for name, prefix in self.prefixes.items():
            if name not in message:
                return None
            value = Router.normalise_re_arg(message[name])
            match = prefix.match(value)
            # Any match failure means we pass
            if match:
                call_args.update(match.groupdict())
                # Modify the message value to remove the part we matched on
                message[name] = value[match.end():]
            else:
                return None
        # Alright, if we got this far our prefixes match. Try all of our
        # included objects now.
        for entry in self.routing:
            match = entry.match(message)
            if match is not None:
                call_args.update(match[1])
                return match[0], call_args
        # Nothing matched :(
        return None

    def channel_names(self):
        """
        Returns the channel names this route listens on
        """
        result = set()
        for entry in self.routing:
            result.update(entry.channel_names())
        return result


# Lowercase standard to match urls.py
route = Route
include = Include
