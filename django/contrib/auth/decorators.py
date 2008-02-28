try:
    from functools import wraps, update_wrapper
except ImportError:
    from django.utils.functional import wraps, update_wrapper  # Python 2.3, 2.4 fallback.

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponseRedirect
from django.utils.http import urlquote

def user_passes_test(test_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Decorator for views that checks that the user passes the given test,
    redirecting to the log-in page if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.
    """
    def decorate(view_func):
        return _CheckLogin(view_func, test_func, login_url, redirect_field_name)
    return decorate

def login_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Decorator for views that checks that the user is logged in, redirecting
    to the log-in page if necessary.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated(),
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

def permission_required(perm, login_url=None):
    """
    Decorator for views that checks whether a user has a particular permission
    enabled, redirecting to the log-in page if necessary.
    """
    return user_passes_test(lambda u: u.has_perm(perm), login_url=login_url)

class _CheckLogin(object):
    """
    Class that checks that the user passes the given test, redirecting to
    the log-in page if necessary. If the test is passed, the view function
    is invoked. The test should be a callable that takes the user object
    and returns True if the user passes.

    We use a class here so that we can define __get__. This way, when a
    _CheckLogin object is used as a method decorator, the view function
    is properly bound to its instance.
    """
    def __init__(self, view_func, test_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):
        if not login_url:
            from django.conf import settings
            login_url = settings.LOGIN_URL
        self.view_func = view_func
        self.test_func = test_func
        self.login_url = login_url
        self.redirect_field_name = redirect_field_name
        update_wrapper(self, view_func)
        
    def __get__(self, obj, cls=None):
        view_func = self.view_func.__get__(obj, cls)
        return _CheckLogin(view_func, self.test_func, self.login_url, self.redirect_field_name)
    
    def __call__(self, request, *args, **kwargs):
        if self.test_func(request.user):
            return self.view_func(request, *args, **kwargs)
        path = urlquote(request.get_full_path())
        tup = self.login_url, self.redirect_field_name, path
        return HttpResponseRedirect('%s?%s=%s' % tup)
