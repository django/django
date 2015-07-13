import functools

from django.utils import six

from channels import channel_backends, DEFAULT_CHANNEL_BACKEND


def consumer(*channels, **kwargs):
    """
    Decorator that registers a function as a consumer.
    """
    # We can't put a kwarg after *args in py2
    alias = kwargs.get("alias", DEFAULT_CHANNEL_BACKEND)
    # Upconvert if you just pass in a string
    if isinstance(channels, six.string_types):
        channels = [channels]
    # Get the channel 
    channel_backend = channel_backends[alias]
    # Return a function that'll register whatever it wraps
    def inner(func):
        channel_backend.registry.add_consumer(func, channels)
        return func
    return inner


# TODO: Sessions, auth
