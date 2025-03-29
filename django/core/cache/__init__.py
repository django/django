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
import threading

from django.core import signals
from django.core.cache.backends.base import (
    BaseCache,
    CacheKeyWarning,
    InvalidCacheBackendError,
    InvalidCacheKey,
)
from django.utils.connection import BaseConnectionHandler, ConnectionProxy
from django.utils.module_loading import import_string

__all__ = [
    "cache",
    "caches",
    "DEFAULT_CACHE_ALIAS",
    "InvalidCacheBackendError",
    "CacheKeyWarning",
    "BaseCache",
    "InvalidCacheKey",
]

DEFAULT_CACHE_ALIAS = "default"


class CacheHandler(BaseConnectionHandler):
    settings_name = "CACHES"
    exception_class = InvalidCacheBackendError

    def __init__(self, settings=None):
        super().__init__(settings)
        # Store thread-safe connections here
        self._global_connections = {}

    def create_connection(self, alias):
        if alias in self._global_connections:
            return self._global_connections[alias]

        params = self.settings[alias].copy()
        backend = params.pop("BACKEND")
        location = params.pop("LOCATION", "")
        try:
            backend_cls = import_string(backend)
        except ImportError as e:
            raise InvalidCacheBackendError(
                "Could not find backend '%s': %s" % (backend, e)
            ) from e

        with threading.Lock():
            connection = backend_cls(location, params)
            if not connection.thread_sensitive:
                self._global_connections[alias] = connection

        return connection


caches = CacheHandler()

cache = ConnectionProxy(caches, DEFAULT_CACHE_ALIAS)


def close_caches(**kwargs):
    # Some caches need to do a cleanup at the end of a request cycle. If not
    # implemented in a particular backend cache.close() is a no-op.
    caches.close_all()


# TODO: doesnt close anything on ASGI because of asgiref.Local
signals.request_finished.connect(close_caches)
