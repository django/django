try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.4 fallback.

from django.utils.cache import patch_vary_headers
from django.utils.decorators import available_attrs

def vary_on_headers(*headers):
    """
    A view decorator that adds the specified headers to the Vary header of the
    response. Usage:

       @vary_on_headers('Cookie', 'Accept-language')
       def index(request):
           ...

    Note that the header names are not case-sensitive.
    """
    def decorator(func):
        def inner_func(*args, **kwargs):
            response = func(*args, **kwargs)
            patch_vary_headers(response, headers)
            return response
        return wraps(func, assigned=available_attrs(func))(inner_func)
    return decorator

def vary_on_cookie(func):
    """
    A view decorator that adds "Cookie" to the Vary header of a response. This
    indicates that a page's contents depends on cookies. Usage:

        @vary_on_cookie
        def index(request):
            ...
    """
    def inner_func(*args, **kwargs):
        response = func(*args, **kwargs)
        patch_vary_headers(response, ('Cookie',))
        return response
    return wraps(func, assigned=available_attrs(func))(inner_func)
