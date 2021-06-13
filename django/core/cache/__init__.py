"""
Caching framework.

This package defines set of cache backends that all conform to a simple API.
In a nutshell, a cache is a set of values -- which can be any object that
may be pickled -- identified by string keys.  For the complete API, see
the abstract BaseCache class in django.core.cache.backends.base.

Client code should use the `cache` variable defined here to access the default
cache backend and look up non-default cache backends in the `caches` dict-like
object.

See docs/topics/cache.txt for information on the public API.
"""
from django.core import signals
from django.core.cache.backends.base import (
    BaseCache, CacheKeyWarning, InvalidCacheBackendError, InvalidCacheKey,
)
from django.utils.connection import BaseConnectionHandler, ConnectionProxy
from django.utils.module_loading import import_string

__all__ = [
    'cache', 'caches', 'DEFAULT_CACHE_ALIAS', 'InvalidCacheBackendError',
    'CacheKeyWarning', 'BaseCache', 'InvalidCacheKey',
]

DEFAULT_CACHE_ALIAS = 'default'


class CacheHandler(BaseConnectionHandler):
    settings_name = 'CACHES'
    exception_class = InvalidCacheBackendError

    def create_connection(self, alias):
        params = self.settings[alias].copy()
        backend = params.pop('BACKEND')
        location = params.pop('LOCATION', '')
        try:
            backend_cls = import_string(backend)
        except ImportError as e:
            raise InvalidCacheBackendError(
                "Could not find backend '%s': %s" % (backend, e)
            ) from e
        return backend_cls(location, params)

    def all(self, initialized_only=False):
        return [
            self[alias] for alias in self
            # If initialized_only is True, return only initialized caches.
            if not initialized_only or hasattr(self._connections, alias)
        ]


caches = CacheHandler()

cache = ConnectionProxy(caches, DEFAULT_CACHE_ALIAS)


def close_caches(**kwargs):
    # Some caches need to do a cleanup at the end of a request cycle. If not
    # implemented in a particular backend cache.close() is a no-op.
    for cache in caches.all(initialized_only=True):
        cache.close()


signals.request_finished.connect(close_caches)
