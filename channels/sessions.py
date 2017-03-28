import functools
import hashlib
from importlib import import_module

from django.conf import settings
from django.contrib.sessions.backends import signed_cookies
from django.contrib.sessions.backends.base import CreateError

from .exceptions import ConsumeLater
from .handler import AsgiRequest
from .message import Message


def session_for_reply_channel(reply_channel):
    """
    Returns a session object tied to the reply_channel unicode string
    passed in as an argument.
    """
    # We hash the whole reply channel name and add a prefix, to fit inside 32B
    reply_name = reply_channel
    hashed = hashlib.sha1(reply_name.encode("utf8")).hexdigest()
    session_key = "chn" + hashed[:29]
    # Make a session storage
    session_engine = import_module(getattr(settings, "CHANNEL_SESSION_ENGINE", settings.SESSION_ENGINE))
    if session_engine is signed_cookies:
        raise ValueError("You cannot use channels session functionality with signed cookie sessions!")
    # Force the instance to load in case it resets the session when it does
    instance = session_engine.SessionStore(session_key=session_key)
    instance._session.keys()
    instance._session_key = session_key
    return instance


def channel_session(func):
    """
    Provides a session-like object called "channel_session" to consumers
    as a message attribute that will auto-persist across consumers with
    the same incoming "reply_channel" value.

    Use this to persist data across the lifetime of a connection.
    """
    @functools.wraps(func)
    def inner(*args, **kwargs):
        message = None
        for arg in args[:2]:
            if isinstance(arg, Message):
                message = arg
                break
        if message is None:
            raise ValueError('channel_session called without Message instance')
        # Make sure there's NOT a channel_session already
        if hasattr(message, "channel_session"):
            try:
                return func(*args, **kwargs)
            finally:
                # Persist session if needed
                if message.channel_session.modified:
                    message.channel_session.save()

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
            return func(*args, **kwargs)
        finally:
            # Persist session if needed
            if session.modified and not session.is_empty():
                session.save()
    return inner


def requeue_messages(message):
    """
    Requeue any pending wait channel messages for this socket connection back onto it's original channel
    """
    while True:
        wait_channel = "__wait__.%s" % message.reply_channel.name
        channel, content = message.channel_layer.receive_many([wait_channel], block=False)
        if channel:
            original_channel = content.pop("original_channel")
            try:
                message.channel_layer.send(original_channel, content)
            except message.channel_layer.ChannelFull:
                raise message.channel_layer.ChannelFull(
                    "Cannot requeue pending __wait__ channel message " +
                    "back on to already full channel %s" % original_channel
                )
        else:
            break


def enforce_ordering(func=None, slight=False):
    """
    Enforces strict (all messages exactly ordered) ordering against a reply_channel.

    Uses sessions to track ordering and socket-specific wait channels for unordered messages.
    """
    # Slight is deprecated
    if slight:
        raise ValueError("Slight ordering is now always on due to Channels changes. Please remove the decorator.")

    # Main decorator
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
            if order == next_order:
                # Run consumer
                func(message, *args, **kwargs)
                # Mark next message order as available for running
                message.channel_session["__channels_next_order"] = order + 1
                message.channel_session.save()
                message.channel_session.modified = False
                requeue_messages(message)
            else:
                # Since out of order, enqueue message temporarily to wait channel for this socket connection
                wait_channel = "__wait__.%s" % message.reply_channel.name
                message.content["original_channel"] = message.channel.name
                try:
                    message.channel_layer.send(wait_channel, message.content)
                except message.channel_layer.ChannelFull:
                    raise message.channel_layer.ChannelFull(
                        "Cannot add unordered message to already " +
                        "full __wait__ channel for socket %s" % message.reply_channel.name
                    )
                # Next order may have changed while this message was being processed
                # Requeue messages if this has happened
                if order == message.channel_session.load().get("__channels_next_order", 0):
                    requeue_messages(message)

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
            try:
                return func(message, *args, **kwargs)
            finally:
                # Persist session if needed (won't be saved if error happens)
                if message.http_session is not None and message.http_session.modified:
                    message.http_session.save()

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


def channel_and_http_session(func):
    """
    Enables both the channel_session and http_session.

    Stores the http session key in the channel_session on websocket.connect messages.
    It will then hydrate the http_session from that same key on subsequent messages.
    """
    @http_session
    @channel_session
    @functools.wraps(func)
    def inner(message, *args, **kwargs):
        # Store the session key in channel_session
        if message.http_session is not None and settings.SESSION_COOKIE_NAME not in message.channel_session:
            message.channel_session[settings.SESSION_COOKIE_NAME] = message.http_session.session_key
        # Hydrate the http_session from session_key
        elif message.http_session is None and settings.SESSION_COOKIE_NAME in message.channel_session:
            session_engine = import_module(settings.SESSION_ENGINE)
            session = session_engine.SessionStore(session_key=message.channel_session[settings.SESSION_COOKIE_NAME])
            message.http_session = session
        # Run the consumer
        return func(message, *args, **kwargs)
    return inner
