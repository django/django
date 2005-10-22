def user_passes_test(view_func, test_func):
    """
    Decorator for views that checks that the user passes the given test,
    redirecting to the log-in page if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.
    """
    from django.views.auth.login import redirect_to_login
    def _checklogin(request, *args, **kwargs):
        if test_func(request.user):
            return view_func(request, *args, **kwargs)
        return redirect_to_login(request.path)
    return _checklogin

def login_required(view_func):
    """
    Decorator for views that checks that the user is logged in, redirecting
    to the log-in page if necessary.
    """
    return user_passes_test(lambda u: not u.is_anonymous())
