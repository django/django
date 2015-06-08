import functools

from django.utils import six

from .utils import name_that_thing


class ConsumerRegistry(object):
    """
    Manages the available consumers in the project and which channels they
    listen to.

    Generally this is attached to a backend instance as ".registry"
    """

    def __init__(self):
        self.consumers = {}

    def add_consumer(self, consumer, channels):
        # Upconvert if you just pass in a string
        if isinstance(channels, six.string_types):
            channels = [channels]
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
