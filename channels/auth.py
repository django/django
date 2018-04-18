from django.conf import settings
from django.contrib.auth import (
    BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY, _get_backends, get_user_model, load_backend, user_logged_in,
    user_logged_out,
)
from django.contrib.auth.models import AnonymousUser
from django.utils.crypto import constant_time_compare
from django.utils.translation import LANGUAGE_SESSION_KEY

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.sessions import CookieMiddleware, SessionMiddleware


@database_sync_to_async
def get_user(scope):
    """
    Return the user model instance associated with the given scope.
    If no user is retrieved, return an instance of `AnonymousUser`.
    """
    if "session" not in scope:
        raise ValueError("Cannot find session in scope. You should wrap your consumer in SessionMiddleware.")
    session = scope["session"]
    user = None
    try:
        user_id = _get_user_session_key(session)
        backend_path = session[BACKEND_SESSION_KEY]
    except KeyError:
        pass
    else:
        if backend_path in settings.AUTHENTICATION_BACKENDS:
            backend = load_backend(backend_path)
            user = backend.get_user(user_id)
            # Verify the session
            if hasattr(user, "get_session_auth_hash"):
                session_hash = session.get(HASH_SESSION_KEY)
                session_hash_verified = session_hash and constant_time_compare(
                    session_hash,
                    user.get_session_auth_hash()
                )
                if not session_hash_verified:
                    session.flush()
                    user = None
    return user or AnonymousUser()


@database_sync_to_async
def login(scope, user, backend=None):
    """
    Persist a user id and a backend in the request.
    This way a user doesn't have to re-authenticate on every request.
    Note that data set during the anonymous session is retained when the user logs in.
    """
    if "session" not in scope:
        raise ValueError("Cannot find session in scope. You should wrap your consumer in SessionMiddleware.")
    session = scope["session"]
    session_auth_hash = ""
    if user is None:
        user = scope.get("user", None)
    if user is None:
        raise ValueError("User must be passed as an argument or must be present in the scope.")
    if hasattr(user, "get_session_auth_hash"):
        session_auth_hash = user.get_session_auth_hash()
    if SESSION_KEY in session:
        if _get_user_session_key(session) != user.pk or (
                session_auth_hash and not
                constant_time_compare(session.get(HASH_SESSION_KEY, ""), session_auth_hash)):
            # To avoid reusing another user's session, create a new, empty
            # session if the existing session corresponds to a different
            # authenticated user.
            session.flush()
    else:
        session.cycle_key()
    try:
        backend = backend or user.backend
    except AttributeError:
        backends = _get_backends(return_tuples=True)
        if len(backends) == 1:
            _, backend = backends[0]
        else:
            raise ValueError(
                "You have multiple authentication backends configured and therefore must provide the `backend` "
                "argument or set the `backend` attribute on the user."
            )
    session[SESSION_KEY] = user._meta.pk.value_to_string(user)
    session[BACKEND_SESSION_KEY] = backend
    session[HASH_SESSION_KEY] = session_auth_hash
    scope["user"] = user
    # note this does not reset the CSRF_COOKIE/Token
    user_logged_in.send(sender=user.__class__, request=None, user=user)


@database_sync_to_async
def logout(scope):
    """
    Remove the authenticated user's ID from the request and flush their session data.
    """
    if "session" not in scope:
        raise ValueError(
            "Login cannot find session in scope. You should wrap your consumer in SessionMiddleware."
        )
    session = scope["session"]
    # Dispatch the signal before the user is logged out so the receivers have a
    # chance to find out *who* logged out.
    user = scope.get("user", None)
    if hasattr(user, "is_authenticated") and not user.is_authenticated:
        user = None
    if user is not None:
        user_logged_out.send(sender=user.__class__, request=None, user=user)
    # remember language choice saved to session
    language = session.get(LANGUAGE_SESSION_KEY)
    session.flush()
    if language is not None:
        session[LANGUAGE_SESSION_KEY] = language
    if "user" in scope:
        scope["user"] = AnonymousUser()


def _get_user_session_key(session):
    # This value in the session is always serialized to a string, so we need
    # to convert it back to Python whenever we access it.
    return get_user_model()._meta.pk.to_python(session[SESSION_KEY])


class AuthMiddleware:
    """
    Middleware which populates scope["user"] from a Django session.
    Requires SessionMiddleware to function.
    """

    def __init__(self, inner):
        self.inner = inner

    def __call__(self, scope):
        # Make sure we have a session
        if "session" not in scope:
            raise ValueError("AuthMiddleware cannot find session in scope. SessionMiddleware must be above it.")
        # Add it to the scope if it's not there already
        scope = dict(scope)
        if "user" not in scope:
            # We can't make this a LazyObject because there's no way to await attribute access,
            # and this is an async function under the hood.
            scope["user"] = async_to_sync(get_user)(scope)
        # Pass control to inner application
        return self.inner(scope)


# Handy shortcut for applying all three layers at once
AuthMiddlewareStack = lambda inner: CookieMiddleware(SessionMiddleware(AuthMiddleware(inner)))
