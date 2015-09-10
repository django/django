import functools
import hashlib
from importlib import import_module

from django.conf import settings
from django.utils import six
from django.contrib import auth

from channels import channel_backends, DEFAULT_CHANNEL_BACKEND


def http_session(func):
    """
    Wraps a HTTP or WebSocket consumer (or any consumer of messages
    that provides a "COOKIES" or "GET" attribute) to provide a "session"
    attribute that behaves like request.session; that is, it's hung off of
    a per-user session key that is saved in a cookie or passed as the
    "session_key" GET parameter.

    It won't automatically create and set a session cookie for users who
    don't have one - that's what SessionMiddleware is for, this is a simpler
    read-only version for more low-level code.

    If a user does not have a session we can inflate, the "session" attribute will
    be None, rather than an empty session you can write to.
    """
    @functools.wraps(func)
    def inner(message, *args, **kwargs):
        if "cookies" not in message.content and "get" not in message.content:
            raise ValueError("No cookies or get sent to consumer; this decorator can only be used on messages containing at least one.")
        # Make sure there's a session key
        session_key = None
        if "get" in message.content:
            try:
                session_key = message.content['get'].get("session_key", [])[0]
            except IndexError:
                pass
        if "cookies" in message.content and session_key is None:
            session_key = message.content['cookies'].get(settings.SESSION_COOKIE_NAME)
        # Make a session storage
        if session_key:
            session_engine = import_module(settings.SESSION_ENGINE)
            session = session_engine.SessionStore(session_key=session_key)
        else:
            session = None
        message.session = session
        # Run the consumer
        result = func(message, *args, **kwargs)
        # Persist session if needed (won't be saved if error happens)
        if session is not None and session.modified:
            session.save()
        return result
    return inner


def http_django_auth(func):
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
        if not hasattr(message, "session"):
            raise ValueError("Did not see a session to get auth from")
        if message.session is None:
            message.user = None
        # Otherwise, be a bit naughty and make a fake Request with just
        # a "session" attribute (later on, perhaps refactor contrib.auth to
        # pass around session rather than request)
        else:
            fake_request = type("FakeRequest", (object, ), {"session": message.session})
            message.user = auth.get_user(fake_request)
        # Run the consumer
        return func(message, *args, **kwargs)
    return inner


def channel_session(func):
    """
    Provides a session-like object called "channel_session" to consumers
    as a message attribute that will auto-persist across consumers with
    the same incoming "reply_channel" value.
    """
    @functools.wraps(func)
    def inner(message, *args, **kwargs):
        # Make sure there's a reply_channel in kwargs
        if not message.reply_channel:
            raise ValueError("No reply_channel sent to consumer; this decorator can only be used on messages containing it.")
        # Turn the reply_channel into a valid session key length thing.
        # We take the last 24 bytes verbatim, as these are the random section,
        # and then hash the remaining ones onto the start, and add a prefix
        # TODO: See if there's a better way of doing this
        reply_name = message.reply_channel.name
        session_key = "skt" + hashlib.md5(reply_name[:-24]).hexdigest()[:8] + reply_name[-24:]
        # Make a session storage
        session_engine = import_module(settings.SESSION_ENGINE)
        session = session_engine.SessionStore(session_key=session_key)
        # If the session does not already exist, save to force our session key to be valid
        if not session.exists(session.session_key):
            session.save()
        message.channel_session = session
        # Run the consumer
        result = func(message, *args, **kwargs)
        # Persist session if needed (won't be saved if error happens)
        if session.modified:
            session.save()
        return result
    return inner
