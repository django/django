import functools

from django.contrib import auth

from .decorators import channel_session, http_session


def transfer_user(from_session, to_session):
    """
    Transfers user from HTTP session to channel session.
    """
    to_session[auth.BACKEND_SESSION_KEY] = from_session[auth.BACKEND_SESSION_KEY]
    to_session[auth.SESSION_KEY] = from_session[auth.SESSION_KEY]
    to_session[auth.HASH_SESSION_KEY] = from_session[auth.HASH_SESSION_KEY]


def channel_session_user(func):
    """
    Presents a message.user attribute obtained from a user ID in the channel
    session, rather than in the http_session. Turns on channel session implicitly.
    """
    @channel_session
    @functools.wraps(func)
    def inner(message, *args, **kwargs):
        # If we didn't get a session, then we don't get a user
        if not hasattr(message, "channel_session"):
            raise ValueError("Did not see a channel session to get auth from")
        if message.channel_session is None:
            message.user = None
        # Otherwise, be a bit naughty and make a fake Request with just
        # a "session" attribute (later on, perhaps refactor contrib.auth to
        # pass around session rather than request)
        else:
            fake_request = type("FakeRequest", (object, ), {"session": message.channel_session})
            message.user = auth.get_user(fake_request)
        # Run the consumer
        return func(message, *args, **kwargs)
    return inner


def http_session_user(func):
    """
    Wraps a HTTP or WebSocket consumer (or any consumer of messages
    that provides a "COOKIES" attribute) to provide both a "session"
    attribute and a "user" attibute, like AuthMiddleware does.

    This runs http_session() to get a session to hook auth off of.
    If the user does not have a session cookie set, both "session"
    and "user" will be None.
    """
    @http_session
    @functools.wraps(func)
    def inner(message, *args, **kwargs):
        # If we didn't get a session, then we don't get a user
        if not hasattr(message, "http_session"):
            raise ValueError("Did not see a http session to get auth from")
        if message.http_session is None:
            message.user = None
        # Otherwise, be a bit naughty and make a fake Request with just
        # a "session" attribute (later on, perhaps refactor contrib.auth to
        # pass around session rather than request)
        else:
            fake_request = type("FakeRequest", (object, ), {"session": message.http_session})
            message.user = auth.get_user(fake_request)
        # Run the consumer
        return func(message, *args, **kwargs)
    return inner
