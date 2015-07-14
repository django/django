import functools
import hashlib
from importlib import import_module

from django.conf import settings
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

def send_channel_session(func):
    """
    Provides a session-like object called "channel_session" to consumers
    as a message attribute that will auto-persist across consumers with
    the same incoming "send_channel" value.
    """
    @functools.wraps(func)
    def inner(*args, **kwargs):
        # Make sure there's a send_channel in kwargs
        if "send_channel" not in kwargs:
            raise ValueError("No send_channel sent to consumer; this decorator can only be used on messages containing it.")
        # Turn the send_channel into a valid session key length thing.
        # We take the last 24 bytes verbatim, as these are the random section,
        # and then hash the remaining ones onto the start, and add a prefix
        # TODO: See if there's a better way of doing this
        session_key = "skt" + hashlib.md5(kwargs['send_channel'][:-24]).hexdigest()[:8] + kwargs['send_channel'][-24:]
        # Make a session storage
        session_engine = import_module(settings.SESSION_ENGINE)
        session = session_engine.SessionStore(session_key=session_key)
        # If the session does not already exist, save to force our session key to be valid
        if not session.exists(session.session_key):
            session.save()
        kwargs['channel_session'] = session
        # Run the consumer
        result = func(*args, **kwargs)
        # Persist session if needed (won't be saved if error happens)
        if session.modified:
            session.save()
        return result
    return inner
