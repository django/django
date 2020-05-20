"Memcached cache backend"

import pickle
import re
import time

from django.core.cache.backends.base import (
    DEFAULT_TIMEOUT, BaseCache, InvalidCacheKey, memcache_key_warnings,
)
from django.utils.functional import cached_property


class BaseMemcachedCache(BaseCache):
    def __init__(self, server, params, library, value_not_found_exception):
        super().__init__(params)
        if isinstance(server, str):
            self._servers = re.split('[;,]', server)
        else:
            self._servers = server

        # The exception type to catch from the underlying library for a key
        # that was not found. This is a ValueError for python-memcache,
        # pylibmc.NotFound for pylibmc, and cmemcache will return None without
        # raising an exception.
        self.LibraryValueNotFoundException = value_not_found_exception

        self._lib = library
        self._options = params.get('OPTIONS') or {}

    @property
    def _cache(self):
        """
        Implement transparent thread-safe access to a memcached client.
        """
        if getattr(self, '_client', None) is None:
            self._client = self._lib.Client(self._servers, **self._options)

        return self._client

    def get_backend_timeout(self, timeout=DEFAULT_TIMEOUT):
        """
        Memcached deals with long (> 30 days) timeouts in a special
        way. Call this function to obtain a safe value for your timeout.
        """
        if timeout == DEFAULT_TIMEOUT:
            timeout = self.default_timeout

        if timeout is None:
            # Using 0 in memcache sets a non-expiring timeout.
            return 0
        elif int(timeout) == 0:
            # Other cache backends treat 0 as set-and-expire. To achieve this
            # in memcache backends, a negative timeout must be passed.
            timeout = -1

        if timeout > 2592000:  # 60*60*24*30, 30 days
            # See https://github.com/memcached/memcached/wiki/Programming#expiration
            # "Expiration times can be set from 0, meaning "never expire", to
            # 30 days. Any time higher than 30 days is interpreted as a Unix
            # timestamp date. If you want to expire an object on January 1st of
            # next year, this is how you do that."
            #
            # This means that we have to switch to absolute timestamps.
            timeout += int(time.time())
        return int(timeout)

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        return self._cache.add(key, value, self.get_backend_timeout(timeout))

    def get(self, key, default=None, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        return self._cache.get(key, default)

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        if not self._cache.set(key, value, self.get_backend_timeout(timeout)):
            # make sure the key doesn't keep its old value in case of failure to set (memcached's 1MB limit)
            self._cache.delete(key)

    def delete(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        return bool(self._cache.delete(key))

    def get_many(self, keys, version=None):
        key_map = {self.make_key(key, version=version): key for key in keys}
        for key in key_map:
            self.validate_key(key)
        ret = self._cache.get_multi(key_map.keys())
        return {key_map[k]: v for k, v in ret.items()}

    def close(self, **kwargs):
        # Many clients don't clean up connections properly.
        self._cache.disconnect_all()

    def incr(self, key, delta=1, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        # memcached doesn't support a negative delta
        if delta < 0:
            return self._cache.decr(key, -delta)
        try:
            val = self._cache.incr(key, delta)

        # python-memcache responds to incr on nonexistent keys by
        # raising a ValueError, pylibmc by raising a pylibmc.NotFound
        # and Cmemcache returns None. In all cases,
        # we should raise a ValueError though.
        except self.LibraryValueNotFoundException:
            val = None
        if val is None:
            raise ValueError("Key '%s' not found" % key)
        return val

    def decr(self, key, delta=1, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        # memcached doesn't support a negative delta
        if delta < 0:
            return self._cache.incr(key, -delta)
        try:
            val = self._cache.decr(key, delta)

        # python-memcache responds to incr on nonexistent keys by
        # raising a ValueError, pylibmc by raising a pylibmc.NotFound
        # and Cmemcache returns None. In all cases,
        # we should raise a ValueError though.
        except self.LibraryValueNotFoundException:
            val = None
        if val is None:
            raise ValueError("Key '%s' not found" % key)
        return val

    def set_many(self, data, timeout=DEFAULT_TIMEOUT, version=None):
        safe_data = {}
        original_keys = {}
        for key, value in data.items():
            safe_key = self.make_key(key, version=version)
            self.validate_key(safe_key)
            safe_data[safe_key] = value
            original_keys[safe_key] = key
        failed_keys = self._cache.set_multi(safe_data, self.get_backend_timeout(timeout))
        return [original_keys[k] for k in failed_keys]

    def delete_many(self, keys, version=None):
        self._cache.delete_multi(self.make_key(key, version=version) for key in keys)

    def clear(self):
        self._cache.flush_all()

    def validate_key(self, key):
        for warning in memcache_key_warnings(key):
            raise InvalidCacheKey(warning)


class MemcachedCache(BaseMemcachedCache):
    "An implementation of a cache binding using python-memcached"
    def __init__(self, server, params):
        import memcache
        super().__init__(server, params, library=memcache, value_not_found_exception=ValueError)

    @property
    def _cache(self):
        if getattr(self, '_client', None) is None:
            client_kwargs = {'pickleProtocol': pickle.HIGHEST_PROTOCOL}
            client_kwargs.update(self._options)
            self._client = self._lib.Client(self._servers, **client_kwargs)
        return self._client

    def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        return self._cache.touch(key, self.get_backend_timeout(timeout)) != 0

    def get(self, key, default=None, version=None):
        key = self.make_key(key, version=version)
        val = self._cache.get(key)
        # python-memcached doesn't support default values in get().
        # https://github.com/linsomniac/python-memcached/issues/159
        # Remove this method if that issue is fixed.
        if val is None:
            return default
        return val

    def delete(self, key, version=None):
        # python-memcached's delete() returns True when key doesn't exist.
        # https://github.com/linsomniac/python-memcached/issues/170
        # Call _deletetouch() without the NOT_FOUND in expected results.
        key = self.make_key(key, version=version)
        return bool(self._cache._deletetouch([b'DELETED'], 'delete', key))


class PyLibMCCache(BaseMemcachedCache):
    "An implementation of a cache binding using pylibmc"
    def __init__(self, server, params):
        import pylibmc
        super().__init__(server, params, library=pylibmc, value_not_found_exception=pylibmc.NotFound)

    @cached_property
    def _cache(self):
        return self._lib.Client(self._servers, **self._options)

    def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        if timeout == 0:
            return self._cache.delete(key)
        return self._cache.touch(key, self.get_backend_timeout(timeout))

    def close(self, **kwargs):
        # libmemcached manages its own connections. Don't call disconnect_all()
        # as it resets the failover state and creates unnecessary reconnects.
        pass
