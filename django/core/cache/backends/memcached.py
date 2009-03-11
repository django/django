"Memcached cache backend"

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

    def add(self, key, value, timeout=0):
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        return self._cache.add(smart_str(key), value, timeout or self.default_timeout)

    def get(self, key, default=None):
        val = self._cache.get(smart_str(key))
        if val is None:
            return default
        else:
            if isinstance(val, basestring):
                return smart_unicode(val)
            else:
                return val

    def set(self, key, value, timeout=0):
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        self._cache.set(smart_str(key), value, timeout or self.default_timeout)

    def delete(self, key):
        self._cache.delete(smart_str(key))

    def get_many(self, keys):
        return self._cache.get_multi(map(smart_str,keys))

    def close(self, **kwargs):
        self._cache.disconnect_all()

    def incr(self, key, delta=1):
        return self._cache.incr(key, delta)

    def decr(self, key, delta=1):
        return self._cache.decr(key, delta)
