import functools
import hashlib
import warnings
from importlib import import_module

from django.conf import settings
from django.contrib.sessions.backends import signed_cookies
from django.contrib.sessions.backends.base import CreateError

from .exceptions import ConsumeLater
from .handler import AsgiRequest


def session_for_reply_channel(reply_channel):
    """
    Returns a session object tied to the reply_channel unicode string
    passed in as an argument.
    """
    # We hash the whole reply channel name and add a prefix, to fit inside 32B
    reply_name = reply_channel
    hashed = hashlib.md5(reply_name.encode("utf8")).hexdigest()
    session_key = "chn" + hashed[:29]
    # Make a session storage
    session_engine = import_module(getattr(settings, "CHANNEL_SESSION_ENGINE", settings.SESSION_ENGINE))
    if session_engine is signed_cookies:
        raise ValueError("You cannot use channels session functionality with signed cookie sessions!")
    return session_engine.SessionStore(session_key=session_key)


def channel_session(func):
    """
    Provides a session-like object called "channel_session" to consumers
    as a message attribute that will auto-persist across consumers with
    the same incoming "reply_channel" value.

    Use this to persist data across the lifetime of a connection.
    """
    @functools.wraps(func)
    def inner(message, *args, **kwargs):
        # Make sure there's NOT a channel_session already
        if hasattr(message, "channel_session"):
            return func(message, *args, **kwargs)
        # Make sure there's a reply_channel
        if not message.reply_channel:
            raise ValueError(
                "No reply_channel sent to consumer; @channel_session " +
                "can only be used on messages containing it."
            )
        # If the session does not already exist, save to force our
        # session key to be valid.
        session = session_for_reply_channel(message.reply_channel.name)
        if not session.exists(session.session_key):
            try:
                session.save(must_create=True)
            except CreateError:
                # Session wasn't unique, so another consumer is doing the same thing
                raise ConsumeLater()
        message.channel_session = session
        # Run the consumer
        try:
            return func(message, *args, **kwargs)
        finally:
            # Persist session if needed
            if session.modified:
                session.save()
    return inner


def enforce_ordering(func=None, slight=False):
    """
    Enforces either slight (order=0 comes first, everything else isn't ordered)
    or strict (all messages exactly ordered) ordering against a reply_channel.

    Uses sessions to track ordering.

    You cannot mix slight ordering and strict ordering on a channel; slight
    ordering does not write to the session after the first message to improve
    performance.
    """
    def decorator(func):
        @channel_session
        @functools.wraps(func)
        def inner(message, *args, **kwargs):
            # Make sure there's an order
            if "order" not in message.content:
                raise ValueError(
                    "No `order` value in message; @enforce_ordering " +
                    "can only be used on messages containing it."
                )
            order = int(message.content['order'])
            # See what the current next order should be
            next_order = message.channel_session.get("__channels_next_order", 0)
            if order == next_order or (slight and next_order > 0):
                # Message is in right order. Maybe persist next one?
                if order == 0 or not slight:
                    message.channel_session["__channels_next_order"] = order + 1
                # Run consumer
                return func(message, *args, **kwargs)
            else:
                # Bad ordering - warn if we're getting close to the limit
                if getattr(message, "__doomed__", False):
                    warnings.warn(
                        "Enforce ordering consumer reached retry limit, message " +
                        "being dropped. Did you decorate all protocol consumers correctly?"
                    )
                raise ConsumeLater()
        return inner
    if func is not None:
        return decorator(func)
    else:
        return decorator


def http_session(func):
    """
    Wraps a HTTP or WebSocket connect consumer (or any consumer of messages
    that provides a "cookies" or "get" attribute) to provide a "http_session"
    attribute that behaves like request.session; that is, it's hung off of
    a per-user session key that is saved in a cookie or passed as the
    "session_key" GET parameter.

    It won't automatically create and set a session cookie for users who
    don't have one - that's what SessionMiddleware is for, this is a simpler
    read-only version for more low-level code.

    If a message does not have a session we can inflate, the "session" attribute
    will be None, rather than an empty session you can write to.

    Does not allow a new session to be set; that must be done via a view. This
    is only an accessor for any existing session.
    """
    @functools.wraps(func)
    def inner(message, *args, **kwargs):
        # Make sure there's NOT a http_session already
        if hasattr(message, "http_session"):
            return func(message, *args, **kwargs)
        try:
            # We want to parse the WebSocket (or similar HTTP-lite) message
            # to get cookies and GET, but we need to add in a few things that
            # might not have been there.
            if "method" not in message.content:
                message.content['method'] = "FAKE"
            request = AsgiRequest(message)
        except Exception as e:
            raise ValueError("Cannot parse HTTP message - are you sure this is a HTTP consumer? %s" % e)
        # Make sure there's a session key
        session_key = request.GET.get("session_key", None)
        if session_key is None:
            session_key = request.COOKIES.get(settings.SESSION_COOKIE_NAME, None)
        # Make a session storage
        if session_key:
            session_engine = import_module(settings.SESSION_ENGINE)
            session = session_engine.SessionStore(session_key=session_key)
        else:
            session = None
        message.http_session = session
        # Run the consumer
        result = func(message, *args, **kwargs)
        # Persist session if needed (won't be saved if error happens)
        if session is not None and session.modified:
            session.save()
        return result
    return inner
