from django.core.cache import cache
from django.utils.httpwrappers import HttpResponseNotModified
from django.utils.text import compress_string
from django.conf.settings import DEFAULT_CHARSET
import datetime, md5

def cache_page(view_func, cache_timeout, key_prefix=''):
    """
    Decorator for views that tries getting the page from the cache and
    populates the cache if the page isn't in the cache yet. Also takes care
    of ETags and gzips the page if the client supports it.

    The cache is keyed off of the page's URL plus the optional key_prefix
    variable. Use key_prefix if your Django setup has multiple sites that
    use cache; otherwise the cache for one site would affect the other. A good
    example of key_prefix is to use sites.get_current().domain, because that's
    unique across all Django instances on a particular server.
    """
    def _check_cache(request, *args, **kwargs):
        try:
            accept_encoding = request.META['HTTP_ACCEPT_ENCODING']
        except KeyError:
            accept_encoding = ''
        accepts_gzip = 'gzip' in accept_encoding
        cache_key = 'views.decorators.cache.cache_page.%s.%s.%s' % (key_prefix, request.path, accepts_gzip)
        response = cache.get(cache_key, None)
        if response is None:
            response = view_func(request, *args, **kwargs)
            content = response.get_content_as_string(DEFAULT_CHARSET)
            if accepts_gzip:
                content = compress_string(content)
                response.content = content
                response['Content-Encoding'] = 'gzip'
            response['ETag'] = md5.new(content).hexdigest()
            response['Content-Length'] = '%d' % len(content)
            response['Last-Modified'] = datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
            cache.set(cache_key, response, cache_timeout)
        else:
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
    return _check_cache
