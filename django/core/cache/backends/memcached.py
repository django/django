"Memcached cache backend"

from django.core.cache.backends.base import BaseCache, InvalidCacheBackendError

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

    def get(self, key, default=None):
        val = self._cache.get(key)
        if val is None:
            return default
        else:
            return val

    def set(self, key, value, timeout=0):
        self._cache.set(key, value, timeout or self.default_timeout)

    def delete(self, key):
        self._cache.delete(key)

    def get_many(self, keys):
        return self._cache.get_multi(keys)
