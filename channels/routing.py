from __future__ import unicode_literals

import importlib
import re

from django.core.exceptions import ImproperlyConfigured
from django.utils import six

from .utils import name_that_thing


class Router(object):
    """
    Manages the available consumers in the project and which channels they
    listen to.

    Generally this is attached to a backend instance as ".router"

    Anything can be a routable object as long as it provides a match()
    method that either returns (callable, kwargs) or None.
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
        # We also add a no-op websocket.connect consumer to the bottom, as the
        # spec requires that this is consumed, but Channels does not. Any user
        # consumer will override this one. Same for websocket.receive.
        self.add_route(Route("websocket.connect", connect_consumer))
        self.add_route(Route("websocket.receive", null_consumer))
        self.add_route(Route("websocket.disconnect", null_consumer))

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

    def __init__(self, channels, consumer, **kwargs):
        # Get channels, make sure it's a list of unicode strings
        if isinstance(channels, six.string_types):
            channels = [channels]
        self.channels = [
            channel.decode("ascii") if isinstance(channel, six.binary_type) else channel
            for channel in channels
        ]
        # Get consumer, optionally importing it
        self.consumer = self._resolve_consumer(consumer)
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

    def _resolve_consumer(self, consumer):
        """
        Turns the consumer from a string into an object if it's a string,
        passes it through otherwise.
        """
        if isinstance(consumer, six.string_types):
            module_name, variable_name = consumer.rsplit(".", 1)
            try:
                consumer = getattr(importlib.import_module(module_name), variable_name)
            except (ImportError, AttributeError):
                raise ImproperlyConfigured("Cannot import consumer %r" % consumer)
        return consumer

    def match(self, message):
        """
        Checks to see if we match the Message object. Returns
        (consumer, kwargs dict) if it matches, None otherwise
        """
        # Check for channel match first of all
        if message.channel.name not in self.channels:
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
        return set(self.channels)

    def __str__(self):
        return "%s %s -> %s" % (
            "/".join(self.channels),
            "" if not self.filters else "(%s)" % (
                ", ".join("%s=%s" % (n, v.pattern) for n, v in self.filters.items())
            ),
            name_that_thing(self.consumer),
        )


class RouteClass(Route):
    """
    Like Route, but targets a class-based consumer rather than a functional
    one, meaning it looks for a (class) method called "channels()" on the
    object rather than having a single channel passed in.
    """

    def __init__(self, consumer, **kwargs):
        # Check the consumer provides a method_channels
        consumer = self._resolve_consumer(consumer)
        if not hasattr(consumer, "channel_names") or not callable(consumer.channel_names):
            raise ValueError("The consumer passed to RouteClass has no valid channel_names method")
        # Call super with list of channels
        super(RouteClass, self).__init__(consumer.channel_names(), consumer, **kwargs)


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


def null_consumer(*args, **kwargs):
    """
    Standard no-op consumer.
    """


def connect_consumer(message, *args, **kwargs):
    """
    Accept-all-connections websocket.connect consumer
    """
    message.reply_channel.send({"accept": True})


# Lowercase standard to match urls.py
route = Route
route_class = RouteClass
include = Include
