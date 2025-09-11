import warnings
from functools import partial
from urllib.parse import urlsplit

from asgiref.sync import iscoroutinefunction, markcoroutinefunction, sync_to_async

from django.conf import settings
from django.contrib import auth
from django.contrib.auth import REDIRECT_FIELD_NAME, load_backend
from django.contrib.auth.backends import RemoteUserBackend
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import resolve_url
from django.utils.deprecation import MiddlewareMixin, RemovedInDjango61Warning
from django.utils.functional import SimpleLazyObject


def get_user(request):
    if not hasattr(request, "_cached_user"):
        request._cached_user = auth.get_user(request)
    return request._cached_user


async def auser(request):
    if not hasattr(request, "_acached_user"):
        request._acached_user = await auth.aget_user(request)
    return request._acached_user


class AuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not hasattr(request, "session"):
            raise ImproperlyConfigured(
                "The Django authentication middleware requires session "
                "middleware to be installed. Edit your MIDDLEWARE setting to "
                "insert "
                "'django.contrib.sessions.middleware.SessionMiddleware' before "
                "'django.contrib.auth.middleware.AuthenticationMiddleware'."
            )
        request.user = SimpleLazyObject(lambda: get_user(request))
        request.auser = partial(auser, request)


class LoginRequiredMiddleware(MiddlewareMixin):
    """
    Middleware that redirects all unauthenticated requests to a login page.

    Views using the login_not_required decorator will not be redirected.
    """

    redirect_field_name = REDIRECT_FIELD_NAME

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not getattr(view_func, "login_required", True):
            return None

        if request.user.is_authenticated:
            return None

        return self.handle_no_permission(request, view_func)

    def get_login_url(self, view_func):
        login_url = getattr(view_func, "login_url", None) or settings.LOGIN_URL
        if not login_url:
            raise ImproperlyConfigured(
                "No login URL to redirect to. Define settings.LOGIN_URL or "
                "provide a login_url via the 'django.contrib.auth.decorators."
                "login_required' decorator."
            )
        return str(login_url)

    def get_redirect_field_name(self, view_func):
        return getattr(view_func, "redirect_field_name", self.redirect_field_name)

    def handle_no_permission(self, request, view_func):
        path = request.build_absolute_uri()
        resolved_login_url = resolve_url(self.get_login_url(view_func))
        # If the login url is the same scheme and net location then use the
        # path as the "next" url.
        login_scheme, login_netloc = urlsplit(resolved_login_url)[:2]
        current_scheme, current_netloc = urlsplit(path)[:2]
        if (not login_scheme or login_scheme == current_scheme) and (
            not login_netloc or login_netloc == current_netloc
        ):
            path = request.get_full_path()

        return redirect_to_login(
            path,
            resolved_login_url,
            self.get_redirect_field_name(view_func),
        )


class RemoteUserMiddleware:
    """
    Middleware for utilizing web-server-provided authentication.

    If request.user is not authenticated, then this middleware attempts to
    authenticate the username from the ``REMOTE_USER`` key in ``request.META``,
    an environment variable commonly set by the webserver.

    If authentication is successful, the user is automatically logged in to
    persist the user in the session.

    The ``request.META`` key is configurable and defaults to ``REMOTE_USER``.
    Subclass this class and change the ``header`` attribute if you need to
    use a different key from ``request.META``, for example a HTTP request
    header.
    """

    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        if get_response is None:
            raise ValueError("get_response must be provided.")
        self.get_response = get_response
        self.is_async = iscoroutinefunction(get_response)
        if self.is_async:
            markcoroutinefunction(self)
        super().__init__()

    # Name of request.META key to grab username from. Note that for
    # request headers, normalization to all uppercase and the addition
    # of a "HTTP_" prefix apply.
    header = "REMOTE_USER"
    force_logout_if_no_header = True

    def __call__(self, request):
        if self.is_async:
            return self.__acall__(request)
        self.process_request(request)
        return self.get_response(request)

    def process_request(self, request):
        # AuthenticationMiddleware is required so that request.user exists.
        if not hasattr(request, "user"):
            raise ImproperlyConfigured(
                "The Django remote user auth middleware requires the"
                " authentication middleware to be installed. Edit your"
                " MIDDLEWARE setting to insert"
                " 'django.contrib.auth.middleware.AuthenticationMiddleware'"
                " before the RemoteUserMiddleware class."
            )
        try:
            username = request.META[self.header]
        except KeyError:
            # If specified header doesn't exist then remove any existing
            # authenticated remote-user, or return (leaving request.user set to
            # AnonymousUser by the AuthenticationMiddleware).
            if self.force_logout_if_no_header and request.user.is_authenticated:
                self._remove_invalid_user(request)
            return
        # If the user is already authenticated and that user is the user we are
        # getting passed in the headers, then the correct user is already
        # persisted in the session and we don't need to continue.
        if request.user.is_authenticated:
            if request.user.get_username() == self.clean_username(username, request):
                return
            else:
                # An authenticated user is associated with the request, but
                # it does not match the authorized user in the header.
                self._remove_invalid_user(request)

        # We are seeing this user for the first time in this session, attempt
        # to authenticate the user.
        user = auth.authenticate(request, remote_user=username)
        if user:
            # User is valid. Set request.user and persist user in the session
            # by logging the user in.
            request.user = user
            auth.login(request, user)

    async def __acall__(self, request):
        # RemovedInDjango61Warning.
        if (
            self.__class__.process_request is not RemoteUserMiddleware.process_request
            and self.__class__.aprocess_request is RemoteUserMiddleware.aprocess_request
        ):
            warnings.warn(
                "Support for subclasses of RemoteUserMiddleware that override "
                "process_request() without overriding aprocess_request() is "
                "deprecated.",
                category=RemovedInDjango61Warning,
                stacklevel=2,
            )
            await sync_to_async(self.process_request, thread_sensitive=True)(request)
            return await self.get_response(request)
        await self.aprocess_request(request)
        return await self.get_response(request)

    async def aprocess_request(self, request):
        # AuthenticationMiddleware is required so that request.user exists.
        if not hasattr(request, "user"):
            raise ImproperlyConfigured(
                "The Django remote user auth middleware requires the"
                " authentication middleware to be installed. Edit your"
                " MIDDLEWARE setting to insert"
                " 'django.contrib.auth.middleware.AuthenticationMiddleware'"
                " before the RemoteUserMiddleware class."
            )
        try:
            username = request.META["HTTP_" + self.header]
        except KeyError:
            # If specified header doesn't exist then remove any existing
            # authenticated remote-user, or return (leaving request.user set to
            # AnonymousUser by the AuthenticationMiddleware).
            if self.force_logout_if_no_header:
                user = await request.auser()
                if user.is_authenticated:
                    await self._aremove_invalid_user(request)
            return
        user = await request.auser()
        # If the user is already authenticated and that user is the user we are
        # getting passed in the headers, then the correct user is already
        # persisted in the session and we don't need to continue.
        if user.is_authenticated:
            if user.get_username() == self.clean_username(username, request):
                return
            else:
                # An authenticated user is associated with the request, but
                # it does not match the authorized user in the header.
                await self._aremove_invalid_user(request)

        # We are seeing this user for the first time in this session, attempt
        # to authenticate the user.
        user = await auth.aauthenticate(request, remote_user=username)
        if user:
            # User is valid. Set request.user and persist user in the session
            # by logging the user in.
            request.user = user
            await auth.alogin(request, user)

    def clean_username(self, username, request):
        """
        Allow the backend to clean the username, if the backend defines a
        clean_username method.
        """
        backend_str = request.session[auth.BACKEND_SESSION_KEY]
        backend = auth.load_backend(backend_str)
        try:
            username = backend.clean_username(username)
        except AttributeError:  # Backend has no clean_username method.
            pass
        return username

    def _remove_invalid_user(self, request):
        """
        Remove the current authenticated user in the request which is invalid
        but only if the user is authenticated via the RemoteUserBackend.
        """
        try:
            stored_backend = load_backend(
                request.session.get(auth.BACKEND_SESSION_KEY, "")
            )
        except ImportError:
            # backend failed to load
            auth.logout(request)
        else:
            if isinstance(stored_backend, RemoteUserBackend):
                auth.logout(request)

    async def _aremove_invalid_user(self, request):
        """
        Remove the current authenticated user in the request which is invalid
        but only if the user is authenticated via the RemoteUserBackend.
        """
        try:
            stored_backend = load_backend(
                await request.session.aget(auth.BACKEND_SESSION_KEY, "")
            )
        except ImportError:
            # Backend failed to load.
            await auth.alogout(request)
        else:
            if isinstance(stored_backend, RemoteUserBackend):
                await auth.alogout(request)


class PersistentRemoteUserMiddleware(RemoteUserMiddleware):
    """
    Middleware for web-server provided authentication on logon pages.

    Like RemoteUserMiddleware but keeps the user authenticated even if
    the ``request.META`` key is not found in the request. Useful for
    setups when the external authentication is only expected to happen
    on some "logon" URL and the rest of the application wants to use
    Django's authentication mechanism.
    """

    force_logout_if_no_header = False
