from django.contrib.auth import LOGIN_URL, REDIRECT_FIELD_NAME
from django.http import HttpResponseRedirect

def user_passes_test(test_func, login_url=LOGIN_URL):
    """
    Decorator for views that checks that the user passes the given test,
    redirecting to the log-in page if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.
    """
    def _dec(view_func):
        def _checklogin(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            return HttpResponseRedirect('%s?%s=%s' % (login_url, REDIRECT_FIELD_NAME, request.path))

        return _checklogin
    return _dec

login_required = user_passes_test(lambda u: not u.is_anonymous())
login_required.__doc__ = (
    """
    Decorator for views that checks that the user is logged in, redirecting
    to the log-in page if necessary.
    """
    )
