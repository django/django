import copy
from django.conf import settings
from django.core.cache import cache
from django.utils.cache import get_cache_key, learn_cache_key, patch_response_headers
from django.utils.httpwrappers import HttpResponseNotModified

class CacheMiddleware:
    """
    Cache middleware. If this is enabled, each Django-powered page will be
    cached for CACHE_MIDDLEWARE_SECONDS seconds. Cache is based on URLs.

    Only parameter-less GET or HEAD-requests with status code 200 are cached.

    This middleware expects that a HEAD request is answered with a response
    exactly like the corresponding GET request.

    When a hit occurs, a shallow copy of the original response object is
    returned from process_request.

    Pages will be cached based on the contents of the request headers
    listed in the response's "Vary" header. This means that pages shouldn't
    change their "Vary" header.

    This middleware also sets ETag, Last-Modified, Expires and Cache-Control
    headers on the response object.
    """
    def __init__(self, cache_timeout=None, key_prefix=None):
        self.cache_timeout = cache_timeout
        if cache_timeout is None:
            self.cache_timeout = settings.CACHE_MIDDLEWARE_SECONDS
        self.key_prefix = key_prefix
        if key_prefix is None:
            self.key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX

    def process_request(self, request):
        "Checks whether the page is already cached and returns the cached version if available."
        if not request.META['REQUEST_METHOD'] in ('GET', 'HEAD') or request.GET:
            request._cache_update_cache = False
            return None # Don't bother checking the cache.

        cache_key = get_cache_key(request, self.key_prefix)
        if cache_key is None:
            request._cache_update_cache = True
            return None # No cache information available, need to rebuild.

        response = cache.get(cache_key, None)
        if response is None:
            request._cache_update_cache = True
            return None # No cache information available, need to rebuild.

        request._cache_update_cache = False
        return copy.copy(response)

    def process_response(self, request, response):
        "Sets the cache, if needed."
        if not request._cache_update_cache:
            # We don't need to update the cache, just return.
            return response
        if not request.META['REQUEST_METHOD'] == 'GET':
            # This is a stronger requirement than above. It is needed
            # because of interactions between this middleware and the
            # HTTPMiddleware, which throws the body of a HEAD-request
            # away before this middleware gets a chance to cache it.
            return response
        if not response.status_code == 200:
            return response
        patch_response_headers(response, self.cache_timeout)
        cache_key = learn_cache_key(request, response, self.cache_timeout, self.key_prefix)
        cache.set(cache_key, response, self.cache_timeout)
        return response
