"""
Decorator for views that tries getting the page from the cache and
populates the cache if the page isn't in the cache yet.

The cache is keyed by the URL and some data from the headers. Additionally
there is the key prefix that is used to distinguish different cache areas
in a multi-site setup. You could use the sites.get_current().domain, for
example, as that is unique across a Django project.

Additionally, all headers from the response's Vary header will be taken into
account on caching -- just like the middleware does.
"""

try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.3, 2.4 fallback.

from django.utils.decorators import decorator_from_middleware_with_args, auto_adapt_to_methods
from django.utils.cache import patch_cache_control, add_never_cache_headers
from django.middleware.cache import CacheMiddleware

def cache_page(*args):
    # We need backwards compatibility with code which spells it this way:
    #   def my_view(): pass
    #   my_view = cache_page(my_view, 123)
    # and this way:
    #   my_view = cache_page(123)(my_view)
    # and possibly this way (?):
    #   my_view = cache_page(123, my_view)

    # We also add some asserts to give better error messages in case people are
    # using other ways to call cache_page that no longer work.
    if len(args) > 1:
        assert len(args) == 2, "cache_page accepts at most 2 arguments"
        if callable(args[0]):
            return decorator_from_middleware_with_args(CacheMiddleware)(args[1])(args[0])
        elif callable(args[1]):
            return decorator_from_middleware_with_args(CacheMiddleware)(args[0])(args[1])
        else:
            assert False, "cache_page must be passed either a single argument (timeout) or a view function and a timeout"
    else:
        return decorator_from_middleware_with_args(CacheMiddleware)(args[0])

def cache_control(**kwargs):

    def _cache_controller(viewfunc):

        def _cache_controlled(request, *args, **kw):
            response = viewfunc(request, *args, **kw)
            patch_cache_control(response, **kwargs)
            return response

        return wraps(viewfunc)(_cache_controlled)

    return auto_adapt_to_methods(_cache_controller)

def never_cache(view_func):
    """
    Decorator that adds headers to a response so that it will
    never be cached.
    """
    def _wrapped_view_func(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        add_never_cache_headers(response)
        return response
    return wraps(view_func)(_wrapped_view_func)
never_cache = auto_adapt_to_methods(never_cache)
