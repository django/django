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

A example: i18n middleware would need to distinguish caches by the
"Accept-language" header.
"""

import datetime, md5, re
from django.conf import settings
from django.core.cache import cache

cc_delim_re = re.compile(r'\s*,\s*')
def patch_cache_control(response, **kwargs):
    """
    This function patches the Cache-Control header by adding all
    keyword arguments to it. The transformation is as follows:

    - all keyword parameter names are turned to lowercase and
      all _ will be translated to -
    - if the value of a parameter is True (exatly True, not just a
      true value), only the parameter name is added to the header
    - all other parameters are added with their value, after applying
      str to it.
    """

    def dictitem(s):
        t = s.split('=',1)
        if len(t) > 1:
            return (t[0].lower().replace('-', '_'), t[1])
        else:
            return (t[0].lower().replace('-', '_'), True)

    def dictvalue(t):
        if t[1] == True:
            return t[0]
        else:
            return t[0] + '=' + str(t[1])

    if response.has_header('Cache-Control'):
        cc = cc_delim_re.split(response['Cache-Control'])
        cc = dict([dictitem(el) for el in cc])
    else:
        cc = {}
    for (k,v) in kwargs.items():
        cc[k.replace('_', '-')] = v
    cc = ', '.join([dictvalue(el) for el in cc.items()])
    response['Cache-Control'] = cc

vary_delim_re = re.compile(r',\s*')

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
    now = datetime.datetime.utcnow()
    expires = now + datetime.timedelta(0, cache_timeout)
    if not response.has_header('ETag'):
        response['ETag'] = md5.new(response.content).hexdigest()
    if not response.has_header('Last-Modified'):
        response['Last-Modified'] = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
    if not response.has_header('Expires'):
        response['Expires'] = expires.strftime('%a, %d %b %Y %H:%M:%S GMT')
    patch_cache_control(response, max_age=cache_timeout)

def patch_vary_headers(response, newheaders):
    """
    Adds (or updates) the "Vary" header in the given HttpResponse object.
    newheaders is a list of header names that should be in "Vary". Existing
    headers in "Vary" aren't removed.
    """
    # Note that we need to keep the original order intact, because cache
    # implementations may rely on the order of the Vary contents in, say,
    # computing an MD5 hash.
    vary = []
    if response.has_header('Vary'):
        vary = vary_delim_re.split(response['Vary'])
    oldheaders = dict([(el.lower(), 1) for el in vary])
    for newheader in newheaders:
        if not newheader.lower() in oldheaders:
            vary.append(newheader)
    response['Vary'] = ', '.join(vary)

def _generate_cache_key(request, headerlist, key_prefix):
    "Returns a cache key from the headers given in the header list."
    ctx = md5.new()
    for header in headerlist:
        value = request.META.get(header, None)
        if value is not None:
            ctx.update(value)
    return 'views.decorators.cache.cache_page.%s.%s.%s' % (key_prefix, request.path, ctx.hexdigest())

def get_cache_key(request, key_prefix=None):
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
    cache_key = 'views.decorators.cache.cache_header.%s.%s' % (key_prefix, request.path)
    headerlist = cache.get(cache_key, None)
    if headerlist is not None:
        return _generate_cache_key(request, headerlist, key_prefix)
    else:
        return None

def learn_cache_key(request, response, cache_timeout=None, key_prefix=None):
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
    cache_key = 'views.decorators.cache.cache_header.%s.%s' % (key_prefix, request.path)
    if response.has_header('Vary'):
        headerlist = ['HTTP_'+header.upper().replace('-', '_') for header in vary_delim_re.split(response['Vary'])]
        cache.set(cache_key, headerlist, cache_timeout)
        return _generate_cache_key(request, headerlist, key_prefix)
    else:
        # if there is no Vary header, we still need a cache key
        # for the request.path
        cache.set(cache_key, [], cache_timeout)
        return _generate_cache_key(request, [], key_prefix)
