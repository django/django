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
from threading import local
import warnings

from django.conf import settings
from django.core import signals
from django.core.cache.backends.base import (
    InvalidCacheBackendError, CacheKeyWarning, BaseCache)
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_by_path


__all__ = [
    'create_cache', 'get_cache', 'cache', 'DEFAULT_CACHE_ALIAS',
    'InvalidCacheBackendError', 'CacheKeyWarning', 'BaseCache',
]

DEFAULT_CACHE_ALIAS = 'default'

if DEFAULT_CACHE_ALIAS not in settings.CACHES:
    raise ImproperlyConfigured("You must define a '%s' cache" % DEFAULT_CACHE_ALIAS)


def get_cache(backend, **kwargs):
    """
    Function to retrieve a configure cache, or create a new one.

    This wrapper is for backward compatibility.

    Use either create_cache or caches directly.

    """
    warnings.warn("'get_cache' is deprecated.  Use either caches or create_cache.",
        PendingDeprecationWarning, stacklevel=2)

    # If it's just an alias with no options, use the new API
    if backend in settings.CACHES and not kwargs:
        return caches[backend]

    return create_cache(backend, **kwargs)


def create_cache(backend, **params):
    """
    Function to create a cache backend dynamically.  This is flexible by design
    to allow different use cases:

    To load a backend with its dotted import path, including options::

        cache = get_cache('django.core.cache.backends.memcached.MemcachedCache',
            LOCATION='127.0.0.1:11211', TIMEOUT=30,
        })

    To create a new instance of a cache in settings.CACHES, pass the alias::

        cache = create_cache('default')

    You can also pass extra parameters to override those in settings.CACHES::

        cache = create_cache('default', LOCATION='bar')

    """

    # We can name a cache from settings.CACHES and update its params
    try:
        conf = settings.CACHES[backend]
    except KeyError:
        pass
    else:
        params = conf.copy()
        params.update(params)
        backend = params.pop('BACKEND')

    try:
        backend_cls = import_by_path(backend)
    except ImproperlyConfigured as e:
        raise InvalidCacheBackendError("Could not find backend '%s': %s" % (
            backend, e
        ))
    location = params.pop('LOCATION', '')
    cache = backend_cls(location, params)
    # Some caches -- python-memcached in particular -- need to do a cleanup at the
    # end of a request cycle. If not implemented in a particular backend
    # cache.close is a no-op
    signals.request_finished.connect(cache.close)
    return cache


class CacheHandler(object):
    """
    A Cache Handler to manage access to Cache instances.

    Ensures only one instance of each alias exists per thread.
    """
    def __init__(self):
        self._caches = local()

    def __getitem__(self, alias):
        try:
            return getattr(self._caches, alias)
        except AttributeError:
            pass

        if alias not in settings.CACHES:
            raise InvalidCacheBackendError(
                "Could not find config for '%s' in settings.CACHES" % alias
            )

        cache = create_cache(alias)
        setattr(self._caches, alias, cache)

        return cache

caches = CacheHandler()

class DefaultCacheProxy(object):
    """
    Proxy access to the default Cache object's attributes.

    This allows the legacy `cache` object to be thread-safe using the new
    ``caches`` API.
    """
    def __getattr__(self, name):
        return getattr(caches[DEFAULT_CACHE_ALIAS], name)

    def __setattr__(self, name, value):
        return setattr(caches[DEFAULT_CACHE_ALIAS], name, value)

    def __delattr__(self, name):
        return delattr(caches[DEFAULT_CACHE_ALIAS], name)

    def __eq__(self, other):
        return caches[DEFAULT_CACHE_ALIAS] == other

    def __ne__(self, other):
        return caches[DEFAULT_CACHE_ALIAS] != other

cache = DefaultCacheProxy()
