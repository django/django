def login_required(view_func):
    """
    Decorator for views that checks that the user is logged in, redirecting
    to the log-in page if necessary.
    """
    from django.views.auth.login import redirect_to_login
    def _checklogin(request, *args, **kwargs):
        if request.user.is_anonymous():
            return redirect_to_login(request.path)
        else:
            return view_func(request, *args, **kwargs)
    return _checklogin
