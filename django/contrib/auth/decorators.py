from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponseRedirect
from urllib import quote

def user_passes_test(test_func, login_url=None):
    """
    Decorator for views that checks that the user passes the given test,
    redirecting to the log-in page if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.
    """
    if not login_url:
        from django.conf import settings
        login_url = settings.LOGIN_URL
    def _dec(view_func):
        def _checklogin(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            return HttpResponseRedirect('%s?%s=%s' % (login_url, REDIRECT_FIELD_NAME, quote(request.get_full_path())))
        _checklogin.__doc__ = view_func.__doc__
        _checklogin.__dict__ = view_func.__dict__

        return _checklogin
    return _dec

login_required = user_passes_test(lambda u: u.is_authenticated())
login_required.__doc__ = (
    """
    Decorator for views that checks that the user is logged in, redirecting
    to the log-in page if necessary.
    """
    )

def permission_required(perm, login_url=None):
    """
    Decorator for views that checks whether a user has a particular permission
    enabled, redirecting to the log-in page if necessary.
    """
    return user_passes_test(lambda u: u.has_perm(perm), login_url=login_url)

