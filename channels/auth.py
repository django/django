from django.contrib import auth
from django.utils.functional import SimpleLazyObject

from channels.sessions import CookieMiddleware, SessionMiddleware


def get_user(scope):
    if "_cached_user" not in scope:
        # We need to fake a request so the auth code works until we get to
        # refactor it to take sessions, not requests.
        fake_request = type("FakeRequest", (object, ), {"session": scope["session"]})
        scope["_cached_user"] = auth.get_user(fake_request)
    return scope["_cached_user"]


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
        if "user" not in scope:
            scope["user"] = SimpleLazyObject(lambda: get_user(scope))
        # Pass control to inner application
        return self.inner(scope)


# Handy shortcut for applying all three layers at once
AuthMiddlewareStack = lambda inner: CookieMiddleware(SessionMiddleware(AuthMiddleware(inner)))
