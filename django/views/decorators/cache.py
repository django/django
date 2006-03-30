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
import re

from django.utils.decorators import decorator_from_middleware
from django.utils.cache import patch_cache_control, add_never_cache_headers
from django.middleware.cache import CacheMiddleware

cache_page = decorator_from_middleware(CacheMiddleware)

def cache_control(**kwargs):

    def _cache_controller(viewfunc):

        def _cache_controlled(request, *args, **kw):
            response = viewfunc(request, *args, **kw)
            patch_cache_control(response, **kwargs)
            return response

        return _cache_controlled

    return _cache_controller

def never_cache(view_func):
    """
    Decorator that adds headers to a response so that it will
    never be cached.
    """
    def _wrapped_view_func(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        add_never_cache_headers(response)
        return response
    return _wrapped_view_func
