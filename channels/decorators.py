import functools
import hashlib
from importlib import import_module

from django.conf import settings


def linearize(func):
    """
    Makes sure the contained consumer does not run at the same time other
    consumers are running on messages with the same reply_channel.

    Required if you don't want weird things like a second consumer starting
    up before the first has exited and saved its session. Doesn't guarantee
    ordering, just linearity.
    """
    @functools.wraps(func)
    def inner(message, *args, **kwargs):
        # Make sure there's a reply channel
        if not message.reply_channel:
            raise ValueError("No reply_channel sent to consumer; @no_overlap can only be used on messages containing it.")
        # Get the lock, or re-queue
        locked = message.channel_backend.lock_channel(message.reply_channel)
        if not locked:
            raise message.Requeue()
        # OK, keep going
        try:
            return func(message, *args, **kwargs)
        finally:
            message.channel_backend.unlock_channel(message.reply_channel)
    return inner


def channel_session(func):
    """
    Provides a session-like object called "channel_session" to consumers
    as a message attribute that will auto-persist across consumers with
    the same incoming "reply_channel" value.

    Use this to persist data across the lifetime of a connection.
    """
    @functools.wraps(func)
    def inner(message, *args, **kwargs):
        # Make sure there's a reply_channel
        if not message.reply_channel:
            raise ValueError("No reply_channel sent to consumer; @channel_session can only be used on messages containing it.")
        # Make sure there's NOT a channel_session already
        if hasattr(message, "channel_session"):
            raise ValueError("channel_session decorator wrapped inside another channel_session decorator")
        # Turn the reply_channel into a valid session key length thing.
        # We take the last 24 bytes verbatim, as these are the random section,
        # and then hash the remaining ones onto the start, and add a prefix
        reply_name = message.reply_channel.name
        session_key = "skt" + hashlib.md5(reply_name[:-24]).hexdigest()[:8] + reply_name[-24:]
        # Make a session storage
        session_engine = import_module(settings.SESSION_ENGINE)
        session = session_engine.SessionStore(session_key=session_key)
        # If the session does not already exist, save to force our
        # session key to be valid.
        if not session.exists(session.session_key):
            session.save(must_create=True)
        message.channel_session = session
        # Run the consumer
        try:
            return func(message, *args, **kwargs)
        finally:
            # Persist session if needed
            if session.modified:
                session.save()
    return inner


def http_session(func):
    """
    Wraps a HTTP or WebSocket connect consumer (or any consumer of messages
    that provides a "cooikies" or "get" attribute) to provide a "http_session"
    attribute that behaves like request.session; that is, it's hung off of
    a per-user session key that is saved in a cookie or passed as the
    "session_key" GET parameter.

    It won't automatically create and set a session cookie for users who
    don't have one - that's what SessionMiddleware is for, this is a simpler
    read-only version for more low-level code.

    If a message does not have a session we can inflate, the "session" attribute
    will be None, rather than an empty session you can write to.
    """
    @functools.wraps(func)
    def inner(message, *args, **kwargs):
        if "cookies" not in message.content and "get" not in message.content:
            raise ValueError("No cookies or get sent to consumer - cannot initialise http_session")
        # Make sure there's NOT a http_session already
        if hasattr(message, "http_session"):
            raise ValueError("http_session decorator wrapped inside another http_session decorator")
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
        message.http_session = session
        # Run the consumer
        result = func(message, *args, **kwargs)
        # Persist session if needed (won't be saved if error happens)
        if session is not None and session.modified:
            session.save()
        return result
    return inner
