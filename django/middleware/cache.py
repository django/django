"""
Cache middleware. If enabled, each Django-powered page will be cached based on
URL. The canonical way to enable cache middleware is to set
``UpdateCacheMiddleware`` as your first piece of middleware, and
``FetchFromCacheMiddleware`` as the last::

    MIDDLEWARE = [
        'django.middleware.cache.UpdateCacheMiddleware',
        ...
        'django.middleware.cache.FetchFromCacheMiddleware'
    ]

This is counter-intuitive, but correct: ``UpdateCacheMiddleware`` needs to run
last during the response phase, which processes middleware bottom-up;
``FetchFromCacheMiddleware`` needs to run last during the request phase, which
processes middleware top-down.

The single-class ``CacheMiddleware`` can be used for some simple sites.
However, if any other piece of middleware needs to affect the cache key, you'll
need to use the two-part ``UpdateCacheMiddleware`` and
``FetchFromCacheMiddleware``. This'll most often happen when you're using
Django's ``LocaleMiddleware``.

More details about how the caching works:

* Only GET or HEAD-requests with status code 200 are cached.

* The number of seconds each page is stored for is set by the "max-age" section
  of the response's "Cache-Control" header, falling back to the
  CACHE_MIDDLEWARE_SECONDS setting if the section was not found.

* This middleware expects that a HEAD request is answered with the same response
  headers exactly like the corresponding GET request.

* When a hit occurs, a shallow copy of the original response object is returned
  from process_request.

* Pages will be cached based on the contents of the request headers listed in
  the response's "Vary" header.

* This middleware also sets ETag, Last-Modified, Expires and Cache-Control
  headers on the response object.

"""

from django.conf import settings
from django.core.cache import DEFAULT_CACHE_ALIAS, caches
from django.utils.cache import (
    get_cache_key,
    get_max_age,
    has_vary_header,
    learn_cache_key,
    patch_response_headers,
)
from django.utils.deprecation import MiddlewareMixin


class UpdateCacheMiddleware(MiddlewareMixin):
    """
    Response-phase cache middleware that updates the cache if the response is
    cacheable.

    Must be used as part of the two-part update/fetch cache middleware.
    UpdateCacheMiddleware must be the first piece of middleware in MIDDLEWARE
    so that it'll get called last during the response phase.
    """

    def __init__(self, get_response):
        super().__init__(get_response)
        self.cache_timeout = settings.CACHE_MIDDLEWARE_SECONDS
        self.page_timeout = None
        self.key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
        self.cache_alias = settings.CACHE_MIDDLEWARE_ALIAS
        self.cache = caches[self.cache_alias]

    def _should_update_cache(self, request, response):
        return hasattr(request, "_cache_update_cache") and request._cache_update_cache

    def process_response(self, request, response):
        """Set the cache, if needed."""
        if not self._should_update_cache(request, response):
            # We don't need to update the cache, just return.
            return response

        if response.streaming or response.status_code not in (200, 304):
            return response

        # Don't cache responses that set a user-specific (and maybe security
        # sensitive) cookie in response to a cookie-less request.
        if (
            not request.COOKIES
            and response.cookies
            and has_vary_header(response, "Cookie")
        ):
            return response

        # Don't cache a response with 'Cache-Control: private'
        if "private" in response.get("Cache-Control", ()):
            return response

        # Page timeout takes precedence over the "max-age" and the default
        # cache timeout.
        timeout = self.page_timeout
        if timeout is None:
            # The timeout from the "max-age" section of the "Cache-Control"
            # header takes precedence over the default cache timeout.
            timeout = get_max_age(response)
            if timeout is None:
                timeout = self.cache_timeout
            elif timeout == 0:
                # max-age was set to 0, don't cache.
                return response
        patch_response_headers(response, timeout)
        if timeout and response.status_code == 200:
            cache_key = learn_cache_key(
                request, response, timeout, self.key_prefix, cache=self.cache
            )
            if hasattr(response, "render") and callable(response.render):
                response.add_post_render_callback(
                    lambda r: self.cache.set(cache_key, r, timeout)
                )
            else:
                self.cache.set(cache_key, response, timeout)
        return response


class FetchFromCacheMiddleware(MiddlewareMixin):
    """
    Request-phase cache middleware that fetches a page from the cache.

    Must be used as part of the two-part update/fetch cache middleware.
    FetchFromCacheMiddleware must be the last piece of middleware in MIDDLEWARE
    so that it'll get called last during the request phase.
    """

    def __init__(self, get_response):
        super().__init__(get_response)
        self.key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
        self.cache_alias = settings.CACHE_MIDDLEWARE_ALIAS
        self.cache = caches[self.cache_alias]

    def process_request(self, request):
        """
        Check whether the page is already cached and return the cached
        version if available.
        """
        if request.method not in ("GET", "HEAD"):
            request._cache_update_cache = False
            return None  # Don't bother checking the cache.

        # try and get the cached GET response
        cache_key = get_cache_key(request, self.key_prefix, "GET", cache=self.cache)
        if cache_key is None:
            request._cache_update_cache = True
            return None  # No cache information available, need to rebuild.
        response = self.cache.get(cache_key)
        # if it wasn't found and we are looking for a HEAD, try looking just for that
        if response is None and request.method == "HEAD":
            cache_key = get_cache_key(
                request, self.key_prefix, "HEAD", cache=self.cache
            )
            response = self.cache.get(cache_key)

        if response is None:
            request._cache_update_cache = True
            return None  # No cache information available, need to rebuild.

        # hit, return cached response
        request._cache_update_cache = False
        return response


class CacheMiddleware(UpdateCacheMiddleware, FetchFromCacheMiddleware):
    """
    Cache middleware that provides basic behavior for many simple sites.

    Also used as the hook point for the cache decorator, which is generated
    using the decorator-from-middleware utility.
    """

    def __init__(self, get_response, cache_timeout=None, page_timeout=None, **kwargs):
        super().__init__(get_response)
        # We need to differentiate between "provided, but using default value",
        # and "not provided". If the value is provided using a default, then
        # we fall back to system defaults. If it is not provided at all,
        # we need to use middleware defaults.

        try:
            key_prefix = kwargs["key_prefix"]
            if key_prefix is None:
                key_prefix = ""
            self.key_prefix = key_prefix
        except KeyError:
            pass
        try:
            cache_alias = kwargs["cache_alias"]
            if cache_alias is None:
                cache_alias = DEFAULT_CACHE_ALIAS
            self.cache_alias = cache_alias
            self.cache = caches[self.cache_alias]
        except KeyError:
            pass

        if cache_timeout is not None:
            self.cache_timeout = cache_timeout
        self.page_timeout = page_timeout
