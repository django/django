import warnings
from functools import wraps
from inspect import iscoroutinefunction

from django.utils.cache import patch_vary_headers


def _vary_on_headers(headers, decorator_name):
    def decorator(func):
        def warn_if_vary_modified_after_cache(response):
            if getattr(response, "_cache_page_cached", False):
                warnings.warn(
                    f"{decorator_name} is calling patch_vary_headers() on a "
                    "response that has already been cached. Ensure the Vary "
                    "header is set before the response is cached.",
                    RuntimeWarning,
                    stacklevel=3,
                )

        if iscoroutinefunction(func):

            async def _view_wrapper(request, *args, **kwargs):
                response = await func(request, *args, **kwargs)
                warn_if_vary_modified_after_cache(response)
                patch_vary_headers(response, headers)
                return response

        else:

            def _view_wrapper(request, *args, **kwargs):
                response = func(request, *args, **kwargs)
                warn_if_vary_modified_after_cache(response)
                patch_vary_headers(response, headers)
                return response

        return wraps(func)(_view_wrapper)

    return decorator


def vary_on_headers(*headers):
    """
    A view decorator that adds the specified headers to the Vary header of the
    response. Usage:

       @vary_on_headers('Cookie', 'Accept-language')
       def index(request):
           ...

    Note that the header names are not case-sensitive.
    """
    return _vary_on_headers(headers, "vary_on_headers()")


vary_on_cookie = _vary_on_headers(("Cookie",), "vary_on_cookie")
vary_on_cookie.__doc__ = (
    'A view decorator that adds "Cookie" to the Vary header of a response. This '
    "indicates that a page's contents depends on cookies."
)
