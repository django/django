"""
Caching framework.

This package defines set of cache backends that all conform to a simple API.
In a nutshell, a cache is a set of values -- which can be any object that
may be pickled -- identified by string keys.  For the complete API, see
the abstract BaseCache class in django.core.cache.backends.base.

Client code should not access a cache backend directly; instead it should
either use the "cache" variable made available here, or it should use the
get_cache() function made available here. get_cache() takes a backend URI
(e.g. "memcached://127.0.0.1:11211/") and returns an instance of a backend
cache class.

See docs/cache.txt for information on the public API.
"""

from cgi import parse_qsl
from django.conf import settings
from django.core.cache.backends.base import InvalidCacheBackendError

BACKENDS = {
    # name for use in settings file --> name of module in "backends" directory
    'memcached': 'memcached',
    'locmem': 'locmem',
    'file': 'filebased',
    'db': 'db',
    'dummy': 'dummy',
}

DEPRECATED_BACKENDS = {
    # deprecated backend --> replacement module
    'simple': 'locmem',
}

def get_cache(backend_uri):
    if backend_uri.find(':') == -1:
        raise InvalidCacheBackendError, "Backend URI must start with scheme://"
    scheme, rest = backend_uri.split(':', 1)
    if not rest.startswith('//'):
        raise InvalidCacheBackendError, "Backend URI must start with scheme://"
    if scheme in DEPRECATED_BACKENDS:
        import warnings
        warnings.warn("'%s' backend is deprecated. Use '%s' instead." % 
            (scheme, DEPRECATED_BACKENDS[scheme]), DeprecationWarning)
        scheme = DEPRECATED_BACKENDS[scheme]
    if scheme not in BACKENDS:
        raise InvalidCacheBackendError, "%r is not a valid cache backend" % scheme

    host = rest[2:]
    qpos = rest.find('?')
    if qpos != -1:
        params = dict(parse_qsl(rest[qpos+1:]))
        host = rest[2:qpos]
    else:
        params = {}
    if host.endswith('/'):
        host = host[:-1]

    cache_class = getattr(__import__('django.core.cache.backends.%s' % BACKENDS[scheme], {}, {}, ['']), 'CacheClass')
    return cache_class(host, params)

cache = get_cache(settings.CACHE_BACKEND)
