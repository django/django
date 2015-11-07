import importlib
from django.utils import six
from django.core.exceptions import ImproperlyConfigured
from .utils import name_that_thing


class ConsumerRegistry(object):
    """
    Manages the available consumers in the project and which channels they
    listen to.

    Generally this is attached to a backend instance as ".registry"
    """

    def __init__(self, routing=None):
        self.consumers = {}
        # Add basic internal consumers
        self.add_consumer(self.echo_consumer, ["__channels__.echo"])
        # Initialise with any routing that was passed in
        if routing:
            # If the routing was a string, import it
            if isinstance(routing, six.string_types):
                module_name, variable_name = routing.rsplit(".", 1)
                try:
                    routing = getattr(importlib.import_module(module_name), variable_name)
                except (ImportError, AttributeError) as e:
                    raise ImproperlyConfigured("Cannot import channel routing %r: %s" % (routing, e))
            # Load consumers into us
            for channel, handler in routing.items():
                self.add_consumer(handler, [channel])

    def add_consumer(self, consumer, channels):
        # Upconvert if you just pass in a string for channels
        if isinstance(channels, six.string_types):
            channels = [channels]
        # Import any consumer referenced as string
        if isinstance(consumer, six.string_types):
            module_name, variable_name = consumer.rsplit(".", 1)
            try:
                consumer = getattr(importlib.import_module(module_name), variable_name)
            except (ImportError, AttributeError):
                raise ImproperlyConfigured("Cannot import consumer %r" % consumer)
        # Register on each channel, checking it's unique
        for channel in channels:
            if channel in self.consumers:
                raise ValueError("Cannot register consumer %s - channel %r already consumed by %s" % (
                    name_that_thing(consumer),
                    channel,
                    name_that_thing(self.consumers[channel]),
                ))
            self.consumers[channel] = consumer

    def all_channel_names(self):
        return self.consumers.keys()

    def consumer_for_channel(self, channel):
        try:
            return self.consumers[channel]
        except KeyError:
            return None

    def echo_consumer(self, message):
        """
        Implements the echo message standard.
        """
        message.reply_channel.send({
            "content": message.content.get("content", None),
        })
