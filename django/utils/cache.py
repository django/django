"""
This module contains helper functions for controlling caching. It does so by
managing the "Vary" header of responses. It includes functions to patch the
header of response objects directly and decorators that change functions to do
that header-patching themselves.

For information on the Vary header, see:

    http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.44

Essentially, the "Vary" HTTP header defines which headers a cache should take
into account when building its cache key. Requests with the same path but
different header content for headers named in "Vary" need to get different
cache keys to prevent delivery of wrong content.

An example: i18n middleware would need to distinguish caches by the
"Accept-language" header.
"""

import re
import time

from django.conf import settings
from django.core.cache import get_cache
from django.utils.encoding import smart_str, iri_to_uri
from django.utils.http import http_date
from django.utils.hashcompat import md5_constructor
from django.utils.translation import get_language
from django.http import HttpRequest

cc_delim_re = re.compile(r'\s*,\s*')

def patch_cache_control(response, **kwargs):
    """
    This function patches the Cache-Control header by adding all
    keyword arguments to it. The transformation is as follows:

    * All keyword parameter names are turned to lowercase, and underscores
      are converted to hyphens.
    * If the value of a parameter is True (exactly True, not just a
      true value), only the parameter name is added to the header.
    * All other parameters are added with their value, after applying
      str() to it.
    """
    def dictitem(s):
        t = s.split('=', 1)
        if len(t) > 1:
            return (t[0].lower(), t[1])
        else:
            return (t[0].lower(), True)

    def dictvalue(t):
        if t[1] is True:
            return t[0]
        else:
            return t[0] + '=' + smart_str(t[1])

    if response.has_header('Cache-Control'):
        cc = cc_delim_re.split(response['Cache-Control'])
        cc = dict([dictitem(el) for el in cc])
    else:
        cc = {}

    # If there's already a max-age header but we're being asked to set a new
    # max-age, use the minimum of the two ages. In practice this happens when
    # a decorator and a piece of middleware both operate on a given view.
    if 'max-age' in cc and 'max_age' in kwargs:
        kwargs['max_age'] = min(cc['max-age'], kwargs['max_age'])

    for (k, v) in kwargs.items():
        cc[k.replace('_', '-')] = v
    cc = ', '.join([dictvalue(el) for el in cc.items()])
    response['Cache-Control'] = cc

def get_max_age(response):
    """
    Returns the max-age from the response Cache-Control header as an integer
    (or ``None`` if it wasn't found or wasn't an integer.
    """
    if not response.has_header('Cache-Control'):
        return
    cc = dict([_to_tuple(el) for el in
        cc_delim_re.split(response['Cache-Control'])])
    if 'max-age' in cc:
        try:
            return int(cc['max-age'])
        except (ValueError, TypeError):
            pass

def patch_response_headers(response, cache_timeout=None):
    """
    Adds some useful headers to the given HttpResponse object:
        ETag, Last-Modified, Expires and Cache-Control

    Each header is only added if it isn't already set.

    cache_timeout is in seconds. The CACHE_MIDDLEWARE_SECONDS setting is used
    by default.
    """
    if cache_timeout is None:
        cache_timeout = settings.CACHE_MIDDLEWARE_SECONDS
    if cache_timeout < 0:
        cache_timeout = 0 # Can't have max-age negative
    if settings.USE_ETAGS and not response.has_header('ETag'):
        response['ETag'] = '"%s"' % md5_constructor(response.content).hexdigest()
    if not response.has_header('Last-Modified'):
        response['Last-Modified'] = http_date()
    if not response.has_header('Expires'):
        response['Expires'] = http_date(time.time() + cache_timeout)
    patch_cache_control(response, max_age=cache_timeout)

def add_never_cache_headers(response):
    """
    Adds headers to a response to indicate that a page should never be cached.
    """
    patch_response_headers(response, cache_timeout=-1)

def patch_vary_headers(response, newheaders):
    """
    Adds (or updates) the "Vary" header in the given HttpResponse object.
    newheaders is a list of header names that should be in "Vary". Existing
    headers in "Vary" aren't removed.
    """
    # Note that we need to keep the original order intact, because cache
    # implementations may rely on the order of the Vary contents in, say,
    # computing an MD5 hash.
    if response.has_header('Vary'):
        vary_headers = cc_delim_re.split(response['Vary'])
    else:
        vary_headers = []
    # Use .lower() here so we treat headers as case-insensitive.
    existing_headers = set([header.lower() for header in vary_headers])
    additional_headers = [newheader for newheader in newheaders
                          if newheader.lower() not in existing_headers]
    response['Vary'] = ', '.join(vary_headers + additional_headers)

def _i18n_cache_key_suffix(request, cache_key):
    """If enabled, returns the cache key ending with a locale."""
    if settings.USE_I18N:
        # first check if LocaleMiddleware or another middleware added
        # LANGUAGE_CODE to request, then fall back to the active language
        # which in turn can also fall back to settings.LANGUAGE_CODE
        cache_key += '.%s' % getattr(request, 'LANGUAGE_CODE', get_language())
    return cache_key

def _generate_cache_key(request, method, headerlist, key_prefix):
    """Returns a cache key from the headers given in the header list."""
    ctx = md5_constructor()
    for header in headerlist:
        value = request.META.get(header, None)
        if value is not None:
            ctx.update(value)
    path = md5_constructor(iri_to_uri(request.path))
    cache_key = 'views.decorators.cache.cache_page.%s.%s.%s.%s' % (
        key_prefix, request.method, path.hexdigest(), ctx.hexdigest())
    return _i18n_cache_key_suffix(request, cache_key)

def _generate_cache_header_key(key_prefix, request):
    """Returns a cache key for the header cache."""
    path = md5_constructor(iri_to_uri(request.path))
    cache_key = 'views.decorators.cache.cache_header.%s.%s' % (
        key_prefix, path.hexdigest())
    return _i18n_cache_key_suffix(request, cache_key)

def get_cache_key(request, key_prefix=None, method='GET', cache=None):
    """
    Returns a cache key based on the request path. It can be used in the
    request phase because it pulls the list of headers to take into account
    from the global path registry and uses those to build a cache key to check
    against.

    If there is no headerlist stored, the page needs to be rebuilt, so this
    function returns None.
    """
    if key_prefix is None:
        key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
    cache_key = _generate_cache_header_key(key_prefix, request)
    if cache is None:
        cache = get_cache(settings.CACHE_MIDDLEWARE_ALIAS)
    headerlist = cache.get(cache_key, None)
    if headerlist is not None:
        return _generate_cache_key(request, method, headerlist, key_prefix)
    else:
        return None

def learn_cache_key(request, response, cache_timeout=None, key_prefix=None, cache=None):
    """
    Learns what headers to take into account for some request path from the
    response object. It stores those headers in a global path registry so that
    later access to that path will know what headers to take into account
    without building the response object itself. The headers are named in the
    Vary header of the response, but we want to prevent response generation.

    The list of headers to use for cache key generation is stored in the same
    cache as the pages themselves. If the cache ages some data out of the
    cache, this just means that we have to build the response once to get at
    the Vary header and so at the list of headers to use for the cache key.
    """
    if key_prefix is None:
        key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
    if cache_timeout is None:
        cache_timeout = settings.CACHE_MIDDLEWARE_SECONDS
    cache_key = _generate_cache_header_key(key_prefix, request)
    if cache is None:
        cache = get_cache(settings.CACHE_MIDDLEWARE_ALIAS)
    if response.has_header('Vary'):
        headerlist = ['HTTP_'+header.upper().replace('-', '_')
                      for header in cc_delim_re.split(response['Vary'])]
        cache.set(cache_key, headerlist, cache_timeout)
        return _generate_cache_key(request, request.method, headerlist, key_prefix)
    else:
        # if there is no Vary header, we still need a cache key
        # for the request.path
        cache.set(cache_key, [], cache_timeout)
        return _generate_cache_key(request, request.method, [], key_prefix)


def _to_tuple(s):
    t = s.split('=',1)
    if len(t) == 2:
        return t[0].lower(), t[1]
    return t[0].lower(), True
