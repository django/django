from functools import wraps
from urllib.parse import urlsplit

from asgiref.sync import async_to_sync, iscoroutinefunction, sync_to_async

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.exceptions import PermissionDenied
from django.shortcuts import resolve_url


def user_passes_test(
    test_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME
):
    """
    Decorator for views that checks that the user passes the given test,
    redirecting to the log-in page if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.
    """

    def decorator(view_func):
        def _redirect_to_login(request):
            path = request.build_absolute_uri()
            resolved_login_url = resolve_url(login_url or settings.LOGIN_URL)
            # If the login url is the same scheme and net location then just
            # use the path as the "next" url.
            login_scheme, login_netloc = urlsplit(resolved_login_url)[:2]
            current_scheme, current_netloc = urlsplit(path)[:2]
            if (not login_scheme or login_scheme == current_scheme) and (
                not login_netloc or login_netloc == current_netloc
            ):
                path = request.get_full_path()
            from django.contrib.auth.views import redirect_to_login

            return redirect_to_login(path, resolved_login_url, redirect_field_name)

        if iscoroutinefunction(view_func):

            async def _view_wrapper(request, *args, **kwargs):
                auser = await request.auser()
                if iscoroutinefunction(test_func):
                    test_pass = await test_func(auser)
                else:
                    test_pass = await sync_to_async(test_func)(auser)

                if test_pass:
                    return await view_func(request, *args, **kwargs)
                return _redirect_to_login(request)

        else:

            def _view_wrapper(request, *args, **kwargs):
                if iscoroutinefunction(test_func):
                    test_pass = async_to_sync(test_func)(request.user)
                else:
                    test_pass = test_func(request.user)

                if test_pass:
                    return view_func(request, *args, **kwargs)
                return _redirect_to_login(request)

        # Attributes used by LoginRequiredMiddleware.
        _view_wrapper.login_url = login_url
        _view_wrapper.redirect_field_name = redirect_field_name

        return wraps(view_func)(_view_wrapper)

    return decorator


def login_required(
    function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None
):
    """
    Decorator for views that checks that the user is logged in, redirecting
    to the log-in page if necessary.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated,
        login_url=login_url,
        redirect_field_name=redirect_field_name,
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


def login_not_required(view_func):
    """
    Decorator for views that allows access to unauthenticated requests.
    """
    view_func.login_required = False
    return view_func


def permission_required(perm, login_url=None, raise_exception=False):
    """
    Decorator for views that checks whether a user has a particular permission
    enabled, redirecting to the log-in page if necessary.
    If the raise_exception parameter is given the PermissionDenied exception
    is raised.
    """
    if isinstance(perm, str):
        perms = (perm,)
    else:
        perms = perm

    def decorator(view_func):
        if iscoroutinefunction(view_func):

            async def check_perms(user):
                # First check if the user has the permission (even anon users).
                if await user.ahas_perms(perms):
                    return True
                # In case the 403 handler should be called raise the exception.
                if raise_exception:
                    raise PermissionDenied
                # As the last resort, show the login form.
                return False

        else:

            def check_perms(user):
                # First check if the user has the permission (even anon users).
                if user.has_perms(perms):
                    return True
                # In case the 403 handler should be called raise the exception.
                if raise_exception:
                    raise PermissionDenied
                # As the last resort, show the login form.
                return False

        return user_passes_test(check_perms, login_url=login_url)(view_func)

    return decorator
