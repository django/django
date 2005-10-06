from django.conf import settings
from django.core.cache import cache
from django.utils.httpwrappers import HttpResponseNotModified
from django.utils.text import compress_string
import datetime, md5

class CacheMiddleware:
    """
    Cache middleware. If this is enabled, each Django-powered page will be
    cached for CACHE_MIDDLEWARE_SECONDS seconds. Cache is based on URLs. Pages
    with GET or POST parameters are not cached.

    If the cache is shared across multiple sites using the same Django
    installation, set the CACHE_MIDDLEWARE_KEY_PREFIX to the name of the site,
    or some other string that is unique to this Django instance, to prevent key
    collisions.

    This middleware will also make the following optimizations:

    * If the CACHE_MIDDLEWARE_GZIP setting is True, the content will be
      gzipped.

    * ETags will be added, using a simple MD5 hash of the page's content.
    """
    def process_request(self, request):
        """
        Checks whether the page is already cached. If it is, returns the cached
        version. Also handles ETag stuff.
        """
        if request.GET or request.POST:
            request._cache_middleware_set_cache = False
            return None # Don't bother checking the cache.

        accept_encoding = ''
        if settings.CACHE_MIDDLEWARE_GZIP:
            try:
                accept_encoding = request.META['HTTP_ACCEPT_ENCODING']
            except KeyError:
                pass
        accepts_gzip = 'gzip' in accept_encoding
        request._cache_middleware_accepts_gzip = accepts_gzip

        # This uses the same cache_key as views.decorators.cache.cache_page,
        # so the cache can be shared.
        cache_key = 'views.decorators.cache.cache_page.%s.%s.%s' % \
            (settings.CACHE_MIDDLEWARE_KEY_PREFIX, request.path, accepts_gzip)
        request._cache_middleware_key = cache_key

        response = cache.get(cache_key, None)
        if response is None:
            request._cache_middleware_set_cache = True
            return None
        else:
            request._cache_middleware_set_cache = False
            # Logic is from http://simon.incutio.com/archive/2003/04/23/conditionalGet
            try:
                if_none_match = request.META['HTTP_IF_NONE_MATCH']
            except KeyError:
                if_none_match = None
            try:
                if_modified_since = request.META['HTTP_IF_MODIFIED_SINCE']
            except KeyError:
                if_modified_since = None
            if if_none_match is None and if_modified_since is None:
                pass
            elif if_none_match is not None and response['ETag'] != if_none_match:
                pass
            elif if_modified_since is not None and response['Last-Modified'] != if_modified_since:
                pass
            else:
                return HttpResponseNotModified()
        return response

    def process_response(self, request, response):
        """
        Sets the cache, if needed.
        """
        if request._cache_middleware_set_cache:
            content = response.get_content_as_string(settings.DEFAULT_CHARSET)
            if request._cache_middleware_accepts_gzip:
                content = compress_string(content)
                response.content = content
                response['Content-Encoding'] = 'gzip'
            response['ETag'] = md5.new(content).hexdigest()
            response['Content-Length'] = '%d' % len(content)
            response['Last-Modified'] = datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
            cache.set(request._cache_middleware_key, response, settings.CACHE_MIDDLEWARE_SECONDS)
        return response
