"Memcached cache backend"

import time

from django.core.cache.backends.base import BaseCache, InvalidCacheBackendError
from django.utils.encoding import smart_unicode, smart_str

try:
    import cmemcache as memcache
except ImportError:
    try:
        import memcache
    except:
        raise InvalidCacheBackendError("Memcached cache backend requires either the 'memcache' or 'cmemcache' library")

class CacheClass(BaseCache):
    def __init__(self, server, params):
        BaseCache.__init__(self, params)
        self._cache = memcache.Client(server.split(';'))

    def _get_memcache_timeout(self, timeout):
        """
        Memcached deals with long (> 30 days) timeouts in a special
        way. Call this function to obtain a safe value for your timeout.
        """
        timeout = timeout or self.default_timeout
        if timeout > 2592000: # 60*60*24*30, 30 days
            # See http://code.google.com/p/memcached/wiki/FAQ
            # "You can set expire times up to 30 days in the future. After that
            # memcached interprets it as a date, and will expire the item after
            # said date. This is a simple (but obscure) mechanic."
            #
            # This means that we have to switch to absolute timestamps.
            timeout += int(time.time())
        return timeout

    def add(self, key, value, timeout=0):
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        return self._cache.add(smart_str(key), value, self._get_memcache_timeout(timeout))

    def get(self, key, default=None):
        val = self._cache.get(smart_str(key))
        if val is None:
            return default
        return val

    def set(self, key, value, timeout=0):
        self._cache.set(smart_str(key), value, self._get_memcache_timeout(timeout))

    def delete(self, key):
        self._cache.delete(smart_str(key))

    def get_many(self, keys):
        return self._cache.get_multi(map(smart_str,keys))

    def close(self, **kwargs):
        self._cache.disconnect_all()

    def incr(self, key, delta=1):
        try:
            val = self._cache.incr(key, delta)

        # python-memcache responds to incr on non-existent keys by
        # raising a ValueError. Cmemcache returns None. In both
        # cases, we should raise a ValueError though.
        except ValueError:
            val = None
        if val is None:
            raise ValueError("Key '%s' not found" % key)

        return val

    def decr(self, key, delta=1):
        try:
            val = self._cache.decr(key, delta)

        # python-memcache responds to decr on non-existent keys by
        # raising a ValueError. Cmemcache returns None. In both
        # cases, we should raise a ValueError though.
        except ValueError:
            val = None
        if val is None:
            raise ValueError("Key '%s' not found" % key)
        return val

    def set_many(self, data, timeout=0):
        safe_data = {}
        for key, value in data.items():
            if isinstance(value, unicode):
                value = value.encode('utf-8')
            safe_data[smart_str(key)] = value
        self._cache.set_multi(safe_data, self._get_memcache_timeout(timeout))

    def delete_many(self, keys):
        self._cache.delete_multi(map(smart_str, keys))

    def clear(self):
        self._cache.flush_all()
