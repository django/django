import datetime
import time
from django.utils import timezone
from importlib import import_module

from django.conf import settings
from django.contrib.sessions.backends.base import UpdateError
from django.core.exceptions import SuspiciousOperation
from django.http import parse_cookie
from django.http.cookie import SimpleCookie
from django.utils.encoding import force_str
from django.utils.http import cookie_date


class CookieMiddleware:
    """
    Extracts cookies from HTTP or WebSocket-style scopes and adds them as a
    scope["cookies"] entry with the same format as Django's request.COOKIES.
    """

    def __init__(self, inner):
        self.inner = inner

    def __call__(self, scope):
        # Check this actually has headers. They're a required scope key for HTTP and WS.
        if "headers" not in scope:
            raise ValueError(
                "CookieMiddleware was passed a scope that did not have a headers key " +
                "(make sure it is only passed HTTP or WebSocket connections)"
            )
        # Go through headers to find the cookie one
        for name, value in scope.get("headers", []):
            if name == b"cookie":
                scope["cookies"] = parse_cookie(value.decode("ascii"))
                break
        else:
            # No cookie header found - add an empty default.
            scope["cookies"] = {}
        # Return inner application
        return self.inner(scope)

    @classmethod
    def set_cookie(
            cls,
            message,
            key,
            value='',
            max_age=None,
            expires=None,
            path='/',
            domain=None,
            secure=False,
            httponly=False
        ):
        """
        Sets a cookie in the passed HTTP response message.

        ``expires`` can be:
        - a string in the correct format,
        - a naive ``datetime.datetime`` object in UTC,
        - an aware ``datetime.datetime`` object in any time zone.
        If it is a ``datetime.datetime`` object then ``max_age`` will be calculated.
        """
        value = force_str(value)
        cookies = SimpleCookie()
        cookies[key] = value
        if expires is not None:
            if isinstance(expires, datetime.datetime):
                if timezone.is_aware(expires):
                    expires = timezone.make_naive(expires, timezone.utc)
                delta = expires - expires.utcnow()
                # Add one second so the date matches exactly (a fraction of
                # time gets lost between converting to a timedelta and
                # then the date string).
                delta = delta + datetime.timedelta(seconds=1)
                # Just set max_age - the max_age logic will set expires.
                expires = None
                max_age = max(0, delta.days * 86400 + delta.seconds)
            else:
                cookies[key]['expires'] = expires
        else:
            cookies[key]['expires'] = ''
        if max_age is not None:
            cookies[key]['max-age'] = max_age
            # IE requires expires, so set it if hasn't been already.
            if not expires:
                cookies[key]['expires'] = cookie_date(time.time() +
                                                           max_age)
        if path is not None:
            cookies[key]['path'] = path
        if domain is not None:
            cookies[key]['domain'] = domain
        if secure:
            cookies[key]['secure'] = True
        if httponly:
            cookies[key]['httponly'] = True
        # Write out the cookies to the response
        for c in cookies.values():
            message.setdefault("headers", []).append(
                (b'Set-Cookie', bytes(c.output(header=''))),
            )

    @classmethod
    def delete_cookie(cls, message, key, path='/', domain=None):
        """
        Deletes a cookie in a response.
        """
        return cls.set_cookie(
            message,
            key,
            max_age=0,
            path=path,
            domain=domain,
            expires='Thu, 01-Jan-1970 00:00:00 GMT',
        )


class SessionMiddleware:
    """
    Class that adds Django sessions (from HTTP cookies) to the
    scope. Works with HTTP or WebSocket protocol types (or anything that
    provides a "headers" entry in the scope).

    Requires the CookieMiddleware to be higher up in the stack.
    """

    # Message types that trigger a session save if it's modified
    save_message_types = ["http.response.start"]

    # Message types that can carry session cookies back
    cookie_response_message_types = ["http.response.start"]

    def __init__(self, inner):
        self.inner = inner
        self.cookie_name = settings.SESSION_COOKIE_NAME
        self.session_store = import_module(settings.SESSION_ENGINE).SessionStore

    def __call__(self, scope):
        return SessionMiddlewareInstance(scope, self)


class SessionMiddlewareInstance:
    """
    Inner class that is instantiated once per scope.
    """

    def __init__(self, scope, middleware):
        self.middleware = middleware
        self.scope = scope
        # Make sure there are cookies in the scope
        if "cookies" not in self.scope:
            raise ValueError("No cookies in scope - SessionMiddleware needs to run inside of CookieMiddleware.")
        # Parse the headers in the scope into cookies
        session_key = self.scope["cookies"].get(self.middleware.cookie_name)
        self.scope["session"] = self.middleware.session_store(session_key)
        # Instantiate our inner application
        self.inner = self.middleware.inner(scope)

    def __call__(self, receive, send):
        """
        We intercept the send() callable so we can do session saves and
        add session cookie overrides to send back.
        """
        self.real_send = send
        return self.inner(receive, self.send)

    async def send(self, message):
        """
        Overridden send that also does session saves/cookies.
        """
        modified = self.scope["session"].modified
        empty = self.scope["session"].is_empty()
        # If this is a message type that we want to save on, and there's
        # changed data, save it. We also save if it's empty as we might
        # not be able to send a cookie-delete along with this message.
        if message["type"] in self.middleware.save_message_types and \
           message.get("status", 200) != 500 and \
           (modified or settings.SESSION_SAVE_EVERY_REQUEST):
            self.save_session()
            # If this is a message type that can transport cookies back to the
            # client, then do so.
            if message["type"] in self.middleware.cookie_response_message_types:
                if empty:
                    # Delete cookie if it's set
                    if settings.SESSION_COOKIE_NAME in self.scope["cookies"]:
                        CookieMiddleware.delete_cookie(
                            message,
                            settings.SESSION_COOKIE_NAME,
                            path=settings.SESSION_COOKIE_PATH,
                            domain=settings.SESSION_COOKIE_DOMAIN,
                        )
                else:
                    # Get the expiry data
                    if self.scope["session"].get_expire_at_browser_close():
                        max_age = None
                        expires = None
                    else:
                        max_age = self.scope["session"].get_expiry_age()
                        expires_time = time.time() + max_age
                        expires = cookie_date(expires_time)
                    # Set the cookie
                    CookieMiddleware.set_cookie(
                        message,
                        self.middleware.cookie_name,
                        self.scope["session"].session_key,
                        max_age=max_age,
                        expires=expires,
                        domain=settings.SESSION_COOKIE_DOMAIN,
                        path=settings.SESSION_COOKIE_PATH,
                        secure=settings.SESSION_COOKIE_SECURE or None,
                        httponly=settings.SESSION_COOKIE_HTTPONLY or None,
                    )
        # Pass up the send
        return await self.real_send(message)

    def save_session(self):
        """
        Saves the current session.
        """
        try:
            self.scope["session"].save()
        except UpdateError:
            raise SuspiciousOperation(
                "The request's session was deleted before the "
                "request completed. The user may have logged "
                "out in a concurrent request, for example."
            )
