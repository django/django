import functools
from django.utils import six
from .utils import name_that_thing

class ConsumerRegistry(object):
    """
    Manages the available consumers in the project and which channels they
    listen to.

    Generally a single project-wide instance of this is used.
    """

    def __init__(self):
        self.consumers = {}

    def add_consumer(self, consumer, channels):
        for channel in channels:
            if channel in self.consumers:
                raise ValueError("Cannot register consumer %s - channel %r already consumed by %s" % (
                    name_that_thing(consumer),
                    channel,
                    name_that_thing(self.consumers[channel]),
                ))
            self.consumers[channel] = consumer

    def consumer(self, channels):
        """
        Decorator that registers a function as a consumer.
        """
        if isinstance(channels, six.string_types):
            channels = [channels]
        def inner(func):
            self.add_consumer(func, channels)
            return func
        return inner

    def all_channel_names(self):
        return self.consumers.keys()

    def consumer_for_channel(self, channel):
        try:
            return self.consumers[channel]
        except KeyError:
            return None
