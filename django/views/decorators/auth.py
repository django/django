from django.contrib.auth.views import redirect_to_login

def user_passes_test(test_func, login_url=login.LOGIN_URL):
    """
    Decorator for views that checks that the user passes the given test,
    redirecting to the log-in page if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.
    """
    def _dec(view_func):
        def _checklogin(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            return redirect_to_login(request.path, login_url)
        return _checklogin
    return _dec

login_required = user_passes_test(lambda u: not u.is_anonymous())
login_required.__doc__ = (
    """
    Decorator for views that checks that the user is logged in, redirecting
    to the log-in page if necessary.
    """
    )
