from django.middleware.csrf import CsrfViewMiddleware
from django.utils.decorators import decorator_from_middleware, available_attrs

try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.4 fallback.

csrf_protect = decorator_from_middleware(CsrfViewMiddleware)
csrf_protect.__name__ = "csrf_protect"
csrf_protect.__doc__ = """
This decorator adds CSRF protection in exactly the same way as
CsrfViewMiddleware, but it can be used on a per view basis.  Using both, or
using the decorator multiple times, is harmless and efficient.
"""

def csrf_response_exempt(view_func):
    """
    Modifies a view function so that its response is exempt
    from the post-processing of the CSRF middleware.
    """
    def wrapped_view(*args, **kwargs):
        resp = view_func(*args, **kwargs)
        resp.csrf_exempt = True
        return resp
    return wraps(view_func, assigned=available_attrs(view_func))(wrapped_view)

def csrf_view_exempt(view_func):
    """
    Marks a view function as being exempt from CSRF view protection.
    """
    # We could just do view_func.csrf_exempt = True, but decorators
    # are nicer if they don't have side-effects, so we return a new
    # function.
    def wrapped_view(*args, **kwargs):
        return view_func(*args, **kwargs)
    wrapped_view.csrf_exempt = True
    return wraps(view_func, assigned=available_attrs(view_func))(wrapped_view)

def csrf_exempt(view_func):
    """
    Marks a view function as being exempt from the CSRF checks
    and post processing.

    This is the same as using both the csrf_view_exempt and
    csrf_response_exempt decorators.
    """
    return csrf_response_exempt(csrf_view_exempt(view_func))
