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

from django.utils.decorators import decorator_from_middleware
from django.middleware.cache import CacheMiddleware

cache_page = decorator_from_middleware(CacheMiddleware)
